# 🩺 ArogyaAI — Voice-First Healthcare Assistant

> A highly accessible, privacy-first healthcare assistant designed for the elderly and visually impaired. Features a continuous hands-free voice loop, prescription OCR reading, and local AI processing to ensure medical queries remain 100% private.

---

## 🚀 Key Features

ArogyaAI provides instant, voice-driven guidance on common symptoms, first aid, and basic medicine usage. 

- **🗣️ Bilingual Voice Loop**: Deeply integrated English and Tamil support. Tap the mic once for a hands-free conversational loop that listens, processes, and speaks back.
- **🚨 Emergency Protocol**: Automatically detects life-threatening symptoms (e.g., chest pain, breathing difficulty) and provides immediate, high-priority emergency instructions.
- **💊 Medication Reminders**: Users can set reminders via voice or text (e.g., "[REMINDER: Dolo 650, 08:30]"), which the assistant will announce at the correct time.
- **📸 Prescription Reader**: Advanced OCR (Tesseract) that scans medical prescriptions and explains dosage and purpose in simple terms.
- **👴 Elderly Mode**: A high-contrast, large-font interface specifically designed for low-vision and elderly users.
- **🔒 100% Private & Local**: Uses a local RAG pipeline and Ollama (Llama 3), ensuring health data never leaves the device.

---

## 🏗️ Architecture

```
Voice Input (Faster-Whisper) → Streamlit → LangChain Orchestrator
                                               ↓              ↓
                                        FAISS Vector DB    Ollama LLM (Llama 3)
                                               ↓              ↓
                        Voice Output (Edge-TTS) ← AI Response ← Health Knowledge Base
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | Streamlit (Custom Glassmorphic CSS) |
| **STT (Speech-to-Text)** | OpenAI Faster-Whisper (Local) |
| **TTS (Text-to-Speech)** | Microsoft Edge-TTS (Offline-ready) |
| **LLM (Brain)** | Ollama — Llama 3 (Local) |
| **Embeddings** | Ollama Embeddings |
| **Vector Store** | FAISS |
| **OCR** | Tesseract & Pillow (`pytesseract`) |
| **Orchestration** | LangChain (LCEL) |

---

## ⚙️ Setup & Installation

### 1. Prerequisites
- [Python 3.11+](https://www.python.org/downloads/)
- [Ollama](https://ollama.com/) installed and running locally.
- **Tesseract OCR**: Required for the prescription reading feature.
  - *Windows*: Download from [UB-Mannheim Tesserract](https://github.com/UB-Mannheim/tesseract/wiki).
  - *Note*: Ensure the path is set in `.env` or `app.py`.

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

---

## 📁 Project Structure

```
├── app.py            # Main application UI & Voice Pipeline logic
├── rag_utils.py      # RAG orchestrator, System Prompts, & Safety Logic
├── health_data.txt   # Medical Knowledge Base (Symptoms, Remedies, First Aid)
├── voice/            # Voice Engine (STT: Whisper, TTS: Edge-TTS)
├── data/             # FAISS Vector Index storage
└── requirements.txt  # Project dependencies
```

---

## 🛡️ Medical Safety Guardrails

ArogyaAI is programmed with strict safety protocols:
1. **No Diagnosis**: It never attempts to diagnose a disease officially.
2. **Emergency Recognition**: It aggressively detects emergency triggers and recommends immediate medical intervention.
3. **Internal Database Only**: All advice is strictly derived from the validated `health_data.txt` knowledge base.

---

## 📚 Knowledge Management

To update the assistant's medical knowledge, simply edit `health_data.txt`. The system will automatically re-index the data on the next startup.
