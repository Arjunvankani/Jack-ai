from sqlalchemy.orm import Session
from datetime import datetime
from backend.db.models import UserProfile, SessionSummary, Reminder, ChatMessage, get_db  # re-export get_db
from typing import List, Optional
import json


# ─── User Profile CRUD ────────────────────────────────────────────────────────

def get_all_users(db: Session) -> List[UserProfile]:
    return db.query(UserProfile).all()

def get_user(db: Session, user_id: str) -> Optional[UserProfile]:
    return db.query(UserProfile).filter(UserProfile.id == user_id).first()

def create_user(db: Session, name: str, age: int, gender: str,
                persona_voice: str = "en-IN-NeerjaNeural",
                language: str = "en",
                avatar_emoji: str = "🧑") -> UserProfile:
    user = UserProfile(
        name=name, age=age, gender=gender,
        persona_voice=persona_voice, language=language,
        avatar_emoji=avatar_emoji,
        interests=[], routines=[]
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def update_user_interests(db: Session, user_id: str, interests: list):
    user = get_user(db, user_id)
    if user:
        # Important: use flag_modified if using JSON type, but here we just re-assign
        user.interests = interests
        user.last_seen_at = datetime.utcnow()
        db.commit()

def update_last_seen(db: Session, user_id: str):
    user = get_user(db, user_id)
    if user:
        user.last_seen_at = datetime.utcnow()
        db.commit()

def add_routine(db: Session, user_id: str, time: str, task: str, days: str = "daily"):
    user = get_user(db, user_id)
    if user:
        routines = list(user.routines or [])
        routines.append({"time": time, "task": task, "days": days})
        user.routines = routines
        db.commit()


# ─── Chat Message CRUD (Hot Window persistence) ──────────────────────────────

def save_chat_message(db: Session, user_id: str, role: str, content: str) -> ChatMessage:
    msg = ChatMessage(user_id=user_id, role=role, content=content)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return msg

def get_chat_history(db: Session, user_id: str, limit: int = 20) -> List[ChatMessage]:
    return (db.query(ChatMessage)
            .filter(ChatMessage.user_id == user_id)
            .order_by(ChatMessage.timestamp.desc())
            .limit(limit)
            .all())[::-1]  # Reverse to get chronological order

def clear_chat_history(db: Session, user_id: str):
    db.query(ChatMessage).filter(ChatMessage.user_id == user_id).delete()
    db.commit()


# ─── Session Summary CRUD (Tier 2 memory) ────────────────────────────────────

def save_session_summary(db: Session, user_id: str, summary: str) -> SessionSummary:
    s = SessionSummary(user_id=user_id, summary=summary)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

def get_latest_session_summary(db: Session, user_id: str) -> Optional[str]:
    s = (db.query(SessionSummary)
           .filter(SessionSummary.user_id == user_id)
           .order_by(SessionSummary.created_at.desc())
           .first())
    return s.summary if s else None


# ─── Reminder CRUD ───────────────────────────────────────────────────────────

def get_active_reminders(db: Session, user_id: str) -> List[Reminder]:
    return db.query(Reminder).filter(
        Reminder.user_id == user_id, Reminder.active == True
    ).all()

def create_reminder(db: Session, user_id: str, message: str,
                    fire_at: str, repeat: str = "daily") -> Reminder:
    r = Reminder(user_id=user_id, message=message, fire_at=fire_at, repeat=repeat)
    db.add(r)
    db.commit()
    db.refresh(r)
    return r
