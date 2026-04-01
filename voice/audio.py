import os
import time
import glob
import ctypes

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

def play_audio(file_path):
    """Plays audio using high-performance WinMM mciSendString. Blocks until finished."""
    if not os.path.exists(file_path):
        print(f"--- Audio file {file_path} not found ---")
        return
    
    # Use short path name AND quotes to be ultra-safe with MCI
    try:
        abs_path = get_short_path_name(os.path.abspath(file_path))
    except:
        abs_path = os.path.abspath(file_path)
        
    print(f"--- Playing Audio (WinMM): {abs_path} ---")
    
    mci = ctypes.windll.winmm.mciSendStringW
    
    try:
        # Check if file has any content
        if os.path.getsize(abs_path) < 100:
            print(f"--- Warning: Audio file is too small ({os.path.getsize(abs_path)} bytes) ---")
            
        mci(u'close voice_aliased', None, 0, 0)
        
        # We wrap in double-double quotes for MCI if needed, or just use short path
        open_cmd = u'open "{}" type mpegvideo alias voice_aliased'.format(abs_path)
        res = mci(open_cmd, None, 0, 0)
        
        if res == 0:
            play_res = mci(u'play voice_aliased wait', None, 0, 0)
            if play_res != 0:
                print(f"--- WinMM Play Error code: {play_res} ---")
        else:
            print(f"--- WinMM Open Error code: {res} ---")
            # Fallback attempt without 'type mpegvideo' (sometimes works better)
            res2 = mci(u'open "{}" alias voice_aliased'.format(abs_path), None, 0, 0)
            if res2 == 0:
                mci(u'play voice_aliased wait', None, 0, 0)
            else:
                 print(f"--- WinMM Fallback Open Error code: {res2} ---")
            
    except Exception as e:
        print(f"--- Error in WinMM playback: {e} ---")
    finally:
        mci(u'close voice_aliased', None, 0, 0)
        # Give a moment for file release
        time.sleep(0.1)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass

def stop_all_audio():
    """Stops any ongoing WinMM playback."""
    ctypes.windll.winmm.mciSendStringW('stop voice_aliased', None, 0, 0)
    ctypes.windll.winmm.mciSendStringW('close voice_aliased', None, 0, 0)

def cleanup_temp_audio(temp_dir="data/temp_audio"):
    """Removes all temporary audio files."""
    if not os.path.exists(temp_dir):
        return
    files = glob.glob(os.path.join(temp_dir, "*.mp3"))
    for f in files:
        try:
            os.remove(f)
        except:
            pass
