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

    # Define Local LLM (Ollama)
    llm = ChatOllama(model=model_name, temperature=0.1)

    # ArogyaAI Healthcare System Prompt - Extreme Brevity Edition
    system_prompt = (
        "You are ArogyaAI, a concise healthcare assistant.\n"
        "RELEVANT KNOWLEDGE: {context}\n\n"
        "STRICT RULES:\n"
        "1. Respond in 1-2 SHORT sentences MAX.\n"
        "2. Be conversational but extremely brief (Google Assistant style).\n"
        "3. Ask only ONE follow-up question if necessary.\n"
        "4. No medical diagnosis. Recommend doctors for severe cases.\n"
        "5. No markdown or complex formatting."
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ])

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    # LCEL Chain
    chain = (
        RunnablePassthrough.assign(
            context=(lambda x: x["input"]) | retriever | format_docs
        )
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain
