import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    secret_key: str = "super-secret-jack-key-change-me"
    # Gemini
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    # Groq
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    # Provider
    llm_provider: str = "gemini" # "gemini" | "groq"

    # Tavily (web research)
    tavily_api_key: str = ""

    # Storage
    chroma_persist_dir: str = "./data/chroma_db"
    sqlite_db_path: str = "./data/jack.db"
    database_url: str = "" # Set this in .env for Supabase/Postgres

    # TTS / STT
    tts_voice: str = "en-IN-NeerjaNeural"
    stt_model: str = "base"

    # Research engine
    research_interval_hours: int = 4

    # Proactive conversations
    proactive_enabled: bool = True
    sleep_start: str = "02:00"
    sleep_end: str = "06:00"

    # Sliding window
    max_hot_turns: int = 20

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
