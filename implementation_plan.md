# Jack AI — Personalized Voice Companion: Full Implementation Plan

> **Latest Update**: Added Dynamic Interests Engine, Web Research Layer, and 24/7 Proactive Conversation System

## What We're Building

**Jack AI** is a locally-run, voice-first AI companion that:
- Identifies **who is speaking** (voice fingerprinting)
- Learns each person's **tone, interests, habits, and routines** over time
- Responds with a **persona tailored to each user** (age-appropriate voice, language style, topic awareness)
- Stores all individual memory in **ChromaDB** (vector embeddings)
- Uses **Gemini API** as the LLM brain
- Starts as a **local web app** with a speech button UI, and evolves into a **hardware device**

---

## Phase Roadmap

```
Phase 1: Local PC MVP (NOW)
  └─ Simple Web UI + Speech Button + Gemini API + ChromaDB

Phase 2: Multi-User Profile System
  └─ Voice fingerprinting + per-user memory + persona engine

Phase 3: Full Intelligence Layer
  └─ Routine learning, reminders, suggestions, emotional tone

Phase 4: Hardware Device
  └─ Raspberry Pi 5 or Jetson Nano + microphone array + speaker
```

---

## Full Tech Stack

| Layer | Technology | Why |
|---|---|---|
| **LLM Brain** | Gemini 1.5 Pro API (Flash for speed) | Multimodal, large context, free tier |
| **Voice → Text** | `faster-whisper` (local, offline STT) | Fast, accurate, no API cost |
| **Text → Voice** | `Coqui TTS` / `edge-tts` (Microsoft Neural) | Custom voices, age/gender variants |
| **Web Research** | `Tavily API` (AI-optimized search) | Real-time googling for interest updates |
| **Interest Tracker** | Dynamic JSON array in ChromaDB | Live evolving interests per user |
| **Speaker ID** | `speechbrain` (ECAPA-TDNN embeddings) | Speaker fingerprinting, identify 4+ users |
| **Vector Memory** | `ChromaDB` (local persistent) | Store per-user embeddings + memory |
| **Embeddings** | `sentence-transformers` (`all-MiniLM-L6-v2`) | Encode memory chunks |
| **Backend** | Python (FastAPI) | REST + WebSocket endpoints |
| **Frontend UI** | HTML + Vanilla JS + CSS | Speech button, chat bubbles, user selector |
| **Scheduler** | `APScheduler` | Reminders, routines, proactive alerts |
| **Audio I/O** | `PyAudio` + `sounddevice` | Mic capture, speaker output |
| **Wake Word** | `openWakeWord` | "Hey Jack" detection |
| **Local DB** | SQLite (via SQLAlchemy) | Structured user profiles, routines |
| **Config** | `.env` + `pydantic-settings` | API keys, tunable parameters |

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    JACK AI SYSTEM                       │
│                                                         │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │  Audio   │───▶│  Speaker ID  │───▶│  User Profile │  │
│  │  Input   │    │ (SpeechBrain)│    │   Resolver    │  │
│  └──────────┘    └──────────────┘    └───────┬───────┘  │
│                                              │           │
│  ┌──────────┐                       ┌───────▼───────┐  │
│  │  faster  │◀──────────────────────│  STT Engine   │  │
│  │ -whisper │    transcribed text   │  (Whisper)    │  │
│  └──────────┘                       └───────────────┘  │
│       │                                                  │
│       ▼                                                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │              MEMORY RETRIEVAL ENGINE             │   │
│  │  ChromaDB ──▶ Retrieve relevant memories        │   │
│  │  SQLite   ──▶ Get profile: age, interests, tone  │   │
│  └──────────────────────┬───────────────────────────┘   │
│                         │                                │
│                         ▼                                │
│  ┌──────────────────────────────────────────────────┐   │
│  │              GEMINI API (LLM CORE)               │   │
│  │  System Prompt = Persona + Memories + Context    │   │
│  │  Response = Personalized reply                   │   │
│  └──────────────────────┬───────────────────────────┘   │
│                         │                                │
│                         ▼                                │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │  TTS     │◀───│  Persona     │◀───│  Memory Write │  │
│  │  Output  │    │  Voice Engine│    │  (new memory) │  │
│  └──────────┘    └──────────────┘    └───────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## Project Folder Structure

```
Jack-ai/
├── backend/
│   ├── main.py                  # FastAPI app entry
│   ├── config.py                # Env vars, Gemini key
│   ├── audio/
│   │   ├── recorder.py          # Mic capture, VAD
│   │   ├── stt.py               # Whisper STT
│   │   ├── tts.py               # Coqui/edge-tts output
│   │   └── wake_word.py         # "Hey Jack" detection
│   ├── identity/
│   │   ├── speaker_id.py        # SpeechBrain voice fingerprint
│   │   └── user_resolver.py     # Match voice → user profile
│   ├── memory/
│   │   ├── chroma_store.py      # ChromaDB ops (read/write)
│   │   ├── embedder.py          # sentence-transformers
│   │   └── memory_writer.py     # Extract + store new memories
│   ├── persona/
│   │   ├── persona_engine.py    # Build system prompt per user
│   │   └── voice_selector.py   # Select TTS voice by persona
│   ├── llm/
│   │   └── gemini_client.py     # Gemini API calls
│   ├── scheduler/
│   │   └── reminder_engine.py  # APScheduler reminders
│   └── db/
│       ├── models.py            # SQLAlchemy User, Routine models
│       └── crud.py              # DB operations
├── frontend/
│   ├── index.html               # Main UI
│   ├── style.css                # Premium dark UI
│   └── app.js                   # Speech button, WebSocket
├── data/
│   ├── chroma_db/               # ChromaDB persistent storage
│   └── voices/                  # Voice samples per user
├── .env                         # GEMINI_API_KEY etc.
├── requirements.txt
└── README.md
```

---

## 🔥 NEW: Dynamic Interests Engine

### The Core Idea
Every user has a **live `interests[]` array** that is:
- **Updated automatically** from every conversation
- **Researched continuously** by Jack in the background (like googling)
- **Used to start proactive conversations** — Jack talks TO you, not just WITH you
- **Ranked by recency + frequency** so stale interests fade, hot topics rise

### Interests Array Schema (per user, stored in ChromaDB + SQLite)
```json
{
  "user_id": "uuid-priya",
  "interests": [
    {
      "topic": "Barbie",
      "category": "entertainment",
      "intensity": 0.92,
      "last_mentioned": "2026-05-01T18:30:00",
      "mention_count": 14,
      "latest_news": "Barbie 2 movie announced for Dec 2026",
      "news_fetched_at": "2026-05-02T06:00:00"
    },
    {
      "topic": "Maggi",
      "category": "food",
      "intensity": 0.78,
      "last_mentioned": "2026-04-30T19:00:00",
      "mention_count": 9,
      "latest_news": null
    },
    {
      "topic": "School homework",
      "category": "education",
      "intensity": 0.65,
      "last_mentioned": "2026-05-01T17:00:00",
      "mention_count": 5,
      "latest_news": null
    }
  ]
}
```

### Interest Update Pipeline
```
Conversation happens
       ↓
Gemini extracts new/updated interests from the text
("She mentioned she's excited about a new cartoon")
       ↓
Interest Extractor updates the interests array:
  - New topic? → Add with intensity 0.5
  - Repeated topic? → Bump intensity + mention_count
  - Not mentioned in 7 days? → Decay intensity by 0.1/day
       ↓
Store back to ChromaDB + SQLite
```

### Interest Intensity Scoring Formula
```python
def calculate_intensity(mention_count, days_since_last, user_emotional_signal):
    recency_score = max(0, 1 - (days_since_last / 30))   # decays over 30 days
    frequency_score = min(1.0, mention_count / 20)        # caps at 20 mentions
    emotion_boost = 0.2 if user_emotional_signal else 0   # "I LOVE cartoons!"
    return round((recency_score * 0.5 + frequency_score * 0.4 + emotion_boost), 2)
```

---

## 🌐 Web Research Engine (Jack Googles For You)

### How It Works
Jack **autonomously researches** each user's top interests every few hours using the **Tavily Search API** (AI-optimized, returns clean summaries).

```
Background scheduler runs every 4 hours
       ↓
For each user → fetch top 3 interests by intensity
       ↓
Tavily API search: "Latest {topic} news today"
       ↓
Gemini summarizes result into 2-line update
       ↓
Stored in interest.latest_news (ChromaDB)
       ↓
Used in next conversation as context OR
Jack proactively says: "Hey! Big news about {topic}..."
```

### Research Categories Per User Type
| User | Auto-Research Topics |
|---|---|
| 7-yr-old girl | Latest cartoon releases, Barbie news, school holiday schedule |
| 20-yr-old male | Tech news, exam tips, trending reels, car launches |
| 47-yr-old father | Stock market today, business news, cricket score, gym tips |
| 45-yr-old mother | Recipes, grocery prices, school events, health tips |

### Research Engine Code Structure
```
backend/
  research/
    ├── research_engine.py       # Scheduler + Tavily calls
    ├── interest_extractor.py    # Gemini extracts interests from text
    ├── interest_ranker.py       # Intensity scoring + decay
    └── news_summarizer.py       # Gemini condenses news to 2 lines
```

### Tavily API Integration (research_engine.py)
```python
from tavily import TavilyClient

client = TavilyClient(api_key=TAVILY_API_KEY)

async def research_interest(topic: str, user_name: str) -> str:
    result = client.search(
        query=f"Latest news about {topic} today 2026",
        search_depth="basic",
        max_results=3
    )
    # Feed to Gemini for summarization
    summary = await gemini_summarize(result['results'], topic, user_name)
    return summary  # "Barbie 2 was just announced for December! 🎀"
```

---

## 🤖 24/7 Proactive Conversation System

Jack doesn't wait to be spoken to. He **initiates conversations** based on:
- New research findings about user interests
- Time-based routines (reminders)
- Detected emotional patterns ("You seemed stressed yesterday...")
- Random check-ins to feel human

### Proactive Trigger Types
```python
PROACTIVE_TRIGGERS = [
    {
        "type": "news_update",
        "condition": "interest.latest_news updated within last 2 hours",
        "example": "Hey Priya! Guess what? They just announced Barbie 2! 🎀"
    },
    {
        "type": "routine_reminder",  
        "condition": "30 min before user routine event",
        "example": "Dad, it's 6:30 — gym in 30 mins! Ready to crush it? 💪"
    },
    {
        "type": "follow_up",
        "condition": "User mentioned an event yesterday (exam, meeting, date)",
        "example": "Hey Rahul, how did the exam go yesterday? 🤞"
    },
    {
        "type": "daily_checkin",
        "condition": "Morning 8am, user hasn't spoken yet today",
        "example": "Good morning! It's a great day — what's the plan?"
    },
    {
        "type": "suggestion",
        "condition": "Dinner time + user has no plan + food preferences known",
        "example": "Mom, it's 7pm — how about making Maggi tonight? Priya will love it!"
    }
]
```

### Conversation Continuity (24/7 always-on)
```
Jack runs in 3 modes:

1. SLEEP MODE (2am–6am)
   └── Only urgent alerts (security, alarms)
   └── Research engine still runs silently

2. AMBIENT MODE (6am–10pm, no one speaking)
   └── Listens for wake word "Hey Jack"
   └── Proactive triggers fire based on schedule
   └── Soft chime + greeting when speaking

3. ACTIVE MODE (mid-conversation)
   └── Full conversation with context window
   └── Real-time interest extraction after each turn
   └── Memory written after conversation ends (5s silence)
```

---

## Updated Folder Structure (with Research Layer)

```
Jack-ai/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── audio/                    # STT, TTS, wake word, recorder
│   ├── identity/                 # Speaker ID + user resolver
│   ├── memory/                   # ChromaDB + embedder + memory writer
│   ├── persona/                  # Persona engine + voice selector
│   ├── llm/                      # Gemini client
│   ├── scheduler/                # APScheduler (reminders + proactive)
│   ├── research/                 # 🆕 Web research engine
│   │   ├── research_engine.py    # Tavily search scheduler
│   │   ├── interest_extractor.py # Gemini extracts topics from chat
│   │   ├── interest_ranker.py    # Intensity scoring + decay logic
│   │   └── news_summarizer.py    # Gemini condenses to 2-line updates
│   └── db/                       # SQLite models + CRUD
├── frontend/
│   ├── index.html                 # Main UI
│   ├── style.css
│   └── app.js                    # Mic button, interests panel, chat
├── data/
│   ├── chroma_db/
│   └── voices/
├── .env
└── requirements.txt
```

---

## Updated .env
```env
GEMINI_API_KEY=your_key
GEMINI_MODEL=gemini-1.5-flash
TAVILY_API_KEY=your_key        # Free tier: 1000 searches/month
CHROMA_PERSIST_DIR=./data/chroma_db
SQLITE_DB_PATH=./data/jack.db
RESEARCH_INTERVAL_HOURS=4      # How often Jack googles interests
PROACTIVE_ENABLED=true
SLEEP_START=02:00
SLEEP_END=06:00
```

---

## 🪟 Sliding Window Conversation Memory

Conversation **sequence matters** — Jack must remember what was just said and keep the flow natural. We use a **3-tier memory architecture**:

```
┌─────────────────────────────────────────────────────────┐
│  TIER 1: HOT WINDOW (last 20 turns, in RAM)             │
│  → Sent directly in every Gemini API call               │
│  → Exact messages, full sequence preserved              │
│  → Clears when conversation ends (5s silence)           │
├─────────────────────────────────────────────────────────┤
│  TIER 2: SESSION SUMMARY (ChromaDB, per session)        │
│  → When window exceeds 20 turns, oldest 10 get          │
│    compressed by Gemini into a 3-line summary           │
│  → Summary injected back as "earlier in this chat..."   │
│  → Keeps sequence context without blowing token limit   │
├─────────────────────────────────────────────────────────┤
│  TIER 3: LONG-TERM MEMORY (ChromaDB, permanent)         │
│  → After session ends, key facts extracted & stored     │
│  → Retrieved via semantic search in future sessions     │
│  → "Last week you said you had an exam..."              │
└─────────────────────────────────────────────────────────┘
```

### Sliding Window Logic
```python
MAX_HOT_TURNS = 20       # Keep last 20 turns in context
COMPRESS_AT = 20         # When reached, compress oldest 10 → summary
SUMMARY_INJECT_LABEL = "[Earlier in this conversation]: "

def get_context_window(user_id: str) -> list[dict]:
    window = hot_window_cache[user_id]   # list of {role, content}
    
    if len(window) >= MAX_HOT_TURNS:
        # Compress oldest 10 turns into summary via Gemini
        oldest = window[:10]
        summary = gemini_compress(oldest)  # "User asked about Barbie, then..."
        store_session_summary(user_id, summary)
        hot_window_cache[user_id] = window[10:]  # Slide the window
    
    # Inject summary if exists (for continuity)
    if session_summary := get_session_summary(user_id):
        return [{"role": "system", "content": SUMMARY_INJECT_LABEL + session_summary}] \
               + hot_window_cache[user_id]
    
    return hot_window_cache[user_id]
```

### Why This Matters for Jack
- If Priya asks "what did I say before?" — Jack remembers the full session
- Multi-turn jokes, stories, questions all flow naturally
- No context drop mid-conversation even in a 2-hour chat session
- Between sessions, Tier 3 long-term memory bridges the gap

---

## Phase 1: Local MVP (Week 1–2)

### What gets built:
- **Web UI** with a microphone button (record → transcribe → respond → speak)
- **Manual user selection** (dropdown: "Who are you?")
- **Gemini API** integration with basic persona system prompts
- **ChromaDB** to store and recall conversation memories
- **Basic TTS** voice output (edge-tts, free, neural voices)

### Key files to build first:
1. `backend/llm/gemini_client.py` — Gemini chat with history
2. `backend/memory/chroma_store.py` — Store and retrieve per-user memories
3. `backend/persona/persona_engine.py` — Build system prompt from user profile
4. `backend/audio/stt.py` — Whisper transcription
5. `backend/audio/tts.py` — edge-tts voice output
6. `frontend/index.html + app.js` — Chat UI + mic button

---

## Phase 2: Multi-User Voice Identity (Week 3–4)

### Speaker Identification Pipeline:
```
Audio Chunk (2s) → ECAPA-TDNN (SpeechBrain) → 192-dim embedding
                                              ↓
                          Compare against stored user embeddings
                                              ↓
                          Cosine similarity → best match (or "new user")
```

### Per-User Profile Schema (SQLite):
```python
class UserProfile:
    id: str                  # UUID
    name: str                # "Priya"
    age: int                 # 7
    gender: str              # "female"
    persona_voice: str       # "en-IN-NeerjaNeural" (edge-tts)
    interests: List[str]     # ["cartoons", "barbie", "maggi"]
    routines: List[Routine]  # [{"time": "18:30", "task": "gym"}]
    voice_embedding: bytes   # Stored speaker fingerprint
    created_at: datetime
```

### Per-User ChromaDB Collections:
```
chroma_db/
  ├── user_<uuid>_episodic      # "She mentioned she likes Barbie on Mon"
  ├── user_<uuid>_preferences   # "Likes Maggi, not fond of salad"
  └── user_<uuid>_routines      # "Gym at 7pm on weekdays"
```

---

## Phase 3: Persona & Intelligence Engine (Week 5–6)

### Persona System Prompt Template:
```
You are Jack, a friendly AI companion.
You are speaking with {name}, a {age}-year-old {gender}.

PERSONA RULES:
- Use a {response_voice_age}-year-old {response_voice_gender} personality
- Keep language {tone_level} (casual/formal/playful)
- Their interests: {interests}
- Their current routine: {routine_summary}

RELEVANT MEMORIES:
{retrieved_memories}

CURRENT TIME: {datetime}
PROACTIVE SUGGESTIONS: If relevant, suggest {suggestion_type}

Respond naturally, warmly, and in a conversational way.
```

### Persona Mapping Table:

| User Type | Jack's Response Persona | Voice (edge-tts) |
|---|---|---|
| 7-yr-old girl | Friendly 8-yr-old boy energy | `en-IN-PrabhatNeural` |
| 20-yr-old male | 18-yr-old female bestie | `en-IN-NeerjaNeural` |
| 47-yr-old father | 30-yr-old professional woman | `en-GB-SoniaNeural` |
| 45-yr-old mother | Caring peer-age friend | `en-IN-NeerjaNeural` |

### Memory Write Strategy:
After each conversation turn, extract and store:
```python
memory_types = {
    "preference": "User said they like X",
    "routine": "User mentioned they go to gym at 7pm",  
    "event": "User had an exam today",
    "emotion": "User seemed stressed about work",
    "family": "User mentioned their child has homework"
}
```

### Proactive Suggestions Engine:
```python
# Time-based triggers
if current_time == "18:25" and user_has_routine("gym", "19:00"):
    jack_says("Hey! Your gym session is in 35 mins, are you getting ready?")

if current_time == "08:00" and user_is("child"):
    jack_says("Good morning! Don't forget your lunchbox today 🎒")
```

---

## Phase 4: Hardware Device (Month 3+)

### Hardware Bill of Materials:

| Component | Model | Cost (approx) |
|---|---|---|
| **SBC (Brain)** | Raspberry Pi 5 (8GB) | ~$80 |
| **Microphone Array** | ReSpeaker 4-Mic Array for Pi | ~$25 |
| **Speaker** | 5W USB/3.5mm speaker | ~$10 |
| **Enclosure** | 3D printed cylindrical shell | ~$15 |
| **Status LED Ring** | NeoPixel 12-LED ring | ~$8 |
| **Power** | 5V/5A USB-C PSU | ~$10 |
| **Storage** | 64GB microSD (A2 rated) | ~$12 |
| **Total** | | **~$160** |

### Hardware Software Stack:
- OS: Raspberry Pi OS 64-bit (Bookworm)
- Wake word runs always-on (openWakeWord, CPU efficient)
- Whisper runs `tiny.en` or `base` model locally
- All Gemini API calls go over WiFi
- ChromaDB persisted on microSD

---

## Data Flow: Full Conversation Cycle

```
1. "Hey Jack" detected (wake word)
        ↓
2. LED ring pulses blue (listening)
        ↓
3. Audio recorded (VAD stops after silence)
        ↓
4. Speaker ID → resolves to "Priya (7F)"
        ↓
5. Whisper transcribes: "Jack, what should I have for dinner?"
        ↓
6. ChromaDB query: retrieve Priya's food preferences
   → ["likes Maggi", "dislikes vegetables", "likes Milkshake"]
        ↓
7. Build Gemini system prompt with Priya's persona + memories
        ↓
8. Gemini responds: "Ooh! How about Maggi tonight? 
   With some ketchup and butter? Your faaavorite! 🍜"
        ↓
9. Memory writer stores: "Priya asked about dinner at 7pm on Fri"
        ↓
10. edge-tts generates audio in 8-yr-old boy voice
         ↓
11. Audio plays through speaker, LED ring glows green
```

---

## API & Environment Setup

```env
# .env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash
CHROMA_PERSIST_DIR=./data/chroma_db
SQLITE_DB_PATH=./data/jack.db
TTS_PROVIDER=edge-tts
STT_MODEL=base          # whisper model size
WAKE_WORD=hey jack
```

---

## Python Dependencies (requirements.txt)

```
fastapi
uvicorn[standard]
python-dotenv
pydantic-settings
google-generativeai
chromadb
sentence-transformers
faster-whisper
edge-tts
speechbrain
sounddevice
pyaudio
webrtcvad
apscheduler
sqlalchemy
aiofiles
websockets
```

---

## Development Sprint Plan

| Sprint | Duration | Deliverable |
|---|---|---|
| **Sprint 1** | Week 1 | FastAPI backend + Gemini chat + basic UI with mic button |
| **Sprint 2** | Week 2 | ChromaDB memory + persona system prompts + TTS voice output |
| **Sprint 2.5** | Week 2 | Interest extractor + dynamic interests array + Tavily research engine |
| **Sprint 3** | Week 3 | Speaker ID (SpeechBrain) + auto user detection |
| **Sprint 4** | Week 4 | Memory writer (auto-extract preferences, routines) |
| **Sprint 5** | Week 5 | Proactive suggestions + reminder scheduler |
| **Sprint 6** | Week 6 | Multi-language tone + polish + local hardware testing |
| **Sprint 7+** | Month 3 | Raspberry Pi port + enclosure + wake word hardware |

---

## Open Questions

> [!IMPORTANT]
> **Language support**: Should Jack respond in Hindi, Hinglish (Hindi+English mix), or English only in Phase 1? This affects TTS voice selection and Gemini prompting significantly.

> [!IMPORTANT]
> **User onboarding**: How should new users register? Options:
> - Manual setup via web UI (name, age, gender, interests)
> - Voice-only onboarding ("Hi Jack, I'm Arjun, I'm 28...")
> - Hybrid: voice first, refine in UI

> [!NOTE]
> **Privacy**: All data stays on local machine / device. No cloud memory storage. Gemini API only receives anonymized conversation context (no stored PII sent to Google).

> [!TIP]
> **Starting point recommendation**: Build Sprint 1 immediately — the FastAPI backend + simple mic UI + Gemini chat. This gives you a working demo in 2–3 days that you can iterate on.

---

## Verification Plan

### Phase 1 Tests:
- [ ] Mic button records and transcribes correctly via Whisper
- [ ] Gemini returns a personalized response based on selected user profile
- [ ] TTS plays audio back through the speaker
- [ ] Memory stored in ChromaDB after each turn
- [ ] Interest array updated after each conversation turn
- [ ] Tavily research runs on schedule and updates `latest_news` field
- [ ] Proactive trigger fires when new interest news arrives
- [ ] Jack initiates morning check-in at 8am automatically

### Phase 2 Tests:
- [ ] Speak as 4 different people, system correctly identifies each
- [ ] Each user gets a different response persona and voice
- [ ] Memory from past conversations recalled correctly

### Phase 3 Tests:
- [ ] Time-based reminder fires at correct time
- [ ] Food/activity suggestions match user preferences from memory
- [ ] New preference learned mid-conversation is stored and recalled next session
