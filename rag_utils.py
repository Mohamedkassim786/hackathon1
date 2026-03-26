# RAG Engine - Ollama Version (2026 Compatible)
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
    No API keys required.
    """
    # Load knowledge base
    try:
        with open("aims_info.txt", "r") as f:
            text = f.read()
    except FileNotFoundError:
        return None

    # Split text
    text_splitter = CharacterTextSplitter(chunk_size=700, chunk_overlap=100)
    docs = text_splitter.create_documents([text])

    # Create vector store (Local)
    embeddings = OllamaEmbeddings(model=model_name)
    vector_store = FAISS.from_documents(docs, embeddings)
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})

    # Define Local LLM (Ollama)
    llm = ChatOllama(model=model_name, temperature=0.1)

    # Prompt Template
    system_prompt = (
        "You are 'Academia AI' - a professional, polite, and helpful academic assistant. "
        "Your goal is to assist users with queries related to admissions, programmes, facilities, and student services."
        "\n\n"
        "RELEVANT CONTEXT:\n{context}\n\n"
        "GUIDELINES:\n"
        "1. If a user asks about admissions, provide eligibility and process details.\n"
        "2. If booking a counselor session, follow the flow: Name -> Inquiry Type -> Preferred Time (One by one).\n"
        "3. Provide accurate information based ONLY on the provided context.\n"
        "4. If you don't know the answer, admit it politely and suggest contacting the admission office."
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
