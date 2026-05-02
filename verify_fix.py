
import sys
import os
import json
import re

# Add project root to path
sys.path.append(os.getcwd())

from backend.memory.memory_writer import update_interests_from_text, _extract_json
from backend.db.models import SessionLocal, init_db, UserProfile
from backend.db.crud import create_user, get_user
from backend.memory.chroma_store import get_interests

def test_robust_extraction():
    print("--- Testing Robust JSON Extraction ---")
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
    assert isinstance(extracted, list)
    assert len(extracted) == 2
    assert extracted[0]["topic"] == "Reading"
    print("✅ Extraction test passed.")

def test_dual_sync():
    print("\n--- Testing Dual-Sync Storage ---")
    init_db()
    db = SessionLocal()
    
    # Create a dummy user
    user = create_user(db, name="TestUser", age=25, gender="male")
    user_id = user.id
    
    def mock_gemini(prompt):
        return '[{"topic": "Testing", "category": "qa"}]'
    
    # Trigger update
    update_interests_from_text(user_id, "I love testing code.", mock_gemini)
    
    # Check SQLite
    db.refresh(user)
    print(f"SQLite Interests: {user.interests}")
    assert any(i["topic"] == "Testing" for i in user.interests)
    
    # Check ChromaDB
    chroma_interests = get_interests(user_id)
    print(f"ChromaDB Interests: {chroma_interests}")
    assert any(i["topic"] == "Testing" for i in chroma_interests)
    
    print("✅ Dual-sync test passed.")
    db.close()

if __name__ == "__main__":
    try:
        test_robust_extraction()
        test_dual_sync()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
