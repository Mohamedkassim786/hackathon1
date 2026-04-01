import edge_tts
import asyncio
import os
import time
import uuid

# Voice Configuration
VOICE = "en-IN-NeerjaNeural"
TEMP_DIR = "data/temp_audio"

class TextToSpeech:
    def __init__(self):
        self.voice = VOICE
        if not os.path.exists(TEMP_DIR):
            os.makedirs(TEMP_DIR, exist_ok=True)

    async def generate_audio_async(self, text):
        """Generates a unique audio file from text using edge-tts."""
        filename = f"tts_{int(time.time())}_{uuid.uuid4().hex[:8]}.mp3"
        output_path = os.path.join(TEMP_DIR, filename)
        
        print(f"--- Generating TTS: {output_path} ---")
        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(output_path)
        return output_path

    def generate_audio(self, text):
        """Synchronous wrapper for generate_audio_async using asyncio.run."""
        return asyncio.run(self.generate_audio_async(text))

# Singleton instance
tts_engine = None

def get_tts_engine():
    global tts_engine
    if tts_engine is None:
        tts_engine = TextToSpeech()
    return tts_engine
