"""
Extracts interests + memories from conversation turns using Gemini,
then updates ChromaDB and SQLite.
"""

import json
import re
from datetime import datetime
from backend.memory.chroma_store import get_interests, save_interests, store_memory
from backend.db.models import SessionLocal
from backend.db.crud import update_user_interests


def _extract_json(text: str) -> list | dict | None:
    """Extract JSON from text using regex, handling conversational padding."""
    # Find anything between [...] or {...}
    match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            return None
    return None


def update_interests_from_text(user_id: str, text: str, gemini_fn):
    """
    Ask Gemini to extract interests mentioned in `text`.
    gemini_fn: a callable(prompt) -> str  (simple Gemini text call)
    """
    # OPTIMIZATION: Skip short or trivial messages to save API quota
    if len(text.strip()) < 15:
        return

    prompt = f"""
Extract the user's interests, mood, family/pet details, and lifestyle facts.
Be EXTREMELY thorough. Capture everything: food (mango, dhokla), hobbies (chess, reels), achievements (National level), and habits.

Return ONLY a JSON object:
{{
  "interests": [
    {{"topic": "National Chess", "category": "achievement", "excited": true}},
    {{"topic": "Mango", "category": "food", "excited": false}}
  ],
  "mood": "relaxed",
  "relationships": {{"family": "taking a nap"}},
  "memories": ["User played in a national chess tournament", "User likes eating dhokla"]
}}
Mood: happy, sad, relaxed, focused, etc.
Relationships: any info about family/pets.
Memories: factual statements.

Text: "{text}"
"""
    try:
        raw = gemini_fn(prompt)
        data = _extract_json(raw)
    except Exception:
        return

    if not data or not isinstance(data, dict):
        return

    # 1. Update Interests
    new_items = data.get("interests", [])
    existing = get_interests(user_id)
    existing_map = {i["topic"].lower(): i for i in existing}
    now = datetime.utcnow().isoformat()

    for item in new_items:
        if not isinstance(item, dict) or "topic" not in item:
            continue
        key = item["topic"].lower()
        excited = item.get("excited", False)
        
        if key in existing_map:
            entry = existing_map[key]
            entry["mention_count"] = entry.get("mention_count", 0) + 1
            entry["last_mentioned"] = now
            entry["intensity"] = _calc_intensity(entry["mention_count"], 0, excited)
        else:
            existing_map[key] = {
                "topic": item["topic"],
                "category": item.get("category", "general"),
                "intensity": _calc_intensity(1, 0, excited),
                "mention_count": 1,
                "last_mentioned": now,
                "latest_news": None,
                "news_fetched_at": None
            }

    updated_list = list(existing_map.values())
    save_interests(user_id, updated_list)
    
    # 2. Sync to SQLite (Interests, Mood, Relationships)
    db = SessionLocal()
    try:
        from backend.db.crud import get_user
        user = get_user(db, user_id)
        if user:
            user.interests = updated_list
            user.current_mood = data.get("mood", user.current_mood)
            
            # Merge relationships
            rels = dict(user.relationships or {})
            new_rels = data.get("relationships", {})
            for rel, name in new_rels.items():
                rels[rel] = name
            user.relationships = rels
            
            user.last_seen_at = datetime.utcnow()
            db.commit()
    finally:
        db.close()

    # 3. Store Real-time Memories
    from backend.memory.chroma_store import store_memory
    new_memories = data.get("memories", [])
    for mem in new_memories:
        store_memory(user_id, mem, metadata={"type": "real_time", "timestamp": now})


def extract_long_term_memories(user_id: str, history: list[dict], gemini_fn):
    """
    After a session ends, extract key facts to store permanently in ChromaDB.
    history: list of {role, content, ts}
    """
    if not history:
        return

    conversation = "\n".join(
        f"{'User' if t['role'] == 'user' else 'Jack'}: {t['content']}"
        for t in history
    )

    prompt = f"""
From this conversation, extract important facts about the user that Jack should remember long-term.
Return as a JSON array of strings (short factual statements).
Example: ["User likes Barbie movies", "User has a math exam on Friday"]
If nothing important, return [].

Conversation:
{conversation[:3000]}
"""
    try:
        raw = gemini_fn(prompt)
        facts = _extract_json(raw)
    except Exception:
        return

    if not facts or not isinstance(facts, list):
        return

    for fact in facts:
        store_memory(user_id, fact, metadata={"type": "long_term", "source": "session_end"})


def decay_interests(user_id: str):
    """
    Decay interest intensity for topics not mentioned recently.
    Called once per day by the scheduler.
    """
    interests = get_interests(user_id)
    now = datetime.utcnow()
    updated = []
    for entry in interests:
        last = datetime.fromisoformat(entry.get("last_mentioned", now.isoformat()))
        days_since = (now - last).days
        entry["intensity"] = _calc_intensity(
            entry.get("mention_count", 1),
            days_since,
            False
        )
        updated.append(entry)
    save_interests(user_id, updated)


def _calc_intensity(mention_count: int, days_since_last: int, emotion_signal: bool) -> float:
    # Recency: decays over 14 days instead of 30
    recency   = max(0.0, 1.0 - (days_since_last / 14))
    
    # Frequency: reaches max faster (after 5 mentions instead of 20)
    frequency = min(1.0, mention_count / 5)
    
    # Emotion: higher weight for emotional signals
    emotion   = 0.3 if emotion_signal else 0.0
    
    # Final score: balanced weight
    score = (recency * 0.4) + (frequency * 0.4) + emotion
    return round(min(1.0, score), 2)
