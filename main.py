"""
GHOST-141 — Autonomous AI System Controller v5.5 "JARVIS MODE"
"""
import threading, time, sys, os, warnings
warnings.filterwarnings("ignore")

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(os.path.expanduser("~/.ghost141/.env"))

from core.voice_engine import VoiceEngine
from core.brain import Brain
from core.speaker import Speaker
from memory.memory_store import MemoryStore
from modules.system_controller import SystemController
from modules.web_controller import WebController
from modules.file_controller import FileController
from modules.app_controller import AppController
from modules.face_recognition_controller import FaceController
from config.settings import Settings

BANNER = """
  ██████  ██   ██  ██████  ███████ ████████       ██  ██  ██
 ██       ██   ██ ██    ██ ██         ██          ███████ ███
 ██   ███ ███████ ██    ██ ███████    ██    ████  ██   ██  ██
 ██    ██ ██   ██ ██    ██      ██    ██           ██  ██  ██
  ██████  ██   ██  ██████  ███████    ██            ██ ██  ██

  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARVIS MODE  |  v5.5  |  llama-3.3-70b  |  Ghost-141
  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

HELP_TEXT = """
  ┌──────────────────────────────────────────────────────────┐
  │               GHOST-141 COMMAND REFERENCE                │
  ├───────────────────┬──────────────────────────────────────┤
  │ Apps              │ open chrome / whatsapp / spotify      │
  │ Web               │ search for X / play X on youtube      │
  │ Real-time         │ weather in Delhi / cricket score      │
  │ News              │ latest news / West Bengal news        │
  │ IPL               │ IPL points table / RCB standings      │
  │ System            │ screenshot / volume 60 / lock         │
  │ Files             │ open downloads / create note          │
  │ Memory            │ remember X / what is my name          │
  │ Face              │ register my face / verify my identity │
  │ Email             │ draft email / read the email          │
  │ Email edit        │ add X / change subject / replace Y    │
  │ Email send        │ open the email / send the email       │
  │ Reminders         │ remind me in 10 minutes               │
  │ Knowledge         │ what is black hole / sin 45           │
  │ Hindi             │ kya tum hindi mein baat kar sakte ho  │
  │ Mute              │ mute yourself / 1234 to unmute        │
  │ Help              │ help / commands                       │
  │ Exit              │ exit / quit / bye                     │
  └───────────────────┴──────────────────────────────────────┘
"""


def handle_face_commands(cmd_lower, face_ctrl, brain, speaker):
    if "register my face" in cmd_lower or "register face" in cmd_lower:
        name = brain.memory.recall("user_name")
        if not name or "don't have" in name.lower():
            name = input("  Enter your name for face registration: ").strip()
        if name:
            face_ctrl.register_face(name)
        return True

    if any(x in cmd_lower for x in ["who am i", "can you see me",
                                      "do you recognise me", "do you recognize me"]):
        speaker.say("Let me take a look, sir.")
        name = face_ctrl.recognize_once(timeout=7)
        if name:
            brain.set_owner_mode(name)
            speaker.say(f"I can see you clearly. You are {name}, sir. Identity confirmed.")
        else:
            brain.set_guest_mode()
            speaker.say(
                "I cannot detect a recognised face right now, sir. "
                "Please ensure good lighting and face the camera directly."
            )
        return True

    if "known faces" in cmd_lower or "who do you know" in cmd_lower:
        faces = face_ctrl.known_faces
        if faces:
            speaker.say(f"I have {len(faces)} face{'s' if len(faces)>1 else ''} registered: {', '.join(faces)}, sir.")
        else:
            speaker.say("No faces registered yet, sir. Say 'register my face' to get started.")
        return True

    return False


def main():
    print(BANNER)

    settings = Settings()
    if not settings.groq_api_key:
        print("  ERROR: GROQ_API_KEY not found in .env")
        print("  Get free key: https://console.groq.com")
        input("\n  Press Enter to exit...")
        sys.exit(1)

    print("  Initialising systems...\n")

    speaker   = Speaker(settings)
    memory    = MemoryStore(settings)
    sys_ctrl  = SystemController(settings)
    web_ctrl  = WebController(settings)
    file_ctrl = FileController(settings)
    app_ctrl  = AppController(settings)
    brain     = Brain(settings, memory, sys_ctrl, web_ctrl, file_ctrl, app_ctrl, speaker)
    face_ctrl = FaceController(settings, speaker, memory)

    brain.face_ctrl = face_ctrl
    face_ctrl.greet_on_startup(brain=brain)

    wake_word    = getattr(settings, "wake_word", "ghost-141")
    voice_engine = VoiceEngine(settings, brain, speaker, wake_word)
    threading.Thread(target=voice_engine.listen_loop, daemon=True).start()

    print(HELP_TEXT)
    print(f"  Wake word: '{wake_word}' | Mute PIN: {brain.mute_password}")
    print("  Ready. Speak or type your command.\n")

    while True:
        try:
            user_input = input(">> ").strip()
            if not user_input:
                continue

            cmd_lower = user_input.lower().strip()

            # ── Mute check ──────────────────────────────────────────────────
            if brain.voice_muted:
                # PIN / unmute → restore mic
                if cmd_lower in (brain.mute_password, "unmute", "unmute yourself",
                                 "enable voice", "start listening"):
                    brain.process(user_input)
                else:
                    # Mic is OFF, but TEXT commands work normally — no restriction
                    print("  [MIC MUTED] Responding via text...")
                    brain.process(user_input)
                continue

            # ── Built-in commands ───────────────────────────────────────────
            if cmd_lower in ("help", "commands", "?"):
                print(HELP_TEXT); continue

            if cmd_lower in ("exit", "quit", "bye", "goodbye", "shutdown ghost"):
                speaker.say("Goodbye, sir. Ghost-141 shutting down.")
                sys.exit(0)

            # ── Face commands ───────────────────────────────────────────────
            if handle_face_commands(cmd_lower, face_ctrl, brain, speaker):
                continue

            # ── All other commands → brain ──────────────────────────────────
            brain.process(user_input)

        except KeyboardInterrupt:
            print("\n\n  [GHOST-141] Interrupted. Goodbye, sir.")
            sys.exit(0)


if __name__ == "__main__":
    main()