"""
ChromaDB wrapper — per-user collections for:
  - episodic memory  (what happened)
  - preferences      (what they like/dislike)
  - interests        (dynamic interest array with news)
"""

import chromadb
import json
from datetime import datetime
from sentence_transformers import SentenceTransformer
from backend.config import settings

_client = None
_embedder = None


def _get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return _client


def _get_embedder() -> SentenceTransformer:
    global _embedder
    if _embedder is None:
        _embedder = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedder


def _embed(text: str) -> list[float]:
    return _get_embedder().encode(text).tolist()


def _col(user_id: str, kind: str):
    """Get or create a named collection for this user."""
    return _get_client().get_or_create_collection(f"user_{user_id}_{kind}")


# ─── Episodic Memory (Tier 3 long-term) ──────────────────────────────────────

from backend.db.models import SessionLocal, Memory, UserProfile
from sqlalchemy import or_

def _is_cloud():
    return settings.database_url and settings.database_url.startswith("postgres")

# ─── Episodic Memory (Tier 3 long-term) ──────────────────────────────────────

def store_memory(user_id: str, text: str, metadata: dict | None = None):
    if _is_cloud():
        db = SessionLocal()
        try:
            mem = Memory(user_id=user_id, content=text, metadata_=metadata or {})
            db.add(mem)
            db.commit()
        finally:
            db.close()
        return

    col = _col(user_id, "episodic")
    doc_id = f"mem_{datetime.utcnow().timestamp()}"
    meta = {"timestamp": datetime.utcnow().isoformat(), **(metadata or {})}
    col.add(
        ids=[doc_id],
        embeddings=[_embed(text)],
        documents=[text],
        metadatas=[meta]
    )

def recall_memories(user_id: str, query: str, n_results: int = 5) -> list[str]:
    if _is_cloud():
        db = SessionLocal()
        try:
            # Simple keyword search for free cloud tier
            words = query.split()
            filters = [Memory.content.ilike(f"%{w}%") for w in words[:3]]
            results = (db.query(Memory)
                       .filter(Memory.user_id == user_id)
                       .filter(or_(*filters))
                       .limit(n_results).all())
            return [m.content for m in results]
        finally:
            db.close()

    col = _col(user_id, "episodic")
    if col.count() == 0:
        return []
    results = col.query(
        query_embeddings=[_embed(query)],
        n_results=min(n_results, col.count())
    )
    return results["documents"][0] if results["documents"] else []

# ─── Preferences ─────────────────────────────────────────────────────────────

def store_preference(user_id: str, text: str):
    store_memory(user_id, text, metadata={"type": "preference"})


# ─── Dynamic Interests Array ─────────────────────────────────────────────────

def get_interests(user_id: str) -> list[dict]:
    if _is_cloud():
        db = SessionLocal()
        try:
            user = db.query(UserProfile).filter(UserProfile.id == user_id).first()
            return user.interests if user and user.interests else []
        finally:
            db.close()

    col = _col(user_id, "interests")
    results = col.get(ids=["interests_array"])
    if results["documents"]:
        return json.loads(results["documents"][0])
    return []

def save_interests(user_id: str, interests: list[dict]):
    if _is_cloud():
        # Interests are already synced to UserProfile in memory_writer.py
        return

    col = _col(user_id, "interests")
    blob = json.dumps(interests)
    col.upsert(
        ids=["interests_array"],
        documents=[blob],
        embeddings=[_embed(blob)],
        metadatas=[{"updated_at": datetime.utcnow().isoformat()}]
    )
