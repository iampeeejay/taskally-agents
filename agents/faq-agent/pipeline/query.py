"""
FAQ/RAG Agent — Query Pipeline
Retrieves relevant context from ChromaDB and generates answers via LLM.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

load_dotenv()
load_dotenv(Path.home() / ".hermes" / ".env")

CHROMA_DIR = Path(__file__).parent.parent / "data" / "chroma_db"
LLM_MODEL = "openai/gpt-4o"


def get_llm():
    return ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        model=LLM_MODEL,
        temperature=0.3,
    )


def get_retriever(k: int = 5):
    """Get a vector store retriever."""
    embeddings = OpenAIEmbeddings(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        model="openai/text-embedding-3-small",
    )
    vectorstore = Chroma(
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings,
    )
    return vectorstore.as_retriever(search_kwargs={"k": k})


def ask(question: str, k: int = 5) -> dict:
    """
    Ask a question and get an answer grounded in the knowledge base.
    Returns dict with answer, sources, and context.
    """
    llm = get_llm()
    retriever = get_retriever(k)
    
    # Retrieve relevant documents
    docs = retriever.invoke(question)
    
    if not docs:
        return {
            "question": question,
            "answer": "I don't have any information about that yet. Please upload relevant documents first.",
            "sources": [],
            "has_context": False,
        }
    
    # Build context from retrieved docs
    context_parts = []
    sources = []
    seen_sources = set()
    
    for doc in docs:
        source = doc.metadata.get("source", "unknown")
        if source not in seen_sources:
            sources.append(source)
            seen_sources.add(source)
        context_parts.append(f"[Source: {source}]\n{doc.page_content}")
    
    context = "\n\n---\n\n".join(context_parts)
    
    # Generate answer
    system_prompt = """You are a helpful customer support agent. Answer the question based ONLY on the provided context.
If the context doesn't contain enough information to answer, say so honestly.
Always cite the source document name. Be concise and professional."""
    
    user_prompt = f"""Context:
{context}

Question: {question}

Answer based on the context above:"""
    
    response = llm.invoke([
        ("system", system_prompt),
        ("human", user_prompt),
    ])
    
    return {
        "question": question,
        "answer": response.content,
        "sources": sources,
        "context_chunks": len(docs),
        "has_context": True,
    }


if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 2:
        print("Usage: python query.py \"Your question here\"")
        sys.exit(1)
    
    question = " ".join(sys.argv[1:])
    result = ask(question)
    print(f"\nQ: {result['question']}")
    print(f"\nA: {result['answer']}")
    if result.get("sources"):
        print(f"\n📚 Sources: {', '.join(result['sources'])}")