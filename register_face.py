"""
register_face.py — Run this ONCE to register your face with Ghost-141.
Usage: python register_face.py
"""
import os, sys
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(os.path.expanduser("~/.ghost141/.env"))

from config.settings import Settings
from core.speaker import Speaker
from memory.memory_store import MemoryStore
from modules.face_recognition_controller import FaceController

def main():
    print("\n  Ghost-141 — Face Registration")
    print("  ─────────────────────────────")

    try:
        import face_recognition
        import cv2
    except ImportError:
        print("\n  ✗ Missing libraries. Install them first:\n")
        print("  pip install face-recognition opencv-python\n")
        print("  Note: face-recognition requires cmake + Visual Studio Build Tools on Windows.")
        print("  Windows install guide: https://github.com/ageitgey/face_recognition#installation")
        input("\n  Press Enter to exit...")
        sys.exit(1)

    settings = Settings()
    speaker  = Speaker(settings)
    memory   = MemoryStore(settings)
    face_ctrl = FaceController(settings, speaker, memory)

    name = input("\n  Enter your name: ").strip()
    if not name:
        print("  Name cannot be empty."); sys.exit(1)

    print(f"\n  Registering face for: {name}")
    print("  → Make sure your face is clearly visible to the webcam")
    print("  → Good lighting helps accuracy")
    print("  → Stay still during capture\n")

    input("  Press Enter when ready...")

    success = face_ctrl.register_face(name, num_samples=8)

    if success:
        # Store name in memory too
        memory.store("user_name", name, silent=True)
        print(f"\n  ✓ Face registered for {name}!")
        print("  Ghost-141 will now greet you automatically on startup.\n")
    else:
        print("\n  ✗ Registration failed. Check webcam and lighting, then try again.\n")

if __name__ == "__main__":
    main()