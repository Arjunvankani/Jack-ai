"""
Sliding Window Conversation Memory — 3-tier architecture.

Tier 1: HOT WINDOW  — last N turns in RAM, sent to Gemini every call
Tier 2: SESSION SUMMARY — when window overflows, oldest chunk is compressed
Tier 3: LONG-TERM (ChromaDB) — after session ends, key facts stored permanently
"""

from collections import defaultdict
from datetime import datetime
from backend.config import settings
from backend.db.models import SessionLocal
from backend.db.crud import save_chat_message, get_chat_history

# In-memory hot windows: { user_id: [ {role, content, timestamp}, ... ] }
_hot_windows: dict[str, list[dict]] = defaultdict(list)

# Per-user session summaries (in-memory within a session)
_session_summaries: dict[str, str] = {}

MAX_HOT_TURNS = settings.max_hot_turns
COMPRESS_TRIGGER = MAX_HOT_TURNS          # compress when we hit this
COMPRESS_KEEP = MAX_HOT_TURNS // 2        # keep the most recent half


def add_turn(user_id: str, role: str, content: str):
    """Append a turn to this user's hot window and persist to SQLite."""
    now = datetime.utcnow()
    turn = {
        "role": role,
        "content": content,
        "ts": now.isoformat()
    }
    _hot_windows[user_id].append(turn)
    
    # Persist to SQLite
    db = SessionLocal()
    try:
        save_chat_message(db, user_id, role, content)
    finally:
        db.close()


def _ensure_loaded(user_id: str):
    """If RAM cache is empty, try to load the last N turns from SQLite."""
    if not _hot_windows[user_id]:
        db = SessionLocal()
        try:
            history = get_chat_history(db, user_id, limit=MAX_HOT_TURNS)
            if history:
                _hot_windows[user_id] = [
                    {"role": m.role, "content": m.content, "ts": m.timestamp.isoformat()}
                    for m in history
                ]
        finally:
            db.close()


def get_window(user_id: str) -> list[dict]:
    """
    Return the context window to pass to Gemini.
    If window is too long, compress oldest half and slide.
    Injects session summary at top if one exists.
    """
    _ensure_loaded(user_id)
    window = _hot_windows[user_id]

    # Auto-compress when limit is hit
    if len(window) >= COMPRESS_TRIGGER:
        _compress_oldest(user_id)

    # Build context: optional summary + hot turns (role/content only for Gemini)
    context = []
    if user_id in _session_summaries:
        context.append({
            "role": "user",
            "content": f"[Earlier in this conversation]: {_session_summaries[user_id]}"
        })
        context.append({
            "role": "model",
            "content": "Got it, I remember what we talked about earlier."
        })

    context += [{"role": t["role"], "content": t["content"]} for t in window]
    return context


def _compress_oldest(user_id: str):
    """
    Compress the oldest half of the window into a summary string.
    The summary is stored in _session_summaries and will be injected
    at the top of the next context window.
    Called internally when the window is full.
    """
    window = _hot_windows[user_id]
    oldest = window[:COMPRESS_KEEP]
    keep   = window[COMPRESS_KEEP:]

    # Build a plain-text summary of the oldest turns
    summary_lines = []
    for t in oldest:
        label = "User" if t["role"] == "user" else "Jack"
        summary_lines.append(f"{label}: {t['content']}")

    # We'll call Gemini to compress — done lazily via gemini_client to avoid circular import
    raw_text = "\n".join(summary_lines)
    _session_summaries[user_id] = f"Summary of earlier chat: {raw_text[:800]}"  # fallback truncation
    _hot_windows[user_id] = keep


def set_compressed_summary(user_id: str, summary: str):
    """
    Called by the Gemini client after it compresses the oldest turns.
    Replaces the fallback truncation with a proper LLM-generated summary.
    """
    _session_summaries[user_id] = summary


def get_session_summary(user_id: str) -> str | None:
    return _session_summaries.get(user_id)


def clear_session(user_id: str):
    """Called when a conversation ends (silence detected). Returns full history for Tier 3 extraction."""
    history = list(_hot_windows[user_id])
    _hot_windows[user_id].clear()
    _session_summaries.pop(user_id, None)
    return history


def get_raw_history(user_id: str) -> list[dict]:
    return list(_hot_windows[user_id])
