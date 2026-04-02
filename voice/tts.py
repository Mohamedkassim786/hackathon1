import edge_tts
import asyncio
import os
import hashlib
import nest_asyncio

# Voice Configuration
VOICES = {
    "en": "en-US-JennyNeural",
    "ta": "ta-IN-PallaviNeural"
}

class TextToSpeech:
    def __init__(self, cache_dir="cache"):
        self.cache_dir = cache_dir
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

    async def generate_audio_async(self, text, lang="en"):
        """Generates audio using edge-tts."""
        # Force detect if not provided correctly (range check for Tamil)
        if any('\u0b80' <= c <= '\u0bff' for c in text): 
            lang = "ta"
        
        voice = VOICES.get(lang, VOICES["en"])
        
        # Caching based on hash of text and voice
        text_hash = hashlib.md5(f"{text}{voice}".encode()).hexdigest()
        output_path = os.path.join(self.cache_dir, f"{text_hash}.mp3")
        
        if os.path.exists(output_path):
            return output_path
        
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_path)
        return output_path

    def generate_audio(self, text, lang="en"):
        """Synchronous wrapper for generate_audio_async with loop handling."""
        if not text or not text.strip():
            return None
            
        try:
            # Python 3.14+ loop handling
            loop = None
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                pass
            
            if loop and loop.is_running():
                nest_asyncio.apply()
                return loop.run_until_complete(self.generate_audio_async(text, lang))
            else:
                return asyncio.run(self.generate_audio_async(text, lang))
        except Exception as e:
            print(f"TTS Error: {e}")
            # Final fallback: force a new loop if everything fails
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            return new_loop.run_until_complete(self.generate_audio_async(text, lang))

# Singleton instance
tts_engine = None

def get_tts_engine():
    global tts_engine
    if tts_engine is None:
        tts_engine = TextToSpeech()
    return tts_engine
