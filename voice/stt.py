import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
from faster_whisper import WhisperModel
import os
import time
import tempfile

def is_tamil(text):
    """Detect if text contains Tamil characters using Unicode range."""
    for char in text:
        if '\u0b80' <= char <= '\u0bff':
            return True
    return False

class SpeechToText:
    def __init__(self, model_size="medium"):
        # Robust initialization with fallback to smaller models if medium fails (network/RAM)
        self.temp_file = os.path.join(tempfile.gettempdir(), "stt_temp.wav")
        # Enriched Tamil medical prompt with common symptoms
        self.initial_prompt = (
            "வணக்கம் Dr, எனக்கு தலைவலி, காய்ச்சல், வயிற்று வலி மற்றும் உடல் சோர்வாக உள்ளது. "
            "Medical conversation about headache, fever, stomach pain, and fatigue in Tamil and English."
        )
        
        models_to_try = [model_size, "small", "tiny"]
        self.model = None
        
        for size in models_to_try:
            try:
                print(f"--- Attempting to load STT model: {size} ---")
                self.model = WhisperModel(size, device="cpu", compute_type="int8")
                print(f"--- Successfully loaded STT model: {size} ---")
                break
            except Exception as e:
                print(f"--- Failed to load model {size}: {e} ---")
                if size == models_to_try[-1]:
                    print("--- CRITICAL: No STT models could be loaded. ---")
                    raise e

    def listen_until_silence(self, silence_threshold=600, silence_duration=2.2, interrupt_check=None, on_loop=None):
        """Records audio until silence is detected or interrupted."""
        CHUNK = 1024
        RATE = 16000
        
        print("--- Listening... ---")
        frames = []
        silent_chunks = 0
        max_silent_chunks = int(silence_duration * RATE / CHUNK)
        min_frames = int(0.5 * RATE / CHUNK) # At least 0.5s
        
        with sd.InputStream(samplerate=RATE, channels=1, dtype='int16') as stream:
            while True:
                if on_loop: on_loop() # Run background tasks (like reminders)
                
                if interrupt_check and interrupt_check():
                    return None
                    
                data, overflowed = stream.read(CHUNK)
                frames.append(data.copy())
                
                # Simple silence detection
                rms = np.sqrt(np.mean(data.astype(np.float32)**2))
                if rms < silence_threshold:
                    silent_chunks += 1
                else:
                    silent_chunks = 0
                
                if len(frames) > min_frames and silent_chunks > max_silent_chunks:
                    break
        
        if not frames: return None
        
        audio_data = np.concatenate(frames)
        wav.write(self.temp_file, RATE, audio_data)
        return self.temp_file

    def transcribe(self, audio_path):
        """Transcribes audio and filters out Whisper hallucinations."""
        if not audio_path or not os.path.exists(audio_path):
            return "", "en"
            
        segments, info = self.model.transcribe(
            audio_path, 
            beam_size=5, 
            initial_prompt=self.initial_prompt
        )
        text = "".join([s.text for s in list(segments)]).strip()
        
        # --- Hallucination Filter ---
        hallucinations = [
            "Thank you for watching", "Thanks for watching", 
            "Subscribe to my channel", "Please like and subscribe",
            "Medical assistant conversation", "வணக்கம் Dr" # Echoes of the prompt
        ]
        
        # If the result is just a hallucination or exactly the prompt, ignore it
        for h in hallucinations:
            if h.lower() in text.lower() and len(text) < len(h) + 10:
                print(f"--- Filtered Hallucination: {text} ---")
                text = ""
                break
        
        if not text or len(text) < 2:
            return "", "en"

        # Determine language for TTS: priority to whisper's info, fallback to Unicode
        lang = "ta" if info.language == "ta" or is_tamil(text) else "en"
        
        print(f"--- Decoded ({lang}): {text} ---")
        try:
            os.remove(audio_path)
        except: pass
        return text, lang

# Singleton instance
stt_engine = None
def get_stt_engine():
    global stt_engine
    if stt_engine is None:
        stt_engine = SpeechToText()
    return stt_engine
