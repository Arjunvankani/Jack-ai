# Jack AI — Personalized AI Voice Companion

Jack AI is a production-ready, locally-run AI companion with proactive intelligence, multi-user personalization, and long-term memory.

## 🚀 Quick Start

### 1. Install Dependencies
Ensure you have Python 3.10+ installed. Then run:
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
Create a `.env` file in the root directory (or let `run.py` create one for you) and add your Gemini API Key:
```env
GEMINI_API_KEY=your_api_key_here
TAVILY_API_KEY=your_tavily_key_here (optional, for research engine)
```

### 3. Run the Application
Start both the backend and frontend with a single command:
```bash
python run.py
```
*   **Backend:** Running on `http://localhost:8000`
*   **Frontend:** Open `http://localhost:8000` in your browser to start chatting.

---

## 📝 Conversation Logs

Each conversation session is automatically logged to **`jack_log.json`** in the root directory. This file tracks:
- **Timestamp**: When the message occurred.
- **User Info**: ID and Name.
- **Input/Output**: The user message and Jack's response.
- **Token Usage**: Prompt tokens, candidate tokens, and total tokens used for each turn.

### Log Format Example:
```json
[
  {
    "timestamp": "2026-05-02T15:30:00.000000",
    "user_id": "user_123",
    "user_name": "Arjun",
    "input": "Hey Jack, how's it going?",
    "output": "I'm doing great! Ready to help you with your projects.",
    "token_usage": {
      "prompt_tokens": 45,
      "candidates_tokens": 12,
      "total_tokens": 57
    }
  }
]
```

---

## 🛠️ Tech Stack
- **Backend:** FastAPI (Python)
- **Frontend:** Vanilla HTML/JS/CSS (Premium Dark Mode)
- **AI Engine:** Google Gemini (Generative AI)
- **Memory:** SQLite (Metadata) + ChromaDB (Vector Store for Interests)
- **Voice:** Edge-TTS (Multi-lingual support)
- **Automation:** Background Scheduler for autonomous research
