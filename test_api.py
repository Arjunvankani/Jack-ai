import requests
import time
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

API = "http://localhost:8000"

print("1. Getting users...")
res = requests.get(f"{API}/api/users")
print(res.json())

print("\n2. Creating user...")
res = requests.post(f"{API}/api/users", json={
    "name": "Arjun",
    "age": 25,
    "gender": "male",
    "language": "en",
    "avatar_emoji": "🧑"
})
user = res.json()
print(user)
user_id = user["id"]

print("\n3. Sending chat message (This might take a few seconds)...")
start = time.time()
res = requests.post(f"{API}/api/chat", json={
    "user_id": user_id,
    "message": "Hey Jack, my name is Arjun. I really love playing cricket and watching sci-fi movies.",
    "return_audio": True
})
print(f"Chat request took {time.time() - start:.2f} seconds")

if res.status_code == 200:
    chat_res = res.json()
    print("Jack's reply:", chat_res["reply"])
    print("Audio URL:", chat_res["audio_url"])
    print("Interests Snapshot:", chat_res["interests_snapshot"])
else:
    print("Error:", res.status_code, res.text)

print("\n4. Getting interests...")
res = requests.get(f"{API}/api/interests/{user_id}")
print(res.json())
