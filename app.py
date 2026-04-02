import streamlit as st
import re
import os
import time
import asyncio
from rag_utils import get_rag_chain
from voice.stt import get_stt_engine
from voice.tts import get_tts_engine
from voice.audio import play_audio, stop_all_audio, cleanup_temp_audio, is_audio_playing, play_emergency_alert
from langchain_core.messages import HumanMessage, AIMessage
import threading
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# --- STARTUP CLEANUP ---
cleanup_temp_audio()

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="ArogyaAI – Healthcare Assistant",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed"
)

if "messages"    not in st.session_state: st.session_state.messages    = []
if "voice_mode"  not in st.session_state: st.session_state.voice_mode  = False
if "state"       not in st.session_state: st.session_state.state       = "idle"
if "stop_signal" not in st.session_state: st.session_state.stop_signal = False
if "reminders"   not in st.session_state: st.session_state.reminders   = []
if "notified_emergency" not in st.session_state: st.session_state.notified_emergency = False
if "caregiver_notified_sms" not in st.session_state: st.session_state.caregiver_notified_sms = False
if "user_lang"   not in st.session_state: st.session_state.user_lang   = "en"
if "last_transcript" not in st.session_state: st.session_state.last_transcript = ""
if "old_mode"    not in st.session_state: st.session_state.old_mode    = False

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

/* ── EMERGENCY ALERT ── */
.emergency-banner {
    background: #7f1d1d;
    border: 4px solid #ef4444;
    border-radius: 15px;
    padding: 1.5rem;
    text-align: center;
    animation: flash 1.5s infinite;
    margin-bottom: 2rem;
}
@keyframes flash {
    0% { opacity: 1; background: #7f1d1d; }
    50% { opacity: 0.8; background: #ef4444; }
    100% { opacity: 1; background: #7f1d1d; }
}
.emergency-text {
    font-size: 2rem !important; font-weight: 900 !important; color: white !important; margin: 0 !important;
}
.emergency-sub { font-size: 1.1rem; color: #fecaca; margin-top: 0.5rem; }

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

@keyframes blink { 50% { opacity: 0.5; } }
</style>
""", unsafe_allow_html=True)

# ── DYNAMIC ACCESSIBILITY (OLD MODE) ──
if st.session_state.old_mode:
    st.markdown("""
    <style>
    :root {
        --bg:      #000000 !important;
        --surface: #111111 !important;
        --text:    #ffffff !important;
        --teal:    #fbbf24 !important; /* High contrast yellow */
        --green:   #fbbf24 !important;
    }
    .arh-title { font-size: 5rem !important; }
    .stButton > button {
        width: 180px !important;
        height: 180px !important;
        font-size: 80px !important;
    }
    .stChatMessage {
        font-size: 1.8rem !important;
        border: 3px solid #fbbf24 !important;
    }
    .arh-sub { font-size: 1.8rem !important; color: #fbbf24 !important; }
    </style>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
#  UI: HEADER
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<div class="arh">
  <div class="arh-icon">🩺</div>
  <h1 class="arh-title">ArogyaAI</h1>
  <p class="arh-sub">Premium Private Healthcare Assistant • <b>Offline Mode</b></p>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
#  EMERGENCY BANNER (TOP LEVEL)
# ══════════════════════════════════════════════════════════════════
if st.session_state.notified_emergency:
    st.markdown(f"""
        <div class="emergency-banner">
            <p class="emergency-text">🚨 EMERGENCY DETECTED 🚨</p>
            <p class="emergency-sub">Please call emergency services immediately!</p>
            {f'<p style="color:#fbbf24; font-weight:bold; margin-top:10px;">📲 SMS ALERT SENT TO CAREGIVER</p>' if st.session_state.get('caregiver_notified_sms') else ''}
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown(
            '<a href="tel:108" style="text-decoration:none;">'
            '<div style="background:#ef4444; color:white; padding:1.5rem; border-radius:15px; text-align:center; font-weight:900; font-size:1.5rem; border:2px solid white;">'
            '📞 CALL 108 (AMBULANCE)'
            '</div></a>', 
            unsafe_allow_html=True
        )
    with col2:
        caregiver_num = os.getenv("CAREGIVER_PHONE", "102")
        st.markdown(
            f'<a href="tel:{caregiver_num}" style="text-decoration:none;">'
            '<div style="background:#14b8a6; color:white; padding:1.5rem; border-radius:15px; text-align:center; font-weight:900; font-size:1.5rem; border:2px solid white;">'
            '🏠 NOTIFY CAREGIVER'
            '</div></a>', 
            unsafe_allow_html=True
        )
    st.divider()

# ══════════════════════════════════════════════════════════════════
#  CACHED ENGINES (Prevent re-loading heavy models on each loop)
# ══════════════════════════════════════════════════════════════════
@st.cache_resource
def get_cached_stt():
    return get_stt_engine()

@st.cache_resource
def get_cached_tts():
    return get_tts_engine()

@st.cache_resource
def get_cached_rag():
    return get_rag_chain()

# Initialize engines
stt_engine_cached = get_cached_stt()
tts_engine_cached = get_cached_tts()
engine = get_cached_rag()

# ══════════════════════════════════════════════════════════════════
#  UTILS
# ══════════════════════════════════════════════════════════════════
def clean_response(text):
    """Remove prefixes, handle repetition, and strip meta-notes."""
    import re
    # 1. Strip meta-notes
    text = re.sub(r'\(Note:.*?\)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'As your village doctor,', '', text, flags=re.IGNORECASE)
    
    # 2. Strip language prefixes
    text = re.sub(r'^(Tamil|English|Answer|Response|முடிவு|தகவல்):\s*', '', text, flags=re.IGNORECASE)
    text = text.replace('"', '').replace('**', '').strip()
    
    # 3. Deduplicate sentences (keep brevity)
    parts = re.split(r'(?<=[.!?|।])\s*|\n+', text)
    seen = []
    for p in parts:
        p_clean = p.strip()
        if not p_clean: continue
        is_duplicate = False
        p_low = p_clean.lower()
        for s in seen:
            s_low = s.lower()
            if p_low == s_low or p_low in s_low or s_low in p_low:
                if len(p_low) > 10:
                    is_duplicate = True
                    break
        if not is_duplicate:
            seen.append(p_clean)
    return " ".join(seen)

def is_tamil_text(text):
    """Utility to check if text contains Tamil characters."""
    for char in text:
        if '\u0b80' <= char <= '\u0bff':
            return True
    return False

def check_emergency(response_text):
    """Checks if the response indicates an emergency and triggers alerts."""
    emergency_keywords = ["108", "emergency", "மருத்துவ உதவி", "ambulance", "ஆம்புலன்ஸ்", "நெஞ்சு வலி", "breath", "மூச்சு"]
    if any(word in response_text.lower() for word in emergency_keywords):
        if not st.session_state.notified_emergency:
            play_emergency_alert()
            trigger_caregiver_alert()
        st.session_state.notified_emergency = True
        return True
    return False

def trigger_caregiver_alert():
    """Simulates sending an emergency SMS/WhatsApp to the caregiver."""
    caregiver_num = os.getenv("CAREGIVER_PHONE", "102")
    alert_msg = f"🆘 EMERGENCY ALERT SENT to Caregiver ({caregiver_num})!"
    st.toast(alert_msg, icon="🚨")
    # For hackathon demo, we'll store this in session state to show a persistent status
    st.session_state.caregiver_notified_sms = True

def clean_for_tts(text):
    """Clean text for TTS."""
    import re
    text = re.sub(r'\[REMINDER:.*?\]', '', text)
    text = re.sub(r'[*#_~>`]', '', text)
    text = text.replace('\n', ' ').strip()
    return text

def process_reminders(text: str):
    match = re.search(r'\[REMINDER:\s*([^,\]]+)(?:,\s*([^\]]+))?\]', text, re.IGNORECASE)
    if match:
        med = match.group(1).strip()
        time_str = (match.group(2) or "").strip()
        t_final = time_str
        if time_str:
            for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p", "%I %p"):
                try:
                    t_final = datetime.now().replace(
                        hour=datetime.strptime(time_str, fmt).hour,
                        minute=datetime.strptime(time_str, fmt).minute
                    ).strftime("%H:%M")
                    break
                except: continue
        else:
            t_final = (datetime.now()).strftime("%H:%M")
        
        exists = any(r["med"].lower() == med.lower() and r["time"] == t_final for r in st.session_state.reminders)
        if not exists:
            st.session_state.reminders.append({
                "med": med, 
                "time": t_final, 
                "notified": False,
                "created_at": datetime.now().isoformat()
            })
            st.toast(f"✅ Reminder set: {med} at {t_final}", icon="⏰")
        clean_text = re.sub(r'\[REMINDER:.*?\]', '', text, flags=re.IGNORECASE).strip()
        return clean_text
    return text

def check_due_reminders():
    now = datetime.now().strftime("%H:%M")
    due = []
    # If it is past the time and we have not notified, trigger it!
    for r in st.session_state.reminders:
        if r["time"] <= now and not r["notified"]:
            due.append(r["med"])
            r["notified"] = True
    return due

@st.cache_resource
def load_engine():
    return get_rag_chain("llama3")

def extract_prescription_text(uploaded_file):
    try:
        import pytesseract
        from PIL import Image, ImageOps, ImageFilter
        tess_path = os.getenv("TESSERACT_PATH", r'C:\Program Files\Tesseract-OCR\tesseract.exe')
        pytesseract.pytesseract.tesseract_cmd = tess_path
        
        # Load and Preprocess for 'Perfect' accuracy
        orig_img = Image.open(uploaded_file)
        
        # --- Multi-Precision Scan ---
        results = []
        # Angles to try (Portrait, Landscape-L, Landscape-R)
        for angle in [0, 270, 90]: 
            img = orig_img.rotate(angle, expand=True).convert('L')
            
            # Step 1: Denoise & Sharpen for handwriting legibility
            img = img.filter(ImageFilter.MedianFilter(size=3)) # Denoise
            img = ImageOps.autocontrast(img, cutoff=2) # Extreme contrast boost
            img = img.filter(ImageFilter.SHARPEN) # Sharpen edges
            
            # Step 2: Extract with Bilingual Support (English + Tamil)
            # Use PSM 11 for sparse lists of medications
            config = '--psm 11 --oem 3' 
            text = pytesseract.image_to_string(img, lang='eng+tam', config=config).strip()
            
            if len(text) > 15:
                results.append(f"[Angle {angle}]:\n{text}")
        
        # Combine all found text blocks for the LLM to cross-reference
        combined = "\n\n".join(results)
        return combined if combined else "__ERROR__: No text could be identified. Please ensure the photo is clear and bright."
    except Exception as e:
        return f"__ERROR__: {e}"


due_meds = check_due_reminders()
for med in due_meds:
    msg_text = f"🔔 REMINDER: It is time to take your {med}!"
    st.session_state.messages.append({"role": "assistant", "content": msg_text})
    st.toast(msg_text, icon="💊")
    tts = get_tts_engine()
    notif_audio = tts.generate_audio(msg_text)
    play_audio(notif_audio)

col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    if st.session_state.state == "idle":
        if st.button("🎤", help="Start Voice Assistant", use_container_width=True):
            st.session_state.voice_mode = True
            st.session_state.state = "listening"
            st.session_state.stop_signal = False
            st.rerun()
    else:
        btn_label = "🛑 STOP" if st.session_state.state != "listening" else "🎤 LISTENING..."
        if st.button(btn_label, help="Interrupt Assistant", use_container_width=True, key="stop_btn"):
            st.session_state.stop_signal = True
            st.session_state.voice_mode = False
            st.session_state.state = "idle"
            stop_all_audio()
            st.rerun()

# ══════════════════════════════════════════════════════════════════
#  VOICE PIPELINE
# ══════════════════════════════════════════════════════════════════
engine = load_engine()

status_container = st.empty()
if st.session_state.last_transcript:
    st.markdown(f"<p style='text-align:center;color:var(--muted);'>You said: <i>\"{st.session_state.last_transcript}\"</i></p>", unsafe_allow_html=True)

if st.session_state.voice_mode:
    # Helper for real-time reminder checks inside blocking loops
    def on_voice_loop():
        due = check_due_reminders()
        for med in due:
            msg = f"🔔 REMINDER: It is time to take your {med}!"
            st.session_state.messages.append({"role": "assistant", "content": msg})
            st.toast(msg, icon="💊")
            tts = get_tts_engine()
            notif_audio = tts.generate_audio(msg)
            play_audio(notif_audio)
            st.rerun()

    if st.session_state.state == "idle":
        on_voice_loop() # Check while idle
        if st.session_state.voice_mode:
            st.session_state.user_lang = None # Reset language for each new turn
            st.session_state.state = "listening"
            st.rerun()
        else:
            time.sleep(1)
            st.rerun()

    elif st.session_state.state == "listening":
        status_container.markdown("<p class='thinking-text'>👂 LISTENING...</p>", unsafe_allow_html=True)
        # Use the cached engine to prevent 10s re-loads!
        stt = stt_engine_cached 
        # Pass the callback so reminders work while waiting for speech!
        audio_path = stt.listen_until_silence(on_loop=on_voice_loop)
        
        if audio_path:
            transcript, lang = stt.transcribe(audio_path)
            if transcript:
                st.session_state.last_transcript = transcript
                st.session_state.user_lang = lang # Store Whisper's detected language!
                st.session_state.messages.append({"role": "user", "content": transcript})
                st.session_state.state = "processing"
                st.rerun()
        st.rerun()

    elif st.session_state.state == "processing":
        if st.session_state.last_transcript:
            status_container.markdown(f"<p class='thinking-text'>🗣️ You said: <b>{st.session_state.last_transcript}</b></p>", unsafe_allow_html=True)
        else:
            status_container.markdown("<p class='thinking-text'>🧠 THINKING...</p>", unsafe_allow_html=True)
            
        q = st.session_state.messages[-1]["content"]
        # Use Whisper's high-quality detection if available, fallback to character check
        if not hasattr(st.session_state, 'user_lang') or not st.session_state.user_lang:
            st.session_state.user_lang = "ta" if is_tamil_text(q) else "en"
        
        hist = [
            HumanMessage(content=m["content"]) if m["role"]=="user"
            else AIMessage(content=m["content"])
            for m in st.session_state.messages[-6:-1]
        ]
        try:
            lang_name = "TAMIL" if st.session_state.user_lang == "ta" else "ENGLISH"
            response = engine.invoke({
                "input": q, 
                "chat_history": hist,
                "language": lang_name,
                "current_time": datetime.now().strftime("%I:%M %p")
            })
            if not response or not response.strip():
                raise ValueError("Empty response from AI")
                
            response = clean_response(response)
            check_emergency(response)
            response = process_reminders(response)
            st.session_state.messages.append({"role": "assistant", "content": response})
            st.session_state.state = "speaking"
            st.rerun()
        except Exception as e:
            err_msg = "மன்னிக்கவும், என்னால் புரிந்து கொள்ள முடியவில்லை. (Sorry, I couldn't understand that.)"
            st.session_state.messages.append({"role": "assistant", "content": err_msg})
            st.session_state.state = "speaking"
            st.rerun()

    elif st.session_state.state == "speaking":
        stop_all_audio()
        status_container.markdown("<p class='thinking-text' style='color:#f1f5f9;'>🎙️ SPEAKING...</p>", unsafe_allow_html=True)
        res = st.session_state.messages[-1]["content"]
        final_lang = "ta" if is_tamil_text(res) else "en"
        # Use cached engine
        tts = tts_engine_cached 
        cleaned_text = clean_for_tts(res)
        tts_path = tts.generate_audio(cleaned_text, lang=final_lang)
        
        if tts_path and os.path.exists(tts_path):
            play_audio(tts_path, wait=False)
            while is_audio_playing():
                if st.session_state.stop_signal:
                    stop_all_audio()
                    break
                time.sleep(0.1)
        
        if st.session_state.voice_mode and not st.session_state.stop_signal:
            st.session_state.state = "listening"
        while True:
            # --- NEW: Check for reminders inside the voice loop ---
            due = check_due_reminders()
            for med in due:
                msg = f"🔔 REMINDER: It is time to take your {med}!"
                st.session_state.messages.append({"role": "assistant", "content": msg})
                # Use cached engine
                tts = tts_engine_cached 
                notif_audio = tts.generate_audio(msg)
                play_audio(notif_audio)
                st.rerun() # Refresh UI to show the message

            if st.session_state.state == "idle":
                st.rerun()

if st.session_state.notified_emergency:
    pass # Already shown at the top

# ══════════════════════════════════════════════════════════════════
#  MEDICAL IMAGE ANALYSIS (OCR + VISION)
# ══════════════════════════════════════════════════════════════════
with st.expander("📸 Upload Medical Image (Prescription or Symptom)", expanded=False):
    analysis_mode = st.radio("What are you uploading?", ["💊 Prescription", "🩺 Physical Symptom (Rash, Wound, etc.)"], horizontal=True)
    up = st.file_uploader("Upload Image", type=["png","jpg","jpeg","bmp","tiff"], key="med_up")
    if up:
        st.image(up, caption="Uploaded Image", use_column_width=True)
        if st.button("🔍 Analyze Image", use_container_width=True, key="vision_go"):
            with st.spinner("Analyzing…"):
                txt = extract_prescription_text(up)
            
            if analysis_mode == "💊 Prescription":
                if "__ERROR__" in txt or len(txt) < 15:
                    instruction = (
                        "I tried to scan this as a prescription but NO READABLE TEXT was found. "
                        "However, if this is a PHYSICAL SYMPTOM (like a rash or wound), please provide a 'First-Look' analysis. "
                        "Otherwise, tell the user to upload a clearer photo of the prescription."
                    )
                else:
                    instruction = (
                        "I have scanned this prescription. Provide a MEDICINE-ONLY summary. "
                        "STRICT RULE: NO greetings, NO meta-notes. Provide Medicine Name, Purpose, and Dosage.\n\n"
                        "OCR Text:\n" + txt
                    )
            else:
                # Symptom Mode
                instruction = (
                    "I am uploading a photo of a physical symptom (e.g., skin rash, wound, swelling). "
                    "Based on the visual context and any recognizable text, provide a medical 'First-Look' analysis. "
                    "1. Possible condition name.\n2. Severity (Urgent vs Manageable).\n3. Home-care steps.\n"
                    "STRICT RULE: Advise seeing a doctor if it looks serious. Be empathetic.\n\n"
                    "Image Context (Text found): " + (txt if txt and "__ERROR__" not in txt else "[No text detected, purely visual analysis required]")
                )
            
            st.session_state.messages.append({"role": "user", "content": instruction})
            st.rerun()

# ══════════════════════════════════════════════════════════════════
#  UI: CHAT HISTORY
# ══════════════════════════════════════════════════════════════════
for msg in st.session_state.messages:
    # Hide OCR-related instructions from the chat UI
    content = msg["content"]
    is_ocr = (
        content.startswith("Analyze this prescription OCR text") or 
        "medication details from the following OCR text" in content or
        "analyze this prescription OCR text and provide a highly readable summary" in content or
        "Using your advanced medical knowledge" in content or
        "I have scanned this prescription at multiple angles" in content or
        "provide a MEDICINE-ONLY summary" in content
    )
    if not is_ocr:
        with st.chat_message(msg["role"]):
            st.markdown(content)

# Text input fallback
if prompt := st.chat_input("Or type here..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# Processing Loop for User Messages
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    last_msg = st.session_state.messages[-1]["content"]
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            lang_name = "TAMIL" if is_tamil_text(last_msg) else "ENGLISH"
            hist = [
                HumanMessage(content=m["content"]) if m["role"]=="user"
                else AIMessage(content=m["content"])
                for m in st.session_state.messages[-6:-1]
            ]
            res = engine.invoke({
                "input": last_msg, 
                "chat_history": hist,
                "language": lang_name,
                "current_time": datetime.now().strftime("%I:%M %p")
            })
            res = clean_response(res)
            is_emergency = check_emergency(res)
            res = process_reminders(res)
            st.session_state.messages.append({"role": "assistant", "content": res})
            
            # If emergency, we MUST rerun to show the banner at the top immediately
            if is_emergency:
                st.rerun()
                
            st.markdown(res)
            tts = get_tts_engine()
            tts_path = tts.generate_audio(clean_for_tts(res))
            play_audio(tts_path)
            if st.session_state.voice_mode:
                st.rerun()

# ══════════════════════════════════════════════════════════════════
#  REMINDERS DRAWER
# ══════════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("⏰ Reminders")
    
    # --- ADHERENCE DASHBOARD ---
    st.subheader("📊 Today's Health Score")
    total_meds = len(st.session_state.reminders)
    taken_meds = sum(1 for r in st.session_state.reminders if r["notified"])
    score = (taken_meds / total_meds * 100) if total_meds > 0 else 100
    st.progress(score / 100)
    st.caption(f"Medication Adherence: {int(score)}%")
    
    st.write(f"Current Time: **{datetime.now().strftime('%H:%M')}**")
    
    st.markdown("---")
    st.session_state.old_mode = st.toggle("👴 ELDERLY MODE (High Contrast)", value=st.session_state.old_mode)
    
    if not st.session_state.reminders:
        st.info("No active reminders.")
    else:
        for i, r in enumerate(st.session_state.reminders):
            cols = st.columns([3, 1])
            with cols[0]:
                st.markdown(f"**{r['med']}** at `{r['time']}`")
            with cols[1]:
                if st.button("🗑️", key=f"del_{i}"):
                    st.session_state.reminders.pop(i)
                    st.rerun()
    if st.button("🚀 Test Reminder (Now)", use_container_width=True):
        msg_text = "🔔 TEST REMINDER: If you see/hear this, it works!"
        st.session_state.messages.append({"role": "assistant", "content": msg_text})
        st.toast(msg_text, icon="🚀")
        try:
            tts = get_tts_engine()
            path = tts.generate_audio(msg_text)
            play_audio(path)
        except Exception as e:
            st.error(f"Audio Error: {e}")
        st.rerun()

    if st.button("🔄 Refresh Reminders", use_container_width=True):
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
