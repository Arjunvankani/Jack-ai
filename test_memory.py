
import sys
import os
import json

# Add project root to path
sys.path.append(os.getcwd())

from backend.memory.chroma_store import save_interests, get_interests, store_memory, recall_memories
from backend.config import settings

def test_storage():
    user_id = "test_user_123"
    
    print(f"--- Testing Interests ---")
    interests = [{"topic": "Coding", "intensity": 0.9, "mention_count": 10}]
    save_interests(user_id, interests)
    print("Saved interests.")
    
    loaded = get_interests(user_id)
    print(f"Loaded interests: {loaded}")
    
    if loaded == interests:
        print("✅ Interests persistence check passed.")
    else:
        print("❌ Interests persistence check failed.")

    print(f"\n--- Testing Episodic Memory ---")
    fact = "The user loves building AI companions."
    store_memory(user_id, fact)
    print("Saved memory fact.")
    
    recalled = recall_memories(user_id, "What does the user love?")
    print(f"Recalled: {recalled}")
    
    if fact in recalled:
        print("✅ Episodic memory check passed.")
    else:
        print("❌ Episodic memory check failed.")

if __name__ == "__main__":
    # Ensure directory exists
    os.makedirs(settings.chroma_persist_dir, exist_ok=True)
    test_storage()
