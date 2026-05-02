"""
Web Research Engine — Tavily search + Gemini summarization.
Runs on APScheduler every N hours. Updates interest.latest_news in ChromaDB.
"""

import asyncio
from datetime import datetime
from backend.config import settings
from backend.memory.chroma_store import get_interests, save_interests
from backend.llm.facade import simple_call
from backend.db.models import SessionLocal
from backend.db.crud import get_all_users


def _search_tavily(topic: str) -> str:
    """Call Tavily search API synchronously."""
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.tavily_api_key)
        result = client.search(
            query=f"Latest news about {topic} today",
            search_depth="basic",
            max_results=3
        )
        # Combine result snippets
        snippets = [r.get("content", "") for r in result.get("results", [])]
        return " ".join(snippets)[:1500]
    except Exception as e:
        return ""


def _summarize_for_user(topic: str, raw_text: str, user_name: str) -> str:
    """Ask Gemini to create a short, exciting update for the user."""
    if not raw_text.strip():
        return ""
    prompt = f"""
You are Jack, a friendly AI companion. Summarize this news about "{topic}" in ONE sentence, 
written in an exciting casual way for {user_name}. Do NOT say "as Jack" — just write the summary.

News: {raw_text}

One-sentence summary:"""
    try:
        return simple_call(prompt).strip()
    except Exception:
        return ""


def research_all_users():
    """
    Main scheduler job: research top interests for every user and update news.
    Run every RESEARCH_INTERVAL_HOURS hours.
    """
    if not settings.tavily_api_key or settings.tavily_api_key == "your_tavily_api_key_here":
        print("[Research] Tavily API key not set — skipping research cycle.")
        return

    db = SessionLocal()
    try:
        users = get_all_users(db)
        for user in users:
            _research_user(user.id, user.name)
    finally:
        db.close()


def _research_user(user_id: str, user_name: str):
    interests = get_interests(user_id)
    if not interests:
        return

    # Sort by intensity, take top 3
    top = sorted(interests, key=lambda x: x.get("intensity", 0), reverse=True)[:3]
    now = datetime.utcnow().isoformat()
    updated = False

    for entry in top:
        topic = entry["topic"]
        print(f"[Research] Searching: {topic} for {user_name}")
        raw = _search_tavily(topic)
        if raw:
            summary = _summarize_for_user(topic, raw, user_name)
            if summary:
                entry["latest_news"] = summary
                entry["news_fetched_at"] = now
                updated = True

    if updated:
        save_interests(user_id, interests)
        print(f"[Research] Updated interests for {user_name}")
