"""
FAQ/RAG Agent — Document Ingestion Pipeline
Loads documents (PDF, web, text), chunks them, embeds, and stores in ChromaDB.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, PyPDFLoader, WebBaseLoader
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

load_dotenv()
load_dotenv(Path.home() / ".hermes" / ".env")

CHROMA_DIR = Path(__file__).parent.parent / "data" / "chroma_db"
DATA_DIR = Path(__file__).parent.parent / "data" / "source"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200

os.makedirs(CHROMA_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)


def get_embeddings():
    return OpenAIEmbeddings(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        model="openai/text-embedding-3-small",
    )


def get_vectorstore():
    """Get or create the Chroma vector store."""
    return Chroma(
        persist_directory=str(CHROMA_DIR),
        embedding_function=get_embeddings(),
    )


def ingest_text(text: str, source: str = "manual") -> int:
    """Ingest raw text into the vector store."""
    from langchain_core.documents import Document
    docs = [Document(page_content=text, metadata={"source": source})]
    return _ingest_documents(docs)


def ingest_file(filepath: str) -> int:
    """Ingest a file (PDF or .txt) into the vector store."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    
    if path.suffix.lower() == ".pdf":
        loader = PyPDFLoader(str(path))
    elif path.suffix.lower() == ".txt":
        loader = TextLoader(str(path), encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {path.suffix}")
    
    docs = loader.load()
    return _ingest_documents(docs)


def ingest_web(url: str) -> int:
    """Ingest a webpage into the vector store."""
    loader = WebBaseLoader(url)
    docs = loader.load()
    return _ingest_documents(docs)


def _ingest_documents(docs: list) -> int:
    """Split and store documents in ChromaDB."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    
    # Add metadata
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = i
    
    # Store in ChromaDB
    vectorstore = get_vectorstore()
    vectorstore.add_documents(chunks)
    vectorstore.persist()
    
    return len(chunks)


def replace_source(text: str, source: str = "client-knowledge") -> int:
    """Replace all content from a source with new text (delete + re-ingest in place)."""
    from langchain_core.documents import Document
    
    vectorstore = get_vectorstore()
    try:
        # Delete existing chunks from this source
        vectorstore.delete(where={"source": source})
    except Exception:
        pass  # No existing chunks yet
    
    docs = [Document(page_content=text, metadata={"source": source})]
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = i
    
    vectorstore.add_documents(chunks)
    return len(chunks)


def clear_knowledge_base():
    """Remove all documents from the vector store."""
    import shutil
    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)
    os.makedirs(CHROMA_DIR, exist_ok=True)
    print(f"🧹 Knowledge base cleared.")


def get_stats() -> dict:
    """Get stats about the knowledge base."""
    try:
        vectorstore = get_vectorstore()
        count = vectorstore._collection.count()
        return {"chunks": count, "chroma_dir": str(CHROMA_DIR)}
    except Exception as e:
        return {"error": str(e), "chunks": 0}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python ingest.py <command> [args]")
        print("  web URL        — Ingest a webpage")
        print("  file PATH      — Ingest a file (.pdf, .txt)")
        print("  text \"TEXT\"    — Ingest raw text")
        print("  clear          — Clear knowledge base")
        print("  stats          — Show knowledge base stats")
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == "web":
        n = ingest_web(sys.argv[2])
        print(f"✅ Ingested {n} chunks from {sys.argv[2]}")
    elif cmd == "file":
        n = ingest_file(sys.argv[2])
        print(f"✅ Ingested {n} chunks from {sys.argv[2]}")
    elif cmd == "text":
        n = ingest_text(sys.argv[2])
        print(f"✅ Ingested {n} chunks from text")
    elif cmd == "clear":
        clear_knowledge_base()
    elif cmd == "stats":
        print(get_stats())
    else:
        print(f"Unknown command: {cmd}")