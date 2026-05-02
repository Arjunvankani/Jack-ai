from backend.config import settings
from backend.memory import conversation_window as cw

def _get_client():
    """Lazy initialization of Groq client."""
    try:
        from groq import Groq
        if not settings.groq_api_key:
            print("[ERROR] GROQ_API_KEY is empty in settings.")
            return None
        return Groq(api_key=settings.groq_api_key)
    except ImportError:
        print("[ERROR] Groq library not found. Run 'pip install groq'.")
        return None
    except Exception as e:
        print(f"[ERROR] Could not initialize Groq client: {e}")
        import traceback
        traceback.print_exc()
        return None

async def chat(user_id: str, user_message: str, system_prompt: str) -> tuple[str, dict]:
    """
    Full sliding-window chat call using Groq.
    """
    client = _get_client()
    if not client:
        return "Groq client is not configured.", {"prompt_tokens":0, "candidates_tokens":0, "total_tokens":0}

    # Add user turn to window
    cw.add_turn(user_id, "user", user_message)

    # Get context (may trigger compression)
    history = cw.get_window(user_id)

    # Build Groq messages
    messages = [{"role": "system", "content": system_prompt}]
    for turn in history:
        messages.append({
            "role": turn["role"] if turn["role"] != "model" else "assistant",
            "content": turn["content"]
        })

    try:
        completion = client.chat.completions.create(
            model=settings.groq_model,
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
            top_p=1,
            stream=False
        )
        
        reply = completion.choices[0].message.content.strip()
        
        # Groq usage info
        usage = {
            "prompt_tokens": completion.usage.prompt_tokens,
            "candidates_tokens": completion.usage.completion_tokens,
            "total_tokens": completion.usage.total_tokens
        }

        # Add model reply to window
        cw.add_turn(user_id, "model", reply)

        return reply, usage

    except Exception as e:
        print(f"[ERROR] Groq API Error: {e}")
        return "I'm having trouble connecting to my brain (Groq) right now. Please try again later.", {
            "prompt_tokens": 0, "candidates_tokens": 0, "total_tokens": 0
        }

def simple_call(prompt: str) -> str:
    """One-shot call for background tasks using Groq."""
    client = _get_client()
    if not client: return "Error"
    try:
        completion = client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=512
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        print(f"[ERROR] Groq Simple Call Error: {e}")
        return "Error"
