"""
Jack AI — Entry Point
Run with: python run.py
"""

import sys
import os

# Force UTF-8 output on Windows to handle emoji in print statements
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import uvicorn

if __name__ == "__main__":
    # Ensure .env exists
    if not os.path.exists(".env"):
        print("[WARN] No .env file found. Copying from .env.example...")
        import shutil
        shutil.copy(".env.example", ".env")
        print("[INFO] Created .env — please add your GEMINI_API_KEY before chatting!\n")

    print("[INFO] Starting Jack AI server at http://localhost:8000")
    print("[INFO] Open http://localhost:8000 in your browser\n")

    port = int(os.environ.get("PORT", 8000))
    is_prod = "PORT" in os.environ

    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1" if not is_prod else "0.0.0.0",
        port=port,
        reload=not is_prod,
        reload_dirs=["backend"],
    )
