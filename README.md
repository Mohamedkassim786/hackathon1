# 🩺 ArogyaAI — Voice-First Healthcare Assistant

> A highly accessible, privacy-first healthcare assistant designed for the elderly and visually impaired. Features a continuous hands-free voice loop, prescription OCR reading, and local AI processing to ensure medical queries remain 100% private.

---

## 🚀 What It Does

ArogyaAI provides instant, voice-driven guidance on common symptoms, first aid, and basic medicine usage. 
It uses a completely local RAG (Retrieval-Augmented Generation) pipeline, meaning no sensitive health questions ever leave the user's computer.

### Key Accessibility Features:
- **Continuous Voice Loop**: Tap the mic once, and it stays locked in a conversational loop. It listens, processes, speaks the answer aloud, and instantly starts listening again.
- **Hands-Free & Big UI**: Giant pulsing microphone, large fonts (20px base), and high-contrast design.
- **Prescription Reader**: Upload a photo of a medical prescription, and ArogyaAI will use OCR to read and explain it simply.

---

## 🏗️ Architecture

```
Voice Input (Web Speech API) → Streamlit → LangChain Orchestrator
                                              ↓              ↓
                                       FAISS Vector DB    Ollama LLM (Llama 3)
                                              ↓              ↓
                        Voice Output (TTS) ← AI Response ← Health Knowledge Base
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Streamlit (Custom JS / CSS for Voice) |
| **Voice** | Native Browser Web Speech API (STT & TTS) |
| **OCR** | Tesseract & Pillow (`pytesseract`) |
| **Orchestration** | LangChain (LCEL) |
| **Vector Store** | FAISS |
| **LLM** | Ollama — Llama 3 (Local) |
| **Embeddings** | Ollama Embeddings |

---

## ⚙️ Setup & Installation

### 1. Prerequisites
- [Python 3.11+](https://www.python.org/downloads/)
- [Ollama](https://ollama.com/) installed and running locally.
- **Tesseract OCR**: Required for the prescription reading feature.
  - *Windows*: Download and install from [UB-Mannheim Tesseract](https://github.com/UB-Mannheim/tesseract/wiki).
  - *Linux*: `sudo apt install tesseract-ocr`
  - *Mac*: `brew install tesseract`

### 2. Pull the LLM Model
```bash
ollama pull llama3
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the App
```bash
streamlit run app.py
```
*Note: Please use Google Chrome or Microsoft Edge for full Voice API support. Firefox is not fully supported.*

---

## 📁 Project Structure

```
├── app.py            # Main Streamlit UI, Voice Javascript handlers, Layout
├── rag_utils.py      # RAG pipeline + System Prompts + Safety Guardrails
├── health_data.txt   # Medical knowledge base (Symptoms, First Aid, etc.)
├── requirements.txt  # Python dependencies (includes pytesseract & Pillow)
└── README.md         # Documentation
```

---

## 🛡️ Medical Safety Guardrails

ArogyaAI is programmed with strict safety guardrails:
1. It will **never** attempt to diagnose a disease.
2. It prioritizes severe symptom recognition and will aggressively recommend visiting a doctor or calling emergency services for warning signs (e.g., chest pain, severe bleeding).
3. All advice is generalized from the internal database and includes disclaimers that it is not a substitute for professional medical care.

---

## 📚 Updating the Knowledge Base

To add more medical context, simply edit `health_data.txt`. The FAISS vector database will automatically rebuild the next time you start the app.
