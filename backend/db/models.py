import uuid
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, JSON, Text
from sqlalchemy.orm import declarative_base, sessionmaker

from backend.config import settings

# Database selection
engine = None
try:
    if settings.database_url and ("postgres" in settings.database_url):
        # Supabase / Postgres
        db_url = settings.database_url.replace("postgres://", "postgresql://", 1)
        print(f"[INFO] Using Supabase Cloud Database (DNS permitting)...")
        engine = create_engine(
            db_url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 3} # Faster timeout
        )
    else:
        raise ValueError("No cloud DB URL")
except Exception:
    print(f"[INFO] Using local SQLite database ({settings.sqlite_db_path})...")
    DATABASE_URL = f"sqlite:///{settings.sqlite_db_path}"
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id           = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name         = Column(String, nullable=False)
    age          = Column(Integer, nullable=False)
    gender       = Column(String, nullable=False)           # "male" | "female" | "other"
    persona_voice = Column(String, default="en-IN-NeerjaNeural")  # edge-tts voice name
    language     = Column(String, default="en")             # "en" | "hi" | "hinglish"
    interests    = Column(JSON, default=list)               # list of interest dicts
    routines     = Column(JSON, default=list)               # [{time, task, days}]
    avatar_emoji = Column(String, default="🧑")
    relationships = Column(JSON, default=dict)  # {relation_type: user_id}
    current_mood = Column(String, default="neutral")
    created_at   = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)


class SessionSummary(Base):
    """Compressed summaries of past hot-window turns (Tier 2 memory)."""
    __tablename__ = "session_summaries"

    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id    = Column(String, nullable=False)
    summary    = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class ChatMessage(Base):
    """Individual turns stored for hot-window persistence across restarts."""
    __tablename__ = "chat_messages"

    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id    = Column(String, index=True, nullable=False)
    role       = Column(String, nullable=False)  # "user" | "model" | "system"
    content    = Column(Text, nullable=False)
    timestamp  = Column(DateTime, default=datetime.utcnow)


class Reminder(Base):
    __tablename__ = "reminders"

    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id    = Column(String, nullable=False)
    message    = Column(String, nullable=False)
    fire_at    = Column(String, nullable=False)  # "HH:MM" or ISO datetime
    repeat     = Column(String, default="daily") # "daily" | "once" | "weekdays"
    active     = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Memory(Base):
    """Long-term memories stored in Postgres for persistence on cloud hosting."""
    __tablename__ = "memories"

    id         = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id    = Column(String, index=True, nullable=False)
    content    = Column(Text, nullable=False)
    metadata_  = Column(JSON, default=dict) # renamed to avoid metadata clash
    timestamp  = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Create all tables and local directories if needed."""
    if not settings.database_url or not settings.database_url.startswith("postgres"):
        import os
        db_dir = os.path.dirname(settings.sqlite_db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    
    Base.metadata.create_all(bind=engine)

    # SCHEMA PATCH: Add missing columns to SQLite if they don't exist
    if not settings.database_url or not settings.database_url.startswith("postgres"):
        from sqlalchemy import inspect, text
        inspector = inspect(engine)
        columns = [c['name'] for c in inspector.get_columns("user_profiles")]
        
        with engine.connect() as conn:
            if "relationships" not in columns:
                print("[INFO] Patching SQLite: Adding 'relationships' column...")
                conn.execute(text("ALTER TABLE user_profiles ADD COLUMN relationships JSON DEFAULT '{}'"))
                conn.commit()
            if "current_mood" not in columns:
                print("[INFO] Patching SQLite: Adding 'current_mood' column...")
                conn.execute(text("ALTER TABLE user_profiles ADD COLUMN current_mood TEXT DEFAULT 'neutral'"))
                conn.commit()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
