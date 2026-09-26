"""
Trusted Medicals — Social Media Content Agent
Generates educational content for medical equipment sales.
Drafts → Review → Approve → Post workflow.
"""
import os, json, datetime, hashlib
from pathlib import Path
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# Load env from multiple locations
load_dotenv()  # local .env
load_dotenv(Path.home() / ".hermes" / ".env")  # Hermes env

# ── Config ──────────────────────────────────────────────────────────────
CLIENT = "Trusted Medicals"
NICHE = "Medical equipment sales and supplies"
TONE = "Educational — inform healthcare professionals and buyers"
PLATFORMS = ["Instagram", "Facebook", "WhatsApp Status"]
DRAFTS_DIR = Path(__file__).parent / "drafts"
TOPICS = [
    "Equipment maintenance tips",
    "How to choose the right equipment",
    "New medical technology trends",
    "Safety standards and regulations",
    "Equipment usage guides",
    "Cost-saving buying strategies",
    "Quality vs price considerations",
    "Industry certifications explained",
]
LLM_MODEL = "openai/gpt-4o"

os.makedirs(DRAFTS_DIR, exist_ok=True)


def get_llm():
    return ChatOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.getenv("OPENROUTER_API_KEY"),
        model=LLM_MODEL,
        temperature=0.8,
    )


# ── Content Generation Engine ───────────────────────────────────────────

PLATFORM_CONTEXT = {
    "Instagram": "Square image + short caption. Use emojis. 1-3 hashtags. Max 3 sentences.",
    "Facebook": "Longer educational post. 3-5 paragraphs. Can include links. Professional tone.",
    "WhatsApp Status": "Very short (1-2 sentences). Eye-catching. No hashtags. Use emojis.",
}

def generate_post(topic: str, platform: str) -> dict:
    """Generate a single post for a given platform on the given topic."""
    llm = get_llm()
    platform_guide = PLATFORM_CONTEXT.get(platform, "Standard social media post.")

    prompt = f"""You are a social media content creator for {CLIENT}, a company that sells medical equipment.

Topic: {topic}
Platform: {platform}
Tone: {TONE}
Format: {platform_guide}

Generate a complete post including:
1. The post text/caption
2. An AI image generation prompt (for creating a matching image via DALL-E or similar)

Return as JSON:
{{
  "platform": "{platform}",
  "topic": "{topic}",
  "headline": "...",
  "caption": "...",
  "image_prompt": "...",
  "hashtags": ["..."],
  "calls_to_action": "..."
}}"""

    response = llm.invoke([
        SystemMessage(content=f"You are an expert medical content creator specializing in {NICHE}. Always output valid JSON."),
        HumanMessage(content=prompt),
    ])

    # Parse response
    text = response.content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0]
    
    try:
        post = json.loads(text)
    except json.JSONDecodeError:
        # Fallback if LLM doesn't return clean JSON
        post = {
            "platform": platform,
            "topic": topic,
            "headline": topic,
            "caption": text[:500],
            "image_prompt": f"Medical equipment related to {topic}",
            "hashtags": ["#MedicalEquipment", "#Healthcare"],
            "calls_to_action": "Contact Trusted Medicals for more information.",
        }
    
    post["status"] = "draft"
    post["generated_at"] = datetime.datetime.now().isoformat()
    return post


def generate_daily_batch() -> list[dict]:
    """Generate a full day's worth of content (2 posts × up to 3 platforms)."""
    import random
    posts = []
    
    # Pick 2 topics for the day
    import random
    today_topics = random.sample(TOPICS, min(2, len(TOPICS)))
    
    for i, topic in enumerate(today_topics):
        for platform in PLATFORMS:
            post = generate_post(topic, platform)
            post["scheduled_time"] = SCHEDULE[i]  # 7am for first, 6pm for second
            posts.append(post)
    
    return posts


SCHEDULE = ["07:00", "18:00"]


def save_draft(post: dict):
    """Save a draft post to the drafts folder."""
    date_str = datetime.date.today().isoformat()
    time_str = post.get("scheduled_time", "00:00").replace(":", "")
    platform = post["platform"]
    safe_topic = post["topic"][:30].replace(" ", "-").replace("/", "-")
    filename = f"{date_str}_{time_str}_{platform}_{safe_topic}.json"
    filepath = DRAFTS_DIR / filename
    
    with open(filepath, "w") as f:
        json.dumps(post, f, indent=2)
    
    return filepath


def list_drafts(status: str = "draft") -> list[dict]:
    """List all drafts with a given status."""
    drafts = []
    for f in sorted(DRAFTS_DIR.glob("*.json")):
        with open(f) as fh:
            post = json.load(fh)
        if post.get("status") == status:
            drafts.append(post)
    return drafts


def approve_post(filename: str):
    """Mark a draft as approved (ready for posting)."""
    filepath = DRAFTS_DIR / filename
    with open(filepath) as f:
        post = json.load(f)
    post["status"] = "approved"
    post["approved_at"] = datetime.datetime.now().isoformat()
    with open(filepath, "w") as f:
        json.dump(post, f, indent=2)
    return post


def generate_batch_report():
    """Generate a full week of content and save all drafts."""
    import random
    all_posts = []
    
    for day_offset in range(7):
        day = datetime.date.today() + datetime.timedelta(days=day_offset)
        topics = random.sample(TOPICS, 2)
        
        for i, topic in enumerate(topics):
            for platform in PLATFORMS:
                post = generate_post(topic, platform)
                post["scheduled_date"] = day.isoformat()
                post["scheduled_time"] = SCHEDULE[i]
                save_draft(post)
                all_posts.append(post)
    
    return all_posts