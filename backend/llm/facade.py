"""
LLM Facade — selects between Gemini and Groq based on settings.
"""

from backend.config import settings
from backend.llm import gemini_client, groq_client
from backend.memory import conversation_window as cw

async def chat(user_id: str, user_message: str, system_prompt: str) -> tuple[str, dict]:
    if settings.llm_provider == "groq":
        reply, usage = await groq_client.chat(user_id, user_message, system_prompt)
    else:
        reply, usage = await gemini_client.chat(user_id, user_message, system_prompt)
    
    # Handle lazy compression summary improvement
    summary = cw.get_session_summary(user_id)
    if summary and summary.startswith("Summary of earlier chat:"):
        old_text = summary.replace("Summary of earlier chat: ", "")
        prompt = f"Summarize this conversation excerpt in 2-3 sentences, focusing on key facts:\n{old_text}"
        better = simple_call(prompt)
        cw.set_compressed_summary(user_id, better)
        
    return reply, usage

def simple_call(prompt: str) -> str:
    if settings.llm_provider == "groq":
        return groq_client.simple_call(prompt)
    else:
        return gemini_client.simple_call(prompt)
