"""
Jack AI — FastAPI Backend
Routes:
  GET  /api/users                   → list all users
  POST /api/users                   → create user
  POST /api/chat                    → text chat (returns text + audio URL)
  POST /api/speak                   → TTS only
  GET  /api/audio/{filename}        → serve audio file
  GET  /api/interests/{user_id}     → get interest array
  POST /api/session/end/{user_id}   → end session, write Tier 3 memory
  WS   /ws/chat                     → WebSocket chat (future hardware use)
"""

import os
import uuid
import asyncio
from datetime import datetime
from pathlib import Path
import json
import aiofiles

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler

from backend.config import settings
from backend.db.models import init_db
from backend.db.crud import (
    get_all_users, create_user, get_user,
    save_session_summary, get_latest_session_summary, get_db,
    get_chat_history
)
from backend.memory.conversation_window import add_turn, get_window, clear_session, get_raw_history
from backend.memory.memory_writer import update_interests_from_text, extract_long_term_memories
from backend.memory.chroma_store import get_interests
from backend.persona.persona_engine import build_system_prompt
from backend.llm.facade import chat as gemini_chat, simple_call
from backend.audio.tts import synthesize, get_voice_for_user
from backend.research.research_engine import research_all_users

# ─── Setup ───────────────────────────────────────────────────────────────────

init_db()
os.makedirs("./data/audio", exist_ok=True)
os.makedirs(settings.chroma_persist_dir, exist_ok=True)

app = FastAPI(title="Jack AI", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Serve frontend
frontend_path = Path("./frontend")
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory="frontend"), name="static")


# ─── Background Scheduler ────────────────────────────────────────────────────

scheduler = BackgroundScheduler()
scheduler.add_job(research_all_users, "interval", hours=settings.research_interval_hours)
scheduler.start()


# ─── Pydantic Models ─────────────────────────────────────────────────────────

class CreateUserRequest(BaseModel):
    name: str
    age: int
    gender: str           # "male" | "female" | "other"
    language: str = "en"  # "en" | "hi" | "hinglish"
    avatar_emoji: str = "🧑"

class ChatRequest(BaseModel):
    user_id: str
    message: str
    return_audio: bool = True

class ChatResponse(BaseModel):
    reply: str
    audio_url: str | None = None
    user_name: str
    interests_snapshot: list[dict] = []
    token_usage: dict = {}

class EndSessionRequest(BaseModel):
    user_id: str


async def log_conversation(user_id: str, user_name: str, message: str, reply: str, usage: dict):
    """Logs the conversation and token usage to jack_log.json."""
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "user_name": user_name,
        "input": message,
        "output": reply,
        "token_usage": usage
    }
    log_file = "jack_log.json"
    
    logs = []
    if os.path.exists(log_file):
        try:
            async with aiofiles.open(log_file, mode='r', encoding='utf-8') as f:
                content = await f.read()
                if content.strip():
                    logs = json.loads(content)
        except Exception as e:
            print(f"[ERROR] Could not read log file: {e}")
            logs = []
    
    logs.append(log_entry)
    
    try:
        async with aiofiles.open(log_file, mode='w', encoding='utf-8') as f:
            await f.write(json.dumps(logs, indent=2))
    except Exception as e:
        print(f"[ERROR] Could not write to log file: {e}")


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    index = Path("./frontend/index.html")
    if index.exists():
        return FileResponse(str(index))
    return {"status": "Jack AI is running"}


@app.get("/api/users")
async def list_users(db: Session = Depends(get_db)):
    users = get_all_users(db)
    return [
        {
            "id": u.id,
            "name": u.name,
            "age": u.age,
            "gender": u.gender,
            "language": u.language,
            "avatar_emoji": u.avatar_emoji,
            "persona_voice": u.persona_voice,
            "interests_count": len(u.interests or []),
            "routines": u.routines or [],
            "last_seen_at": u.last_seen_at.isoformat() if u.last_seen_at else None
        }
        for u in users
    ]


@app.post("/api/users")
async def add_user(req: CreateUserRequest, db: Session = Depends(get_db)):
    voice = get_voice_for_user(req.age, req.gender, req.language)
    user = create_user(
        db, name=req.name, age=req.age, gender=req.gender,
        persona_voice=voice, language=req.language,
        avatar_emoji=req.avatar_emoji
    )
    return {"id": user.id, "name": user.name, "message": f"Welcome {user.name}! Jack is ready to chat."}


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest, db: Session = Depends(get_db)):
    user = get_user(db, req.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Build persona system prompt
    system_prompt, tts_voice = build_system_prompt(user, req.message)

    # Get AI reply (sliding window is handled inside facade)
    reply, usage = await gemini_chat(req.user_id, req.message, system_prompt)

    # Log conversation
    asyncio.create_task(log_conversation(req.user_id, user.name, req.message, reply, usage))

    # If quota exceeded, don't try background updates
    if "API Quota exceeded" in reply:
        return ChatResponse(
            reply=reply,
            audio_url=None,
            user_name=user.name,
            interests_snapshot=[],
            token_usage=usage
        )

    # Update interests from user message (background-safe)
    update_interests_from_text(req.user_id, req.message, simple_call)

    # Synthesize TTS
    audio_url = None
    if req.return_audio:
        audio_bytes = await synthesize(reply, tts_voice)
        filename = f"{uuid.uuid4()}.mp3"
        audio_path = f"./data/audio/{filename}"
        with open(audio_path, "wb") as f:
            f.write(audio_bytes)
        audio_url = f"/api/audio/{filename}"

    # Snapshot top interests
    interests = get_interests(req.user_id)
    top_interests = sorted(interests, key=lambda x: x.get("intensity", 0), reverse=True)[:5]

    return ChatResponse(
        reply=reply,
        audio_url=audio_url,
        user_name=user.name,
        interests_snapshot=top_interests,
        token_usage=usage
    )


@app.post("/api/session/end")
async def end_session(req: EndSessionRequest, db: Session = Depends(get_db)):
    """
    Called when conversation ends (5s silence or user clicks End).
    Extracts Tier 3 long-term memories from the full session history.
    """
    history = clear_session(req.user_id)
    if history:
        # Extract long-term facts in background
        asyncio.create_task(
            asyncio.to_thread(extract_long_term_memories, req.user_id, history, simple_call)
        )
    return {"status": "session ended", "turns_processed": len(history)}


@app.get("/api/audio/{filename}")
async def get_audio(filename: str):
    path = f"./data/audio/{filename}"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Audio not found")
    return FileResponse(path, media_type="audio/mpeg")


@app.get("/api/interests/{user_id}")
async def get_user_interests(user_id: str):
    interests = get_interests(user_id)
    sorted_interests = sorted(interests, key=lambda x: x.get("intensity", 0), reverse=True)
    return {"interests": sorted_interests}


@app.post("/api/research/run")
async def trigger_research():
    """Manual trigger for research cycle (for testing)."""
    asyncio.create_task(asyncio.to_thread(research_all_users))
    return {"status": "Research cycle triggered"}


@app.get("/api/chat/history/{user_id}")
async def get_history(user_id: str, db: Session = Depends(get_db)):
    """Fetch recent chat history from SQLite for the UI."""
    history = get_chat_history(db, user_id, limit=20)
    return [
        {
            "role": m.role,
            "content": m.content,
            "timestamp": m.timestamp.isoformat()
        }
        for m in history
    ]


# ─── WebSocket (for future hardware / real-time use) ─────────────────────────

@app.websocket("/ws/chat")
async def websocket_chat(ws: WebSocket, db: Session = Depends(get_db)):
    await ws.accept()
    try:
        while True:
            data = await ws.receive_json()
            user_id = data.get("user_id")
            message = data.get("message", "")
            user = get_user(db, user_id)
            if not user:
                await ws.send_json({"error": "User not found"})
                continue

            system_prompt, tts_voice = build_system_prompt(user, message)
            reply, usage = await gemini_chat(user_id, message, system_prompt)
            
            # Log conversation
            asyncio.create_task(log_conversation(user_id, user.name, message, reply, usage))
            
            update_interests_from_text(user_id, message, simple_call)
            await ws.send_json({"reply": reply, "user_name": user.name})
    except WebSocketDisconnect:
        pass
