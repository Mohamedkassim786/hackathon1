# RAG Engine - ArogyaAI Healthcare Version (2026 Compatible)
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import CharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

load_dotenv()

def get_rag_chain(model_name="llama3"):
    """
    Creates a RAG chain using local Ollama model.
    Loads health_data.txt as the healthcare knowledge base.
    No API keys required.
    """
    # Load healthcare knowledge base
    try:
        with open("health_data.txt", "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        return None

    # Split text into retrieval chunks
    text_splitter = CharacterTextSplitter(chunk_size=700, chunk_overlap=100)
    docs = text_splitter.create_documents([text])

    # Create local vector store
    embeddings = OllamaEmbeddings(model=model_name)
    vector_store = FAISS.from_documents(docs, embeddings)
    retriever = vector_store.as_retriever(search_kwargs={"k": 4})

    # Define Local LLM (Ollama)
    llm = ChatOllama(model=model_name, temperature=0.1)

    # ArogyaAI Healthcare System Prompt
    system_prompt = (
        "You are ArogyaAI, a helpful and caring healthcare assistant. "
        "Your purpose is to provide simple, safe, and easy-to-understand health guidance to the general public.\n\n"
        "RELEVANT HEALTH KNOWLEDGE:\n{context}\n\n"
        "STRICT GUIDELINES — FOLLOW THESE ALWAYS:\n"
        "1. Provide simple, clear, and safe health information based on the context provided.\n"
        "2. DO NOT provide a medical diagnosis under any circumstances.\n"
        "3. For any serious, severe, or emergency symptoms, ALWAYS advise the user to consult a qualified doctor or call emergency services immediately.\n"
        "4. Keep your responses short, friendly, and easy to understand — use bullet points where appropriate.\n"
        "5. If the information is not in your knowledge base, honestly say so and recommend seeing a healthcare professional.\n"
        "6. Never recommend prescription medications without noting that a doctor's prescription is required.\n"
        "7. Always be empathetic and reassuring in tone."
    )

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ])

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    # LCEL Chain (Pydantic V2 Compatible)
    chain = (
        RunnablePassthrough.assign(
            context=(lambda x: x["input"]) | retriever | format_docs
        )
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain
