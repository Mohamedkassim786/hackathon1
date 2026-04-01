import streamlit as st
import re
import os
import time
import asyncio
from rag_utils import get_rag_chain
from voice.stt import get_stt_engine
from voice.tts import get_tts_engine
from voice.audio import play_audio, stop_all_audio, cleanup_temp_audio
from langchain_core.messages import HumanMessage, AIMessage

# --- STARTUP CLEANUP ---
cleanup_temp_audio()

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="ArogyaAI – Healthcare Assistant",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# OLD CODE
# if "messages"      not in st.session_state: st.session_state.messages      = []
# if "voice_mode"    not in st.session_state: st.session_state.voice_mode    = False
# if "processing"    not in st.session_state: st.session_state.processing    = False

# NEW CODE
if "messages"    not in st.session_state: st.session_state.messages    = []
if "voice_mode"  not in st.session_state: st.session_state.voice_mode  = False
if "state"       not in st.session_state: st.session_state.state       = "idle"  # idle, listening, processing, speaking
if "stop_signal" not in st.session_state: st.session_state.stop_signal = False

# ══════════════════════════════════════════════════════════════════
#  ACCESSIBILITY-FIRST DESIGN (CSS)
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap');

:root {
    --green:   #22c55e;
    --teal:    #14b8a6;
    --bg:      #0a0f1a;
    --surface: rgba(255,255,255,0.05);
    --border:  rgba(255,255,255,0.10);
    --text:    #f1f5f9;
    --muted:   #94a3b8;
}

body {
    background-color: var(--bg);
    color: var(--text);
    font-family: 'Nunito', sans-serif;
}

[data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
}

/* Hide Streamlit chrome */
[data-testid="stHeader"], [data-testid="stToolbar"], footer { display: none !important; }

/* Main column */
.main .block-container {
    max-width: 860px !important;
    margin: 0 auto !important;
    padding: 2rem 1.5rem 6rem !important;
}

/* ── HEADER ── */
.arh { text-align: center; margin-bottom: 2rem; }
.arh-icon { font-size: 4rem; line-height: 1; margin-bottom: 0.3rem; }
.arh-title {
    font-size: 3.2rem; font-weight: 900;
    background: linear-gradient(135deg, #f1f5f9, var(--teal));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0;
}
.arh-sub { font-size: 1.2rem; color: var(--muted); }

/* ── CHAT BUBBLE ── */
.stChatMessage {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 20px !important;
    padding: 1rem !important;
    margin-bottom: 1rem !important;
}

/* ── MIC BUTTON ── */
.mic-btn-container {
    display: flex;
    justify-content: center;
    margin: 2rem 0;
}

.stButton > button {
    background: var(--green) !important;
    color: white !important;
    border-radius: 50% !important;
    width: 100px !important;
    height: 100px !important;
    font-size: 40px !important;
    border: none !important;
    box-shadow: 0 0 20px rgba(34, 197, 94, 0.4) !important;
    transition: all 0.3s ease !important;
}

.stButton > button:hover {
    transform: scale(1.1) !important;
    box-shadow: 0 0 30px rgba(34, 197, 94, 0.6) !important;
}

.voice-active {
    animation: pulse 1.5s infinite;
}

@keyframes pulse {
    0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.7); }
    70% { transform: scale(1.1); box-shadow: 0 0 0 15px rgba(34, 197, 94, 0); }
    100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(34, 197, 94, 0); }
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
#  UTILS
# ══════════════════════════════════════════════════════════════════
def clean_for_tts(text: str) -> str:
    t = re.sub(r'[#*_~>`\-]+', ' ', text)
    t = t.replace('\n', ' ').strip()
    return t[:1000]

@st.cache_resource
def load_engine():
    return get_rag_chain("llama3")

def extract_prescription_text(uploaded_file):
    try:
        import pytesseract
        from PIL import Image
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        img = Image.open(uploaded_file)
        return pytesseract.image_to_string(img).strip()
    except Exception as e:
        return f"__ERROR__: {e}"

# ══════════════════════════════════════════════════════════════════
#  HEADER
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<div class="arh">
  <div class="arh-icon">🩺</div>
  <h1 class="arh-title">ArogyaAI</h1>
  <p class="arh-sub">A premium, multi-modal healthcare assistant</p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
#  CONTROLS
# ══════════════════════════════════════════════════════════════════
col1, col2, col3 = st.columns([1, 2, 1])

# OLD CODE
# with col2:
#     if not st.session_state.voice_mode:
#         if st.button("🎤", help="Start Voice Assistant"):
#             st.session_state.voice_mode = True
#             st.rerun()
#     else:
#         if st.button("🔴", help="Stop Assistant"):
#             st.session_state.voice_mode = False
#             st.rerun()

# NEW CODE
with col2:
    if st.session_state.state == "idle":
        if st.button("🎤", help="Start Voice Assistant", use_container_width=True):
            st.session_state.voice_mode = True
            st.session_state.state = "listening"
            st.session_state.stop_signal = False
            st.rerun()
    else:
        if st.button("🛑 STOP", help="Interrupt Assistant", use_container_width=True):
            st.session_state.stop_signal = True
            st.session_state.voice_mode = False
            st.session_state.state = "idle"
            stop_all_audio()
            st.rerun()

# ══════════════════════════════════════════════════════════════════
#  VOICE PIPELINE
# ══════════════════════════════════════════════════════════════════
engine = load_engine()

# OLD CODE
# if st.session_state.voice_mode:
#     status_placeholder = st.empty()
#     status_placeholder.markdown("<p style='text-align:center;color:#22c55e;'><b>LISTENING...</b></p>", unsafe_allow_html=True)
#     
#     # 1. Listen
#     stt = get_stt_engine()
#     audio_path = stt.listen_until_silence()
#     transcript = stt.transcribe(audio_path)
#     
#     if transcript:
#         st.session_state.messages.append({"role": "user", "content": transcript})
#         
#         # 2. LLM Processing
#         status_placeholder.markdown("<p style='text-align:center;color:#14b8a6;'><b>THINKING...</b></p>", unsafe_allow_html=True)
#         ...
#         # 3. TTS + Playback
#         ...
#         play_audio(tts_path)
#         st.rerun()

# NEW CODE
status_container = st.empty()

if st.session_state.voice_mode:
    if st.session_state.state == "listening":
        status_container.markdown("<p style='text-align:center;color:#22c55e;font-size:1.5rem;'><b>🎤 Listening...</b></p>", unsafe_allow_html=True)
        stt = get_stt_engine()
        # Non-blocking check: if stop signal is mid-listen, it returns None
        audio_path = stt.listen_until_silence(interrupt_check=lambda: st.session_state.stop_signal)
        
        if st.session_state.stop_signal:
            st.session_state.state = "idle"
            st.rerun()
            
        if audio_path:
            transcript = stt.transcribe(audio_path)
            if transcript:
                st.session_state.messages.append({"role": "user", "content": transcript})
                st.session_state.state = "processing"
                st.rerun()
        else:
            # Re-run to keep the loop alive without blocking UI forever
            st.rerun()

    elif st.session_state.state == "processing":
        status_container.markdown("<p style='text-align:center;color:#14b8a6;font-size:1.5rem;'><b>🧠 Thinking...</b></p>", unsafe_allow_html=True)
        # LLM Logic
        q = st.session_state.messages[-1]["content"]
        hist = [
            HumanMessage(content=m["content"]) if m["role"]=="user"
            else AIMessage(content=m["content"])
            for m in st.session_state.messages[-6:-1]
        ]
        try:
            response = engine.invoke({"input": q, "chat_history": hist})
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state.state = "speaking"
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
            st.session_state.state = "idle"
            st.rerun()

    elif st.session_state.state == "speaking":
        status_container.markdown("<p style='text-align:center;color:#f1f5f9;font-size:1.5rem;'><b>🎙️ Generating Voice...</b></p>", unsafe_allow_html=True)
        res = st.session_state.messages[-1]["content"]
        
        start_time = time.time()
        tts = get_tts_engine()
        tts_path = tts.generate_audio(clean_for_tts(res))
        gen_time = time.time() - start_time
        print(f"--- TTS Generation took {gen_time:.2f}s ---")
        
        status_container.markdown("<p style='text-align:center;color:#f1f5f9;font-size:1.5rem;'><b>🔊 Speaking...</b></p>", unsafe_allow_html=True)
        play_audio(tts_path)
        
        if st.session_state.voice_mode and not st.session_state.stop_signal:
            st.session_state.state = "listening"
        else:
            st.session_state.state = "idle"
        st.rerun()

# ══════════════════════════════════════════════════════════════════
#  PRESCRIPTION OCR
# ══════════════════════════════════════════════════════════════════
with st.expander("📋 Upload Prescription for Explanation", expanded=False):
    up = st.file_uploader("Prescription image", type=["png","jpg","jpeg","bmp","tiff"], key="presc_up")
    if up:
        st.image(up, caption="Your prescription", use_column_width=True)
        if st.button("🔍 Explain this prescription", use_container_width=True, key="ocr_go"):
            with st.spinner("Reading…"):
                txt = extract_prescription_text(up)
            if txt.startswith("__ERROR__"):
                st.error("Tesseract not found. Please install it or check the path.")
            elif not txt:
                st.warning("No text found – try a clearer image.")
            else:
                st.session_state.messages.append({"role": "user", "content": f"Analyze this prescription OCR text. For each medicine, list: 1. Medicine Name, 2. What it is used for (its purpose), 3. Dosage schedule (when/how to take). If the OCR is unclear about the purpose, use your medical knowledge to provide a general explanation. Keep it very brief: {txt}"})
                st.rerun()

# ══════════════════════════════════════════════════════════════════
#  UI: CHAT HISTORY
# ══════════════════════════════════════════════════════════════════
for msg in st.session_state.messages:
    # Do not show internal OCR commands
    if not msg["content"].startswith("Analyze this prescription OCR text"):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# Text input fallback
if prompt := st.chat_input("Or type here..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# Processing Loop for User Messages
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_msg = st.session_state.messages[-1]["content"]
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            hist = [
                HumanMessage(content=m["content"]) if m["role"]=="user"
                else AIMessage(content=m["content"])
                for m in st.session_state.messages[-6:-1]
            ]
            res = engine.invoke({"input": last_msg, "chat_history": hist})
            st.markdown(res)
            st.session_state.messages.append({"role": "assistant", "content": res})
            
            # Speak the response
            tts = get_tts_engine()
            tts_path = tts.generate_audio(clean_for_tts(res))
            play_audio(tts_path)
            
            # If in voice mode, rerun to continue the loop
            if st.session_state.voice_mode:
                st.rerun()

st.markdown("---")
if st.button("🗑️ Clear Conversation", use_container_width=True):
    st.session_state.messages = []
    st.rerun()

st.markdown("""
<div style="text-align:center;color:#475569;font-size:0.9rem;margin-top:2rem;">
  ArogyaAI • local & Private Voice Assistant • 🇮🇳
</div>
""", unsafe_allow_html=True)
