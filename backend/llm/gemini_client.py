"""
Gemini API client.
Handles: chat with sliding window, one-shot text calls, and compression.
"""

import asyncio
import google.generativeai as genai
from google.api_core import exceptions
from backend.config import settings
from backend.memory import conversation_window as cw

genai.configure(api_key=settings.gemini_api_key)
_model = genai.GenerativeModel(settings.gemini_model)


async def async_retry(func, *args, max_retries=3, initial_delay=2, **kwargs):
    """Simple async exponential backoff for 429s."""
    delay = initial_delay
    last_exc = None
    for i in range(max_retries):
        try:
            return await asyncio.to_thread(func, *args, **kwargs)
        except exceptions.ResourceExhausted as e:
            last_exc = e
            print(f"[WARN] Gemini Quota Exceeded (429). Retrying in {delay}s... (Attempt {i+1}/{max_retries})")
            await asyncio.sleep(delay)
            delay *= 2
        except Exception as e:
            # For other errors, don't necessarily retry unless they are transient
            raise e
    raise last_exc


def simple_call(prompt: str) -> str:
    """Single-turn Gemini call. Handles its own basic retry for background tasks."""
    import time
    for _ in range(2):
        try:
            response = _model.generate_content(prompt)
            return response.text.strip()
        except exceptions.ResourceExhausted:
            time.sleep(2)
        except Exception:
            break
    return "Error: Could not complete call."


async def chat(user_id: str, user_message: str, system_prompt: str) -> tuple[str, dict]:
    """
    Full sliding-window chat call with strict system instruction enforcement.
    Returns: (reply_text, usage_metadata)
    """
    # Create a model instance with the specific system instruction for this turn/user
    model = genai.GenerativeModel(
        model_name=settings.gemini_model,
        system_instruction=system_prompt
    )

    # Add user turn to window
    cw.add_turn(user_id, "user", user_message)

    # Get context (may trigger compression)
    history = cw.get_window(user_id)

    # Build Gemini chat history (exclude the latest user turn added above, 
    # as we pass it to send_message)
    gemini_history = []
    for turn in history[:-1]:
        gemini_history.append({
            "role": turn["role"],
            "parts": [turn["content"]]
        })

    # Start a Gemini chat session with history
    chat_session = model.start_chat(history=gemini_history)

    # Use retry helper for the actual API call
    try:
        response = await async_retry(chat_session.send_message, user_message)
        reply = response.text.strip()
    except exceptions.ResourceExhausted:
        return "I'm a bit tired right now (API Quota exceeded). Let's chat in a few minutes!", {
            "prompt_tokens": 0, "candidates_tokens": 0, "total_tokens": 0
        }

    # Extract usage metadata
    usage = {
        "prompt_tokens": response.usage_metadata.prompt_token_count,
        "candidates_tokens": response.usage_metadata.candidates_token_count,
        "total_tokens": response.usage_metadata.total_token_count
    }

    # Add model reply to window
    cw.add_turn(user_id, "model", reply)

    return reply, usage


def compress_turns(turns: list[dict]) -> str:
    """Compress a list of {role, content} turns into a short summary."""
    lines = "\n".join(
        f"{'User' if t['role'] == 'user' else 'Jack'}: {t['content']}"
        for t in turns
    )
    return simple_call(
        f"Summarize this conversation in 2-3 sentences, preserving key facts:\n{lines[:2000]}"
    )
