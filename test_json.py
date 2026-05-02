
import re
import json

def _extract_json(text: str) -> list | dict | None:
    """Extract JSON from text using regex, handling conversational padding."""
    match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            return None
    return None

def test():
    dirty_json = """
    Sure thing! Here is what I found about the user's interests:
    ```json
    [
        {"topic": "Reading", "category": "hobby"},
        {"topic": "Walking", "category": "health"}
    ]
    ```
    I hope that helps!
    """
    extracted = _extract_json(dirty_json)
    print(f"Extracted: {extracted}")
    if extracted and len(extracted) == 2:
        print("✅ Extraction logic works!")
    else:
        print("❌ Extraction logic failed!")

if __name__ == "__main__":
    test()
