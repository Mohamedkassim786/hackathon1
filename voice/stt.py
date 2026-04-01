import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
from faster_whisper import WhisperModel
import os
import time

# Model configuration
MODEL_SIZE = "base"  # "base", "small", "md" for local
DEVICE = "cpu"      # Use "cuda" if GPU is available
COMPUTE_TYPE = "int8"

class SpeechToText:
    def __init__(self):
        print(f"--- Loading Whisper Model: {MODEL_SIZE} ---")
        self.model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
        self.temp_file = "temp_stt.wav"
        self.stop_requested = False

    def record_audio(self, duration=5, samplerate=16000):
        """Records audio from the microphone."""
        print(f"--- Recording for {duration} seconds... ---")
        audio_data = sd.rec(int(duration * samplerate), samplerate=samplerate, channels=1, dtype='int16')
        sd.wait()
        wav.write(self.temp_file, samplerate, audio_data)
        return self.temp_file

    def listen_until_silence(self, samplerate=16000, silence_threshold=300, silence_duration=0.8, interrupt_check=None):
        """Records until silence is detected OR interrupt_check returns True."""
        print(f"--- Listening (Thresh: {silence_threshold})... ---")
        chunk_size = 1024
        audio_buffer = []
        has_spoken = False
        start_time = time.time()
        max_duration = 15 # Max 15 seconds per turn
        
        with sd.InputStream(samplerate=samplerate, channels=1, dtype='int16') as stream:
            silent_chunks = 0
            while True:
                # 1. Check for manual STOP
                if interrupt_check and interrupt_check():
                    print("--- Listening interrupted ---")
                    return None
                
                # 2. Check for global timeout
                if time.time() - start_time > max_duration:
                    print("--- Maximum recording duration reached ---")
                    break

                data, overflowed = stream.read(chunk_size)
                audio_buffer.append(data.copy())
                
                # 3. Detect volume
                max_vol = np.max(np.abs(data))
                if max_vol > silence_threshold:
                    if not has_spoken:
                        print("--- Speech detected! ---")
                    has_spoken = True
                    silent_chunks = 0
                else:
                    if has_spoken:
                        silent_chunks += 1
                
                # 4. Detect end of speech (silence after speaking)
                if has_spoken and (silent_chunks > (silence_duration * samplerate / chunk_size)):
                    print("--- End of speech detected ---")
                    break
                
                # 5. Safety: No speech at all for 10 seconds
                if not has_spoken and (time.time() - start_time > 10):
                    print("--- No speech detected, stopping ---")
                    return None

        if not audio_buffer or not has_spoken:
            return None
            
        audio_data = np.concatenate(audio_buffer, axis=0)
        wav.write(self.temp_file, samplerate, audio_data)
        return self.temp_file

    def transcribe(self, audio_path=None):
        """Transcribes audio to text."""
        path = audio_path or self.temp_file
        if not os.path.exists(path):
            return ""
        
        segments, info = self.model.transcribe(path, beam_size=5)
        text = " ".join([segment.text for segment in segments]).strip()
        
        # Cleanup
        if os.path.exists(path):
            os.remove(path)
            
        return text

# Singleton instance
stt_engine = None

def get_stt_engine():
    global stt_engine
    if stt_engine is None:
        stt_engine = SpeechToText()
    return stt_engine
