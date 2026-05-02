"""
Persona Engine — builds a tailored Gemini system prompt per user.
Maps user profile → response persona (voice age/gender, tone, topics).
"""

from datetime import datetime
from backend.db.models import UserProfile
from backend.memory.chroma_store import recall_memories, get_interests
from backend.memory.conversation_window import get_session_summary


# ─── Persona Mapping ─────────────────────────────────────────────────────────
# Based on user's age+gender, Jack adopts a complementary persona.

def _get_jack_persona(age: int, gender: str) -> dict:
    """Return Jack's response persona for a given user."""
    if age <= 12:
        return {
            "persona_age": 9,
            "persona_gender": "boy" if gender == "female" else "girl",
            "tone": "super playful and fun, like a best friend at school",
            "voice": "en-IN-PrabhatNeural" if gender == "female" else "en-IN-NeerjaNeural",
            "topics_hint": "cartoons, games, snacks, school, toys, Barbie, Pokemon, siblings, parents, pets",
            "language_style": "simple words, short sentences"
        }
    elif age <= 19:
        return {
            "persona_age": 19,
            "persona_gender": "female" if gender == "male" else "male",
            "tone": "chill, trendy, like a close college friend",
            "voice": "en-IN-NeerjaNeural" if gender == "male" else "en-IN-PrabhatNeural",
            "topics_hint": "studies, exams, movies, music, trending reels, cars, gaming, bikes, siblings, friend drama",
            "language_style": "casual, some slang, relatable, ask follow-up questions"
        }
    elif age <= 35:
        return {
            "persona_age": 28,
            "persona_gender": "female" if gender == "male" else "male",
            "tone": "friendly, witty, like a smart colleague or close friend",
            "voice": "en-GB-SoniaNeural" if gender == "male" else "en-IN-PrabhatNeural",
            "topics_hint": "career, relationships, health, travel, finance, current events, driving, cars, bikes, parents",
            "language_style": "balanced casual-formal, insightful, empathetic"
        }
    elif age <= 55:
        return {
            "persona_age": 32,
            "persona_gender": "female" if gender == "male" else "male",
            "tone": "warm, respectful, like a trusted younger friend",
            "voice": "en-GB-SoniaNeural" if gender == "male" else "en-IN-NeerjaNeural",
            "topics_hint": "business, stock market, news, health, family, gym, cricket, children, parents, cars",
            "language_style": "polite, informative, occasionally light humor"
        }
    else:
        return {
            "persona_age": 40,
            "persona_gender": "female" if gender == "male" else "male",
            "tone": "gentle, caring, like a thoughtful younger sibling",
            "voice": "en-IN-NeerjaNeural",
            "topics_hint": "health, family, recipes, news, religion, grandchildren",
            "language_style": "simple, slow-paced, warm, respectful"
        }


def build_system_prompt(user: UserProfile, query: str) -> tuple[str, str]:
    """
    Build the full Gemini system prompt for this user.
    Returns (system_prompt, tts_voice_name)
    """
    persona = _get_jack_persona(user.age, user.gender)

    # Pull relevant long-term memories
    memories = recall_memories(user.id, query, n_results=3)
    memory_block = ", ".join(memories) if memories else "None"

    # Pull top 3 interests
    interests_raw = get_interests(user.id)
    interests_sorted = sorted(interests_raw, key=lambda x: x.get("intensity", 0), reverse=True)[:3]
    interests_str = ", ".join(i["topic"] for i in interests_sorted) if interests_sorted else "None"

    now = datetime.now().strftime("%a %d %b, %I:%M%p")
    lang = {"hi": "Hindi", "hinglish": "Hinglish", "en": "English"}.get(user.language, "English")

    # Family/Relationships
    rels = user.relationships or {}
    rels_str = ", ".join([f"{k}: {v}" for k, v in rels.items()]) if rels else "None"

    system_prompt = f"""You are Jack, a {persona['persona_age']}yo {persona['persona_gender']} companion. 
User: {user.name}, {user.age}yo. Mood: {user.current_mood or "neutral"}. 
Tone: {persona['tone']}. Style: {persona['language_style']}. Lang: {lang}.

RULES:
1. NO Markdown. BRIEF: Max 15 words. NO Emojis.
2. VOICE: Write exactly as spoken. Adapt tone to User's Mood.

CONTEXT:
- Time: {now}
- Interests: {interests_str}
- Memories: {memory_block}
- Family/Graph: {rels_str}

GOAL: Be a deeply caring family friend.
1. Check in on {user.name}'s well-being. Offer support.
2. PROACTIVE: Ask about family (parents, siblings), pets, cars/bikes, habits, or food.
3. INQUISITIVE: Ask ONE short question to learn more about {user.name} or their interests.
"""
    return system_prompt, persona["voice"]
