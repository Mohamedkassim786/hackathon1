import sys
import pydantic
import streamlit as st
import os
from rag_utils import get_rag_chain
from langchain_core.messages import HumanMessage, AIMessage

# --- PRE-REQUISITE: HACKATHON PYDANTIC PATCH ---
try:
    if not hasattr(pydantic, "v1"):
        import pydantic.v1 as v1
        sys.modules["pydantic.v1"] = v1
except ImportError:
    sys.modules["pydantic.v1"] = pydantic

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="City AI • AIMS Dashboard",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- PREMIUM SAAS CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@300;400;500;600;700&display=swap');
    
    :root {
        --primary-accent: #6366f1;
        --secondary-accent: #a855f7;
        --bg-deep: #030712;
        --glass-bg: rgba(17, 25, 40, 0.6);
        --glass-border: rgba(255, 255, 255, 0.08);
        --text-primary: #f9fafb;
        --text-secondary: #9ca3af;
        --glow-strength: 20px;
    }

    /* Global Reset */
    .main {
        background-color: var(--bg-deep);
        color: var(--text-primary);
        font-family: 'Plus Jakarta Sans', sans-serif;
    }

    [data-testid="stAppViewContainer"] {
        background: radial-gradient(circle at 0% 0%, rgba(99, 102, 241, 0.08) 0%, transparent 40%),
                    radial-gradient(circle at 100% 100%, rgba(168, 85, 247, 0.08) 0%, transparent 40%),
                    var(--bg-deep);
        background-attachment: fixed;
    }

    /* Hide Streamlit elements */
    [data-testid="stHeader"] { background: transparent; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }

    /* Typography */
    h1, h2, h3 {
        font-family: 'Space Grotesk', sans-serif;
        color: var(--text-primary);
    }

    .hero-title {
        font-size: 3.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #fff 0%, #a855f7 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        line-height: 1.1;
        margin-bottom: 0.5rem;
    }

    .hero-subtitle {
        font-size: 1.2rem;
        color: var(--text-secondary);
        margin-bottom: 2rem;
    }

    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(16, 185, 129, 0.05);
        border: 1px solid rgba(16, 185, 129, 0.15);
        color: #10b981;
        padding: 6px 16px;
        border-radius: 100px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-bottom: 2rem;
    }

    /* Glass Cards */
    .glass-card {
        background: var(--glass-bg);
        backdrop-filter: blur(12px);
        border: 1px solid var(--glass-border);
        border-radius: 20px;
        padding: 1.5rem;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        cursor: pointer;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .glass-card:hover {
        transform: translateY(-8px) scale(1.02);
        border-color: rgba(99, 102, 241, 0.4);
        box-shadow: 0 20px 40px -12px rgba(0, 0, 0, 0.5),
                    0 0 20px rgba(99, 102, 241, 0.1);
    }

    /* Card Titles */
    .card-icon { font-size: 1.5rem; margin-bottom: 0.5rem; }
    .card-title { font-size: 1.1rem; font-weight: 700; color: #fff; margin-bottom: 0.25rem; }
    .card-desc { font-size: 0.85rem; color: var(--text-secondary); line-height: 1.4; }

    /* Quick Start Column */
    .quick-start-container {
        padding-left: 2rem;
        border-left: 1px solid rgba(255, 255, 255, 0.05);
    }

    /* Dividers */
    .glowing-divider {
        height: 1px;
        width: 100%;
        background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.2), transparent);
        margin: 3rem 0;
    }

    /* Chat Area */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.02) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        border-radius: 16px !important;
        padding: 1rem !important;
    }

    /* Chat Input */
    .stChatInputContainer {
        border-radius: 16px !important;
        border: 1px solid var(--glass-border) !important;
        background: rgba(255, 255, 255, 0.03) !important;
        backdrop-filter: blur(20px);
        transition: all 0.3s ease;
    }
    
    .stChatInputContainer:focus-within {
        border-color: var(--primary-accent) !important;
        box-shadow: 0 0 15px rgba(99, 102, 241, 0.15) !important;
    }

    /* Styled Buttons as Cards */
    .stButton > button {
        background: var(--glass-bg) !important;
        color: white !important;
        border: 1px solid var(--glass-border) !important;
        border-radius: 16px !important;
        padding: 1rem !important;
        text-align: left !important;
        display: block !important;
        width: 100% !important;
        transition: all 0.3s ease !important;
        height: auto !important;
    }

    .stButton > button:hover {
        border-color: var(--primary-accent) !important;
        transform: translateY(-4px) !important;
        background: rgba(99, 102, 241, 0.05) !important;
        box-shadow: 0 10px 20px -5px rgba(0, 0, 0, 0.3) !important;
    }
</style>
""", unsafe_allow_html=True)

# --- STATE MANAGEMENT ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "counselor_flow" not in st.session_state:
    st.session_state.counselor_flow = False

# --- UTILS ---
def clear_chat():
    st.session_state.messages = []
    st.session_state.counselor_flow = False
    st.rerun()

def send_query(text):
    st.session_state.messages.append({"role": "user", "content": text})
    st.session_state.counselor_flow = False
    st.rerun()

# --- CONTENT LOADING ---
@st.cache_resource
def get_engine(model):
    try:
        return get_rag_chain(model)
    except:
        return None

# --- HERO & NAVIGATION (2-COLUMN) ---
col_left, col_right = st.columns([0.65, 0.35])

with col_left:
    st.markdown('<div class="status-badge">● AI Engine Online • Private • Secure</div>', unsafe_allow_html=True)
    st.markdown('<h1 class="hero-title">City AI<br>AIMS Assistant</h1>', unsafe_allow_html=True)
    st.markdown('<p class="hero-subtitle">The next-generation intelligence layer for your academic journey. Streamlined, secure, and context-aware.</p>', unsafe_allow_html=True)

    st.markdown("### 🎓 Explore Ecosystem")
    # Explore Cards Grid
    exp_col1, exp_col2 = st.columns(2)
    
    explore_cards = [
        {"icon": "📝", "title": "Admissions", "desc": "Check eligibility and process", "query": "What is the admission and eligibility process?"},
        {"icon": "📚", "title": "Programmes", "desc": "Explore courses and durations", "query": "List all available programmes and courses"},
        {"icon": "🏫", "title": "Facilities", "desc": "Campus labs and digital library", "query": "Tell me about the campus facilities and infrastructure"},
        {"icon": "📖", "title": "Services", "desc": "Mentorship and student portal", "query": "What academic services and practices do you offer?"},
        {"icon": "💼", "title": "Placements", "desc": "Average package and recruiters", "query": "What are the student outcomes and placement stats?"},
        {"icon": "🧑‍🏫", "title": "Counselor", "desc": "Book an academic session", "action": "counselor"}
    ]

    for i, card in enumerate(explore_cards):
        target_col = exp_col1 if i % 2 == 0 else exp_col2
        with target_col:
            if st.button(f"{card['icon']} {card['title']}\n{card['desc']}", key=f"exp_{i}", use_container_width=True):
                if card.get("action") == "counselor":
                    st.session_state.counselor_flow = True
                    # We don't rerun yet, let the UI handle it below
                else:
                    send_query(card["query"])

with col_right:
    st.markdown('<div class="quick-start-container">', unsafe_allow_html=True)
    st.markdown("### ✨ Try Asking")
    
    quick_queries = [
        {"title": "UG Eligibility", "q": "What are the eligibility criteria for undergraduate programmes?"},
        {"title": "PG Eligibility", "q": "What are the eligibility criteria for postgraduate programmes?"},
        {"title": "B.Tech CS Info", "q": "Tell me about B.Tech in Computer Science"},
        {"title": "Placement Average", "q": "What is the average placement package?"},
        {"title": "Digital Library", "q": "Tell me about the digital library facilities"}
    ]

    for i, item in enumerate(quick_queries):
        if st.button(f"🚀 {item['title']}", key=f"quick_{i}", use_container_width=True):
            send_query(item["q"])
    
    st.markdown('<br>', unsafe_allow_html=True)
    if st.button("🗑️ Reset Assistant", use_container_width=True):
        clear_chat()
    st.markdown('</div>', unsafe_allow_html=True)

# --- DIVIDER ---
st.markdown('<div class="glowing-divider"></div>', unsafe_allow_html=True)

# --- COUNSELOR FORM (CONDITIONAL) ---
if st.session_state.counselor_flow:
    st.markdown("### 🧑‍🏫 Book an Academic Session")
    with st.container(border=True):
        with st.form("book_form"):
            f_col1, f_col2 = st.columns(2)
            name = f_col1.text_input("Student Name")
            inquiry = f_col2.selectbox("Inquiry Type", ["Admission", "Course Choice", "Career Guidance"])
            f_date = f_col1.date_input("Preferred Date")
            f_time = f_col2.time_input("Preferred Time")
            
            if st.form_submit_button("Submit Request", use_container_width=True):
                if name:
                    st.success(f"✅ Success! Counseling request for {name} has been submitted.")
                    st.balloons()
                else:
                    st.error("Please provide your name.")
        if st.button("Close Form"):
            st.session_state.counselor_flow = False
            st.rerun()

# --- CHAT INTERFACE ---
engine = get_engine("llama3")

# Display Messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            st.markdown(message["content"])
        else:
            st.markdown(f"**{message['content']}**")

# Handle new user input
if prompt := st.chat_input("Message AIMS Assistant..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.rerun()

# AI Reaction
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    with st.chat_message("assistant"):
        if engine:
            with st.spinner("Analyzing knowledge bank..."):
                current_q = st.session_state.messages[-1]["content"]
                history = [
                    HumanMessage(content=m["content"]) if m["role"]=="user" else AIMessage(content=m["content"])
                    for m in st.session_state.messages[-5:-1]
                ]
                try:
                    res = engine.invoke({"input": current_q, "chat_history": history})
                    # Polish response
                    formatted = res.replace("###", "##").replace("1.", "\n- 📍").replace("2.", "\n- 📍").replace("3.", "\n- 📍")
                    st.markdown(formatted)
                    st.session_state.messages.append({"role": "assistant", "content": formatted})
                    st.rerun()
                except Exception as e:
                    st.error(f"Engine Error: {e}")
        else:
            st.error("Engine disconnected. Check connectivity.")

# Footer
st.markdown("""
<div style="text-align: center; color: var(--text-secondary); font-size: 0.8rem; margin-top: 6rem; padding-bottom: 2rem;">
    Enterprise Standard AIMS Assistant • v3.8 Platinum • Private LLM Instance
</div>
""", unsafe_allow_html=True)
