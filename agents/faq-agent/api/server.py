"""
FAQ/RAG Agent — FastAPI Server
Provides a REST API for ingesting documents and asking questions.
"""
import os, sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, UploadFile, File
from pydantic import BaseModel
from pipeline.ingest import ingest_text, ingest_file, ingest_web, clear_knowledge_base, get_stats
from pipeline.query import ask

app = FastAPI(title="Task-ally FAQ Agent", version="1.0.0")


class AskRequest(BaseModel):
    question: str
    k: int = 5


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: list[str] = []
    has_context: bool = False


class IngestWebRequest(BaseModel):
    url: str


class IngestTextRequest(BaseModel):
    text: str
    source: str = "manual"


# ── Health ─────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "agent": "Task-ally FAQ Agent"}


# ── Query ──────────────────────────────────────────────────────────────

@app.post("/ask", response_model=AskResponse)
def ask_question(req: AskRequest):
    """Ask a question and get an answer from the knowledge base."""
    result = ask(req.question, k=req.k)
    return AskResponse(
        question=result["question"],
        answer=result["answer"],
        sources=result.get("sources", []),
        has_context=result.get("has_context", False),
    )


@app.get("/ask")
def ask_question_get(q: str, k: int = 5):
    """Ask a question via GET parameter."""
    result = ask(q, k=k)
    return AskResponse(
        question=result["question"],
        answer=result["answer"],
        sources=result.get("sources", []),
        has_context=result.get("has_context", False),
    )


# ── Ingest ─────────────────────────────────────────────────────────────

@app.post("/ingest/web")
def ingest_webpage(req: IngestWebRequest):
    """Ingest a webpage into the knowledge base."""
    try:
        n = ingest_web(req.url)
        return {"status": "ok", "chunks_added": n, "url": req.url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/ingest/text")
def ingest_text_endpoint(req: IngestTextRequest):
    """Ingest raw text into the knowledge base."""
    try:
        n = ingest_text(req.text, source=req.source)
        return {"status": "ok", "chunks_added": n}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/ingest/file")
async def ingest_file_endpoint(file: UploadFile = File(...)):
    """Upload and ingest a file (PDF or TXT)."""
    filepath = Path(__file__).parent.parent / "data" / "source" / file.filename
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    
    try:
        n = ingest_file(str(filepath))
        return {"status": "ok", "chunks_added": n, "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# ── Management ─────────────────────────────────────────────────────────

@app.post("/knowledge/clear")
def clear():
    """Clear the entire knowledge base."""
    clear_knowledge_base()
    return {"status": "ok", "message": "Knowledge base cleared"}


@app.get("/knowledge/stats")
def stats():
    """Get knowledge base statistics."""
    return get_stats()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)