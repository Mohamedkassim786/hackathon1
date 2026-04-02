# RAG Engine - ArogyaAI Optimized Version
import os
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

load_dotenv()

DB_PATH = "data/faiss_index"

def get_rag_chain(model_name="llama3"):
    """
    Creates a RAG chain using local Ollama model.
    Loads and persists FAISS index to disk.
    """
    embeddings = OllamaEmbeddings(model=model_name)
    
    # Load or Create Vector Store
    if os.path.exists(os.path.join(DB_PATH, "index.faiss")):
        print(f"--- Loading existing FAISS index from {DB_PATH} ---")
        vector_store = FAISS.load_local(DB_PATH, embeddings, allow_dangerous_deserialization=True)
    else:
        print("--- Creating new FAISS index ---")
        try:
            with open("health_data.txt", "r", encoding="utf-8") as f:
                text = f.read()
        except FileNotFoundError:
            return None

        text_splitter = CharacterTextSplitter(chunk_size=700, chunk_overlap=100)
        docs = text_splitter.create_documents([text])
        vector_store = FAISS.from_documents(docs, embeddings)
        vector_store.save_local(DB_PATH)

    retriever = vector_store.as_retriever(search_kwargs={"k": 4})

    # Define Local LLM (Ollama) with optimization for repetition and variety
    llm = ChatOllama(
        model=model_name, 
        temperature=0.4, 
        repeat_penalty=1.1, # Slightly reduced to prevent early stopping
        num_predict=256 # Increased for longer Tamil responses
    )

    # Stricter, Natural Tamil/English System Prompt
    system_prompt = (
        "You are 'ArogyaAI', a kind Village Doctor. "
        "Your tone is warm, supportive, and uses simple spoken language.\n\n"
        "PRESCRIPTION OCR RULE:\n"
        "If the user input contains OCR text or starts with 'I have scanned...', SKIP the 'Village Doctor' intro.\n"
        "- ONLY provide the medicine details.\n"
        "- NO hospital names, NO doctor names, NO greetings, NO meta-notes.\n"
        "- Just provide the requested medicine list/table.\n\n"
        "EMERGENCY PROTOCOL:\n"
        "If you detect any life-threatening symptoms (e.g., chest pain, difficulty breathing, severe bleeding, unconsciousness):\n"
        "- START your response with: '🚨 EMERGENCY DETECTED: CALL 108 IMMEDIATELY.'\n"
        "- Give 1-2 life-saving steps (e.g., 'Sit down', 'Stay calm').\n"
        "- Keep it extremely short.\n\n"
        "GREETING RULE:\n"
        "- If the user input is a simple greeting (e.g., 'hi', 'hello', 'வணக்கம்'), respond with a warm welcome and ask how you can help today.\n"
        "- DO NOT give medical tips, summaries of your knowledge, or a general health guide unless the user asks a specific health question or mentions a symptom.\n\n"
        "STRICT LANGUAGE RULE:\n"
        "The user is speaking {language}. You MUST respond ONLY in {language} script.\n"
        "- If {language} is TAMIL: Use ONLY Tamil script (தமிழ்). Do NOT use English/Transliteration.\n"
        "- If {language} is ENGLISH: Use ONLY English characters. Do NOT use Tamil script.\n"
        "DO NOT MIX LANGUAGES.\n\n"
        "KNOWLEDGE: {context}\n\n"
        "ADDITIONAL RULES:\n"
        "1. NO META-NOTES: Do NOT include phrases like '(Note: I've responded...)' or '(I am a doctor)'. Just give the advice.\n"
        "2. BREVITY: Max 3 sentences (unless providing a medicine list or emergency steps). BE BRIEF.\n\n"
        "⏰ REMINDERS: If asked, append EXACTLY: [REMINDER: drug_name, HH:MM] (24h format).\n"
        "Current Time: {current_time}\n"
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt + "\n\nACTUAL USER LANGUAGE: {language}"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ])

    # LCEL Chain
    chain = (
        RunnablePassthrough.assign(
            context=(lambda x: x["input"]) | retriever | (lambda docs: "\n\n".join(d.page_content for d in docs))
        )
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain
