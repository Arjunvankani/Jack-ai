"""
TTS — Text to Speech using edge-tts (Microsoft Neural Voices, free).
Returns audio as bytes so the FastAPI route can stream it to the browser.
"""

import asyncio
import io
import edge_tts


async def synthesize(text: str, voice: str) -> bytes:
    """Convert text to speech. Returns MP3 bytes."""
    communicate = edge_tts.Communicate(text, voice)
    audio_buf = io.BytesIO()

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_buf.write(chunk["data"])

    return audio_buf.getvalue()


def get_voice_for_user(age: int, gender: str, language: str = "en") -> str:
    """
    Select an appropriate edge-tts voice based on user's persona target.
    Jack's RESPONSE voice (not the user's voice — Jack talks back in a complementary voice).
    """
    voice_map = {
        # (age_bucket, user_gender) -> Jack's voice (complementary)
        ("child",  "female"): "en-IN-PrabhatNeural",      # boy voice for girl child
        ("child",  "male"):   "en-IN-NeerjaNeural",        # girl voice for boy child
        ("teen",   "male"):   "en-IN-NeerjaNeural",        # girl bestie for teen boy
        ("teen",   "female"): "en-IN-PrabhatNeural",       # boy bestie for teen girl
        ("adult",  "male"):   "en-GB-SoniaNeural",         # professional woman for adult man
        ("adult",  "female"): "en-GB-RyanNeural",          # professional man for adult woman
        ("senior", "male"):   "en-IN-NeerjaNeural",        # caring woman for senior man
        ("senior", "female"): "en-IN-PrabhatNeural",       # caring man for senior woman
    }

    if age <= 12:
        bucket = "child"
    elif age <= 19:
        bucket = "teen"
    elif age <= 55:
        bucket = "adult"
    else:
        bucket = "senior"

    # Hindi / Hinglish override
    if language == "hi":
        return "hi-IN-SwaraNeural" if gender == "male" else "hi-IN-MadhurNeural"

    return voice_map.get((bucket, gender), "en-IN-NeerjaNeural")
