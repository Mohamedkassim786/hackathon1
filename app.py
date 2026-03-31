import sys
import pydantic
import streamlit as st
import re
from rag_utils import get_rag_chain
from langchain_core.messages import HumanMessage, AIMessage
import streamlit.components.v1 as components

# --- PYDANTIC PATCH ---
try:
    if not hasattr(pydantic, "v1"):
        import pydantic.v1 as v1
        sys.modules["pydantic.v1"] = v1
except ImportError:
    sys.modules["pydantic.v1"] = pydantic

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="ArogyaAI – Healthcare Assistant",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- SESSION STATE ---
if "messages"      not in st.session_state: st.session_state.messages      = []
if "voice_pending" not in st.session_state: st.session_state.voice_pending = ""
if "tts_text"      not in st.session_state: st.session_state.tts_text      = ""
if "auto_listen"   not in st.session_state: st.session_state.auto_listen   = False

# ══════════════════════════════════════════════════════════════════
#  ACCESSIBILITY-FIRST DESIGN
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

* { box-sizing: border-box; }

html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    font-family: 'Nunito', sans-serif !important;
    font-size: 20px !important;
    color: var(--text) !important;
}

/* Radial glow background */
[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed; inset: 0; z-index: 0;
    background:
        radial-gradient(ellipse 60% 40% at 20% 20%, rgba(34,197,94,0.08) 0%, transparent 70%),
        radial-gradient(ellipse 60% 40% at 80% 80%, rgba(20,184,166,0.08) 0%, transparent 70%);
    pointer-events: none;
}

/* Hide Streamlit chrome */
[data-testid="stHeader"],
[data-testid="stToolbar"],
#MainMenu, footer, .stDeployButton { display: none !important; }

/* Sidebar collapsed */
[data-testid="stSidebar"] { display: none !important; }

/* Main column */
.main .block-container {
    max-width: 860px !important;
    margin: 0 auto !important;
    padding: 2rem 1.5rem 6rem !important;
}

/* ── HEADER ── */
.arh { text-align: center; margin-bottom: 0.5rem; }
.arh-icon { font-size: 4rem; line-height: 1; margin-bottom: 0.3rem; }
.arh-title {
    font-size: 3.2rem; font-weight: 900;
    background: linear-gradient(135deg, #f1f5f9, var(--teal));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 0 0 0.3rem;
}
.arh-sub {
    font-size: 1.2rem; color: var(--muted); margin-bottom: 0.3rem;
}
.arh-hint {
    display: inline-block;
    background: rgba(34,197,94,0.08);
    border: 1px solid rgba(34,197,94,0.2);
    color: var(--green);
    border-radius: 999px;
    padding: 6px 20px;
    font-size: 1rem;
    font-weight: 700;
    margin-bottom: 1.5rem;
}

/* ── CHAT BUBBLE ── */
.stChatMessage {
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    border-radius: 20px !important;
    padding: 1.4rem 1.6rem !important;
    margin-bottom: 1rem !important;
    font-size: 1.2rem !important;
    line-height: 1.75 !important;
}
.stChatMessage p { font-size: 1.2rem !important; }

/* ── CHAT INPUT ── */
.stChatInputContainer {
    border-radius: 999px !important;
    border: 2px solid var(--border) !important;
    background: rgba(255,255,255,0.04) !important;
    backdrop-filter: blur(16px);
    font-size: 1.2rem !important;
}
.stChatInputContainer textarea {
    font-size: 1.2rem !important;
    color: var(--text) !important;
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
}

/* ── HIDE THE TEXT INPUT BRIDGE ── */
div[data-testid="stForm"] {
    display: none !important;
}

/* ── QUICK BUTTONS ── */
.stButton > button {
    background: var(--surface) !important;
    color: var(--text) !important;
    border: 1px solid var(--border) !important;
    border-radius: 16px !important;
    padding: 1rem 1.2rem !important;
    font-size: 1.05rem !important;
    font-weight: 700 !important;
    font-family: 'Nunito', sans-serif !important;
    transition: all 0.2s !important;
    width: 100% !important;
    text-align: left !important;
    line-height: 1.4 !important;
}
.stButton > button:hover {
    border-color: var(--green) !important;
    background: rgba(34,197,94,0.08) !important;
    transform: translateY(-2px) !important;
}

/* ── EXPANDER ── */
details > summary {
    font-size: 1.1rem !important;
    font-weight: 700 !important;
    color: var(--muted) !important;
    cursor: pointer;
}

/* ── SPINNER ── */
.stSpinner > div { border-color: var(--green) transparent transparent transparent !important; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
#  UTILS
# ══════════════════════════════════════════════════════════════════
def send_query(text: str):
    if text and text.strip():
        st.session_state.messages.append({"role": "user", "content": text.strip()})
        st.rerun()

def clear_chat():
    st.session_state.messages      = []
    st.session_state.voice_pending = ""
    st.session_state.tts_text      = ""
    st.rerun()

def clean_for_tts(text: str) -> str:
    t = re.sub(r'[#*_~>`\-]+', ' ', text)
    t = t.replace('"', '').replace("'", '').replace('\n', ' ')
    t = re.sub(r'\s+', ' ', t).strip()
    return t[:700]

def extract_prescription_text(uploaded_file):
    try:
        import pytesseract
        from PIL import Image
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        img = Image.open(uploaded_file)
        return pytesseract.image_to_string(img).strip()
    except ImportError:
        return "__IMPORT_ERROR__"
    except Exception as e:
        if "tesseract" in str(e).lower():
            return "__TESSERACT_MISSING__"
        return f"__ERROR__: {e}"

@st.cache_resource
def get_engine(model="llama3"):
    try:
        return get_rag_chain(model)
    except Exception:
        return None

# ══════════════════════════════════════════════════════════════════
#  TTS – fires on every rerun where tts_text is set
#  Placed at TOP so it persists before st.rerun() clears it
# ══════════════════════════════════════════════════════════════════
if st.session_state.tts_text:
    _tts = st.session_state.tts_text
    st.session_state.tts_text = ""
    components.html(f"""
<script>
(function(){{
  function speak(){{
    var text = "{_tts}";
    if(!('speechSynthesis' in window)){{ afterSpeak(); return; }}
    window.speechSynthesis.cancel();
    var u = new SpeechSynthesisUtterance(text);
    u.lang    = 'en-IN';
    u.rate    = 0.92;
    u.pitch   = 1.0;
    u.volume  = 1.0;
    var voices = window.speechSynthesis.getVoices();
    var pref = voices.find(v => v.lang.startsWith('en') && v.name.toLowerCase().includes('female'))
            || voices.find(v => v.lang.startsWith('en'));
    if(pref) u.voice = pref;
    u.onend = afterSpeak;
    window.speechSynthesis.speak(u);
  }}
  function afterSpeak(){{
    // Dispatch a custom event on the topmost parent document to cross the iframe boundary perfectly
    try{{
      window.parent.document.dispatchEvent(new CustomEvent('arogyaTTSComplete'));
    }}catch(e){{}}
  }}
  if(window.speechSynthesis.getVoices().length === 0){{
    window.speechSynthesis.onvoiceschanged = speak;
  }} else {{
    speak();
  }}
}})();
</script>
""", height=0)

# ══════════════════════════════════════════════════════════════════
#  VOICE INPUT (hidden form bridge form)
# ══════════════════════════════════════════════════════════════════
with st.form("voice_form", clear_on_submit=True):
    st.text_input("v", key="_vt", label_visibility="collapsed")
    submitted = st.form_submit_button("Submit")

if submitted and st.session_state._vt:
    q = st.session_state._vt.strip()
    if q:
        send_query(q)

# ══════════════════════════════════════════════════════════════════
#  HEADER
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<div class="arh">
  <div class="arh-icon">🩺</div>
  <h1 class="arh-title">ArogyaAI</h1>
  <p class="arh-sub">Your caring voice-first health companion</p>
  <span class="arh-hint">Press <strong>SPACE</strong> or tap 🎤 to speak</span>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
#  VOICE MIC BUTTON (large, central, always visible)
# ══════════════════════════════════════════════════════════════════
components.html(f"""
<style>
  #micArea {{
    display: flex;
    flex-direction: column;
    align-items: center;
    margin: 0.5rem 0 1.5rem;
  }}
  #micBtn {{
    width: 120px; height: 120px;
    border-radius: 50%;
    border: 3px solid rgba(34,197,94,0.5);
    background: radial-gradient(circle at 35% 35%, rgba(34,197,94,0.25), rgba(20,184,166,0.1));
    color: #22c55e;
    font-size: 3rem;
    cursor: pointer;
    transition: all 0.25s ease;
    outline: none;
    position: relative;
    box-shadow: 0 0 30px rgba(34,197,94,0.15);
  }}
  #micBtn:hover {{
    transform: scale(1.08);
    box-shadow: 0 0 50px rgba(34,197,94,0.35);
  }}
  #micBtn.listening {{
    border-color: #ef4444;
    background: radial-gradient(circle at 35% 35%, rgba(239,68,68,0.25), rgba(239,68,68,0.05));
    color: #ef4444;
    box-shadow: 0 0 0 0 rgba(239,68,68,0.4);
    animation: pulse 1.2s infinite;
  }}
  @keyframes pulse {{
    0%   {{ box-shadow: 0 0 0 0   rgba(239,68,68,0.4); }}
    60%  {{ box-shadow: 0 0 0 22px rgba(239,68,68,0); }}
    100% {{ box-shadow: 0 0 0 0   rgba(239,68,68,0); }}
  }}
  #micLabel {{
    margin-top: 14px;
    font-size: 1.15rem;
    font-weight: 800;
    font-family: 'Nunito', sans-serif;
    color: #94a3b8;
    letter-spacing: 0.02em;
  }}
  #micStatus {{
    margin-top: 8px;
    font-size: 1.05rem;
    font-family: 'Nunito', sans-serif;
    color: #64748b;
    min-height: 26px;
    text-align: center;
  }}
</style>

<div id="micArea">
  <button id="micBtn" title="Click or press SPACE to speak" aria-label="Microphone: click to speak">🎤</button>
  <div id="micLabel">TAP TO SPEAK</div>
  <div id="micStatus"></div>
</div>

<script>
(function(){{
  var recognition = null;
  var listening    = false;
  var manualStop   = false;
  // Read from session storage so Streamlit reruns don't wipe the continuous state
  var isContinuousSession = sessionStorage.getItem('arogya_cont') === 'true';

  var SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;

  if(!SpeechRec){{
    document.getElementById('micStatus').innerText = 'Voice not supported – use Chrome or Edge';
    document.getElementById('micBtn').disabled = true;
    return;
  }}

  // Check for Secure Context (HTTPS) - required for Speech API on non-localhost
  if (!window.isSecureContext && window.location.hostname !== 'localhost' && window.location.hostname !== '127.0.0.1') {{
    document.getElementById('micStatus').innerHTML = '<span style="color:#ef4444;font-weight:bold;">⚠️ HTTPS REQUIRED FOR VOICE</span><br><small style="color:#94a3b8;">Browsers block mic/voice on non-secure mobile connections. Use <b>localhost</b> or set up <b>HTTPS</b>.</small>';
    document.getElementById('micBtn').style.opacity = '0.4';
    document.getElementById('micBtn').title = 'HTTPS required for voice on mobile';
  }}

  function buildRec(){{
    var r = new SpeechRec();
    r.lang = 'en-IN';
    r.interimResults = false;
    r.maxAlternatives = 1;
    r.continuous = false;

    r.onresult = function(e){{
      var t = e.results[0][0].transcript;
      document.getElementById('micStatus').innerText = 'Heard: ' + t;
      sendToStreamlit(t);
    }};
    r.onerror = function(e){{
      var m = e.error === 'not-allowed' ? 'Microphone access denied – please allow mic permission'
            : e.error === 'no-speech'   ? 'No speech – listening again...'
            : 'Error: ' + e.error;
      document.getElementById('micStatus').innerText = m;
      // On no-speech, restart anyway (keep always-on)
      if(!manualStop) setTimeout(startListening, 400);
      else stopListeningUI();
    }};
    // onend fires after every utterance; restart unless user manually stopped
    r.onend = function(){{
      if(!manualStop){{
        setTimeout(startListening, 300); // brief pause then listen again
      }} else {{
        stopListeningUI();
      }}
    }};
    return r;
  }}

  function startListening(){{
    if(listening) return; // guard: already on
    try {{
      manualStop = false;
      isContinuousSession = true;
      sessionStorage.setItem('arogya_cont', 'true');
      recognition = buildRec();
      recognition.start();
      listening = true;
      document.getElementById('micBtn').classList.add('listening');
      document.getElementById('micBtn').innerText = '🔴';
      document.getElementById('micLabel').innerText = 'LISTENING…';
      document.getElementById('micStatus').innerText = 'Speak now — always listening';
    }} catch(e) {{
      document.getElementById('micStatus').innerText = 'Could not start mic: ' + e.message;
    }}
  }}

  // Reset visual state only
  function stopListeningUI(){{
    listening = false;
    document.getElementById('micBtn').classList.remove('listening');
    document.getElementById('micBtn').innerText = '🎤';
    document.getElementById('micLabel').innerText = 'TAP TO SPEAK';
  }}

  // Full manual stop (prevents onend from restarting, breaks the continuous session)
  function stopListening(){{
    manualStop = true;
    isContinuousSession = false;
    sessionStorage.setItem('arogya_cont', 'false');
    try{{ if(recognition) recognition.stop(); }}catch(e){{}}
    stopListeningUI();
  }}

  document.getElementById('micBtn').onclick = function(){{
    if(listening){{ stopListening(); }}
    else {{ startListening(); }}
  }};

  // Spacebar shortcut
  document.addEventListener('keydown', function(e){{
    if(e.code === 'Space' && !e.target.matches('input,textarea')){{
      e.preventDefault();
      if(listening){{ stopListening(); }}
      else {{ startListening(); }}
    }}
  }});
  // Read the TTS complete event from the shared parent document DOM
  try {{
    window.parent.document.addEventListener('arogyaTTSComplete', function() {{
      if(isContinuousSession) {{
        // Brief pause to clear audio channel
        setTimeout(startListening, 600);
      }}
    }});
  }} catch(e) {{}}
  // Send transcript into Streamlit hidden form
  function sendToStreamlit(text){{
    try{{
      var doc = window.parent.document;
      
      // 1. Find the hidden form's text input
      var inps = doc.querySelectorAll('div[data-testid="stForm"] input[type="text"]');
      if(inps.length === 0) return;
      var el = inps[0];
      
      // 2. Set value natively so React detects it
      var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;
      setter.call(el, text);
      el.dispatchEvent(new Event('input', {{bubbles:true}}));
      el.dispatchEvent(new Event('change', {{bubbles:true}}));
      
      // 3. Find the hidden form's submit button and click it! This is 100% reliable in Streamlit.
      setTimeout(function() {{
        var btns = doc.querySelectorAll('div[data-testid="stForm"] button');
        if(btns.length > 0) {{
          btns[0].click();
        }}
      }}, 50);
      
    }}catch(e){{
      document.getElementById('micStatus').innerText = 'Could not send to app: ' + e.message;
    }}
  }}

  // Global spacebar listener on parent page too
  try{{
    window.parent.document.addEventListener('keydown', function(e){{
      if(e.code === 'Space' && !e.target.matches('input,textarea,button')){{
        e.preventDefault();
        if(listening){{ try{{ recognition.stop(); }}catch(e2){{}} stopListening(); }}
        else {{ startListening(); }}
      }}
    }});
  }}catch(e){{}}

}})();
</script>
""", height=220)

# ══════════════════════════════════════════════════════════════════
#  QUICK HEALTH TOPICS  (compact – 2 rows of 3)
# ══════════════════════════════════════════════════════════════════
with st.expander("💊 Quick Topics  (tap to ask instantly)", expanded=False):
    q1, q2, q3 = st.columns(3)
    topics = [
        ("🤒", "Fever",       "How do I manage a fever at home?"),
        ("🤕", "Headache",    "What helps with a bad headache?"),
        ("🤧", "Cold & Flu",  "Remedies for cold and runny nose?"),
        ("🩹", "First Aid",   "Basic first-aid for cuts and wounds?"),
        ("💊", "Safe Meds",   "When is paracetamol safe to take?"),
        ("🚨", "Emergency",   "What symptoms need emergency care?"),
    ]
    for i, (icon, label, query) in enumerate(topics):
        col = [q1, q2, q3][i % 3]
        with col:
            if st.button(f"{icon} {label}", key=f"qt_{i}", use_container_width=True):
                send_query(query)

# ══════════════════════════════════════════════════════════════════
#  PRESCRIPTION OCR
# ══════════════════════════════════════════════════════════════════
with st.expander("📋 Upload Prescription for Explanation", expanded=False):
    up = st.file_uploader("Prescription image", type=["png","jpg","jpeg","bmp","tiff"],
                          label_visibility="collapsed", key="presc_up")
    if up:
        st.image(up, caption="Your prescription", use_column_width=True)
        if st.button("🔍 Explain this prescription", use_container_width=True, key="ocr_go"):
            with st.spinner("Reading…"):
                txt = extract_prescription_text(up)
            if txt == "__IMPORT_ERROR__":
                st.error("Run: `python -m pip install pytesseract Pillow`")
            elif txt == "__TESSERACT_MISSING__":
                st.warning("Install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki")
            elif txt.startswith("__ERROR__"):
                st.error(txt)
            elif not txt:
                st.warning("No text found – try a clearer image.")
            else:
                send_query(f"Explain this prescription simply: {txt}")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════
#  CHAT HISTORY
# ══════════════════════════════════════════════════════════════════
engine = get_engine("llama3")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Text fallback input
if prompt := st.chat_input("Or type your health question here…"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# ══════════════════════════════════════════════════════════════════
#  AI RESPONSE
# ══════════════════════════════════════════════════════════════════
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        if engine:
            with st.spinner("🩺  Thinking…"):
                q = st.session_state.messages[-1]["content"]

                # Handle auto-listen toggle signals (not real queries)
                if q in ("__AUTOLISTEN_ON__", "__AUTOLISTEN_OFF__"):
                    st.session_state.auto_listen = q == "__AUTOLISTEN_ON__"
                    st.session_state.messages.pop()
                    st.rerun()

                hist = [
                    HumanMessage(content=m["content"]) if m["role"]=="user"
                    else AIMessage(content=m["content"])
                    for m in st.session_state.messages[-6:-1]
                ]
                try:
                    res = engine.invoke({"input": q, "chat_history": hist})
                    fmt = res.replace("###", "##")
                    st.markdown(fmt)
                    st.session_state.messages.append({"role": "assistant", "content": fmt})
                    st.session_state.tts_text = clean_for_tts(fmt)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.error("Engine offline. Make sure Ollama is running: `ollama run llama3`")

# ══════════════════════════════════════════════════════════════════
#  FOOTER
# ══════════════════════════════════════════════════════════════════
col_f1, col_f2 = st.columns([4, 1])
with col_f2:
    if st.button("🗑️ Clear Chat", use_container_width=True, key="clr"):
        clear_chat()

st.markdown("""
<div style="text-align:center;color:#475569;font-size:0.9rem;margin-top:3rem;padding-bottom:2rem;">
  ArogyaAI • Voice-First Healthcare • 🇮🇳 •
  <em>Not a substitute for professional medical advice</em>
</div>
""", unsafe_allow_html=True)
