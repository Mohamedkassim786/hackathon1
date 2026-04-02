import os
import time
import glob
import ctypes
import winsound
import threading

def get_short_path_name(long_name):
    """Returns the DOS-compatible 8.3 short path for a given long path."""
    from ctypes import wintypes
    _GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
    _GetShortPathNameW.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
    _GetShortPathNameW.restype = wintypes.DWORD
    
    needed = _GetShortPathNameW(long_name, None, 0)
    if needed == 0: return long_name
    
    output_buf = ctypes.create_unicode_buffer(needed)
    _GetShortPathNameW(long_name, output_buf, needed)
    return output_buf.value

def play_audio(file_path, wait=False):
    """Plays audio using high-performance WinMM mciSendString."""
    if not os.path.exists(file_path):
        return
    
    try:
        abs_path = get_short_path_name(os.path.abspath(file_path))
    except:
        abs_path = os.path.abspath(file_path)
        
    mci = ctypes.windll.winmm.mciSendStringW
    
    # Close any existing session
    mci(u'close voice_aliased', None, 0, 0)
    
    open_cmd = u'open "{}" type mpegvideo alias voice_aliased'.format(abs_path)
    res = mci(open_cmd, None, 0, 0)
    
    if res == 0:
        # Non-blocking play (remove 'wait') unless specified
        play_cmd = u'play voice_aliased' + (u' wait' if wait else u'')
        mci(play_cmd, None, 0, 0)
    else:
        # Fallback
        mci(u'open "{}" alias voice_aliased'.format(abs_path), None, 0, 0)
        mci(u'play voice_aliased' + (u' wait' if wait else u''), None, 0, 0)

def stop_all_audio():
    """Immediately stops and closes the WinMM alias."""
    mci = ctypes.windll.winmm.mciSendStringW
    mci(u'stop voice_aliased', None, 0, 0)
    mci(u'close voice_aliased', None, 0, 0)

def is_audio_playing():
    """Checks if audio is still playing."""
    mci = ctypes.windll.winmm.mciSendStringW
    buffer = ctypes.create_unicode_buffer(128)
    mci(u'status voice_aliased mode', buffer, 128, 0)
    return u'playing' in buffer.value.lower()

def cleanup_temp_audio(temp_dir="data/temp_audio"):
    """Removes all temporary audio files."""
    if not os.path.exists(temp_dir):
        return
    # Use a try-except to avoid issues with open files
    for f in glob.glob(os.path.join(temp_dir, "*.mp3")):
        try: os.remove(f)
        except: pass

def play_emergency_alert():
    """Plays a high-frequency alternating siren sound using Windows Beep in a thread."""
    def _siren():
        for _ in range(3):
            winsound.Beep(1500, 300) # High pitch
            winsound.Beep(1000, 300) # Low pitch
    
    threading.Thread(target=_siren, daemon=True).start()
