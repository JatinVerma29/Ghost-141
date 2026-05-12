"""
config/settings.py — Ghost-141 Settings v2.1
"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
    load_dotenv(os.path.expanduser("~/.ghost141/.env"))
except:
    pass


class Settings:
    def __init__(self):
        self.groq_api_key   = os.getenv("GROQ_API_KEY", "")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")

        # Always use smarter free model
        self.groq_model = "llama-3.3-70b-versatile"
        self.model      = self.groq_model   # backward compat

        print(f"[SETTINGS] Model: {self.groq_model}")

        # ── Voice ─────────────────────────────────────────────────────────
        # CUSTOM WAKE WORD — change this to anything you like
        # Examples: "jarvis", "computer", "hey ghost", "nova", "atlas"
        self.wake_word    = os.getenv("WAKE_WORD", "ghost-141")
        self.voice_rate   = 165
        self.voice_volume = 0.9
        self.edge_voice   = "en-GB-RyanNeural"   # Jarvis-like English voice
        # Hindi voice is auto-selected in speaker.py (hi-IN-MadhurNeural)

        # ── Behaviour ─────────────────────────────────────────────────────
        self.confirm_destructive = True
        self.auto_learn          = True
        self.verbose_logging     = True

        # ── Paths ─────────────────────────────────────────────────────────
        self.memory_dir      = os.path.expanduser("~/.ghost141")
        self.screenshot_dir  = os.path.expanduser("~/Desktop")
        self.default_browser = "chrome"

        # ── Smart home (future) ───────────────────────────────────────────
        self.ha_url   = os.getenv("HA_URL",   "")
        self.ha_token = os.getenv("HA_TOKEN", "")

        os.makedirs(self.memory_dir, exist_ok=True)