"""
FAQ Agent — Client Dashboard
Lets the client manage knowledge base content and monitor questions via a simple web UI.
Single admin password (set via DASHBOARD_PASSWORD env, default: change-me).
"""
import json, secrets, os, sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Knowledge store
DATA_DIR = Path(__file__).parent.parent / "data"
KNOWLEDGE_FILE = DATA_DIR / "knowledge.json"
QUESTION_LOG = DATA_DIR / "question_log.jsonl"
SESSIONS: dict[str, datetime] = {}  # token -> expiry

DATA_DIR.mkdir(exist_ok=True)

DEFAULT_KNOWLEDGE = {
    "company_name": "Your Store Name",
    "about": "Describe your business here...",
    "products": "List your products and prices...\n- Product 1: price\n- Product 2: price",
    "delivery": "Delivery info: areas, cost, timing...",
    "payment": "Accepted payment methods...",
    "returns": "Returns and refund policy...",
    "contact": "Phone, WhatsApp, email, hours...",
    "faqs": "Common questions and answers...\nQ: Question?\nA: Answer.",
}

ADMIN_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "change-me-now")


def load_knowledge() -> dict:
    if KNOWLEDGE_FILE.exists():
        return json.loads(KNOWLEDGE_FILE.read_text())
    return dict(DEFAULT_KNOWLEDGE)


def save_knowledge(knowledge: dict):
    KNOWLEDGE_FILE.write_text(json.dumps(knowledge, indent=2))


def knowledge_to_text(knowledge: dict) -> str:
    """Convert knowledge dict into ingestable text."""
    sections = []
    for key, label in [
        ("company_name", "Company"),
        ("about", "About"),
        ("products", "Products & Prices"),
        ("delivery", "Delivery"),
        ("payment", "Payment"),
        ("returns", "Returns & Refunds"),
        ("contact", "Contact"),
        ("faqs", "FAQs"),
    ]:
        val = knowledge.get(key, "").strip()
        if val:
            sections.append(f"{label}:\n{val}")
    return "\n\n".join(sections)


def log_question(question: str, answer: str, sources: list[str] | None = None):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "question": question,
        "answer": answer[:500],
        "sources": sources or [],
    }
    with open(QUESTION_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def get_question_log(limit: int = 50) -> list[dict]:
    if not QUESTION_LOG.exists():
        return []
    entries = []
    for line in reversed(QUESTION_LOG.read_text().splitlines()):
        if line.strip():
            entries.append(json.loads(line))
        if len(entries) >= limit:
            break
    return entries


# ── Auth helpers ────────────────────────────────────────────────────────

def make_session() -> str:
    token = secrets.token_hex(16)
    SESSIONS[token] = datetime.now()
    return token


def is_authed(request: Request) -> bool:
    token = request.cookies.get("session")
    if not token or token not in SESSIONS:
        return False
    # Sessions expire after 24h
    if (datetime.now() - SESSIONS[token]).total_seconds() > 86400:
        SESSIONS.pop(token, None)
        return False
    return True


# ── Dashboard app ───────────────────────────────────────────────────────

dashboard = FastAPI(title="Task-ally Agent Dashboard")


class LoginRequest(BaseModel):
    password: str


class KnowledgeUpdate(BaseModel):
    knowledge: dict


@dashboard.get("/", response_class=HTMLResponse)
def dashboard_home():
    html = (Path(__file__).parent.parent / "static" / "dashboard.html").read_text()
    return HTMLResponse(html)


@dashboard.post("/api/login")
def login(req: LoginRequest, response: Response):
    if req.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Wrong password")
    token = make_session()
    response.set_cookie("session", token, httponly=True, max_age=86400)
    return {"status": "ok"}


@dashboard.get("/api/knowledge")
def get_knowledge(request: Request):
    if not is_authed(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return load_knowledge()


@dashboard.post("/api/knowledge")
def update_knowledge(req: KnowledgeUpdate, request: Request):
    if not is_authed(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    knowledge = {**load_knowledge(), **req.knowledge}
    save_knowledge(knowledge)

    # Re-ingest into the agent's knowledge base (replace old client content in place)
    from pipeline.ingest import replace_source
    try:
        n = replace_source(knowledge_to_text(knowledge), source="client-knowledge")
        return {"status": "ok", "chunks_ingested": n}
    except Exception as e:
        return {"status": "ok", "warning": f"Saved but ingest failed: {e}"}


@dashboard.get("/api/questions")
def questions(request: Request, limit: int = 50):
    if not is_authed(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    return {"questions": get_question_log(limit)}


@dashboard.get("/api/stats")
def stats(request: Request):
    if not is_authed(request):
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        from pipeline.ingest import get_stats
        kb_stats = get_stats()
    except Exception:
        kb_stats = {"chunks": 0}
    log = get_question_log(limit=1000)
    return {
        "knowledge_chunks": kb_stats.get("chunks", 0),
        "questions_answered": len(log),
        "last_question": log[0]["timestamp"] if log else None,
    }