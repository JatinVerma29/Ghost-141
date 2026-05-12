"""
core/speaker.py — Ghost-141 Speaker v3.2
- Auto-detects Hindi text → switches to hi-IN-MadhurNeural (Indian male)
- English text → en-GB-RyanNeural (British Jarvis-like)
- No language mixing issues
- pygame banner suppressed
- JSON leak guard added
"""

import threading
import queue
import os
import tempfile
import time
import re

# Suppress pygame banner
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"


def _is_hindi(text: str) -> bool:
    """Detect if text contains Devanagari script (Hindi)."""
    return bool(re.search(r'[\u0900-\u097F]', text))


def _clean_for_speech(text: str) -> str:
    """Remove any JSON fragments that leak into speak text."""
    # If it looks like raw JSON leaked in, strip it
    if '"steps"' in text or '"module"' in text or '"confirmation_needed"' in text:
        # Extract just the speak value if possible
        m = re.search(r'"speak"\s*:\s*"([^"]+)"', text)
        if m:
            return m.group(1)
        # Otherwise strip JSON-like content
        text = re.sub(r'\{[^}]*\}', '', text)
        text = re.sub(r'"[a-z_]+"\s*:', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
    return text


class Speaker:
    def __init__(self, settings):
        self.settings      = settings
        self.q             = queue.Queue()
        self._stopped      = False
        self._engine       = None
        self._use_edge     = False
        self._voice_en     = getattr(settings, "edge_voice", "en-GB-RyanNeural")
        self._voice_hi     = "hi-IN-MadhurNeural"   # Indian Hindi male — natural accent

        self._init_edge()
        if not self._use_edge:
            self._init_pyttsx3()

        threading.Thread(target=self._worker, daemon=True).start()
        print("[SPEAKER] Voice system ready.")

    # ── Edge-TTS init ──────────────────────────────────────────────────────────
    def _init_edge(self):
        try:
            import edge_tts
            self._use_edge = True
            print(f"[SPEAKER] Edge-TTS ready — EN: {self._voice_en} | HI: {self._voice_hi}")
        except ImportError:
            self._use_edge = False
            print("[SPEAKER] edge-tts not found. Run: pip install edge-tts pygame")
            print("[SPEAKER] Falling back to pyttsx3.")

    # ── pyttsx3 fallback ───────────────────────────────────────────────────────
    def _init_pyttsx3(self):
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty("rate",   getattr(self.settings, "voice_rate",   175))
            self._engine.setProperty("volume", getattr(self.settings, "voice_volume", 1.0))
            for v in self._engine.getProperty("voices"):
                if any(n in v.name.lower() for n in ["male","david","mark","george","richard"]):
                    self._engine.setProperty("voice", v.id)
                    break
            print("[SPEAKER] pyttsx3 fallback ready.")
        except Exception as e:
            print(f"[SPEAKER] pyttsx3 init failed: {e}")
            self._engine = None

    # ── Public API ─────────────────────────────────────────────────────────────
    def say(self, text: str):
        """Non-blocking — queues text, prints to console."""
        if not text or not text.strip():
            return
        text = _clean_for_speech(text)
        if not text.strip():
            return
        print(f"[GHOST-141] {text}")
        self.q.put(text.strip())

    def stop(self):
        while not self.q.empty():
            try: self.q.get_nowait()
            except Exception: break

    def stop_speaking(self):
        """Alias — required by voice_engine.py import."""
        self.stop()

    # ── Worker ─────────────────────────────────────────────────────────────────
    def _worker(self):
        while not self._stopped:
            try:
                text = self.q.get(timeout=0.5)
                self._speak(text)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[SPEAKER ERR] {e}")

    def _speak(self, text: str):
        if self._use_edge:
            self._speak_edge(text)
        elif self._engine:
            self._speak_pyttsx3(text)

    def _speak_edge(self, text: str):
        """Auto-selects Hindi or English voice based on script detected."""
        try:
            import edge_tts, asyncio

            # Choose voice based on language
            voice = self._voice_hi if _is_hindi(text) else self._voice_en

            tmp      = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            tmp_path = tmp.name
            tmp.close()

            async def _gen():
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(tmp_path)

            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed(): raise RuntimeError
                loop.run_until_complete(_gen())
            except RuntimeError:
                asyncio.run(_gen())

            # Check file actually has content
            if os.path.getsize(tmp_path) < 100:
                raise ValueError("Empty audio file generated")

            self._play_mp3(tmp_path)

            try: os.unlink(tmp_path)
            except Exception: pass

        except Exception as e:
            print(f"[SPEAKER] Edge-TTS error: {e}")
            # Don't permanently fall back — just skip this utterance
            # Edge-TTS will retry on next say() call
            try: os.unlink(tmp_path)
            except Exception: pass

    def _play_mp3(self, path: str):
        # Method 1: pygame
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                time.sleep(0.05)
            pygame.mixer.music.stop()
            pygame.mixer.quit()
            return
        except Exception:
            pass

        # Method 2: playsound
        try:
            from playsound import playsound
            playsound(path, block=True)
            return
        except Exception:
            pass

        # Method 3: Windows PowerShell
        try:
            import subprocess
            subprocess.run(
                ["powershell", "-c",
                 f"Add-Type -AssemblyName presentationCore; "
                 f"$mp = [System.Windows.Media.MediaPlayer]::new(); "
                 f"$mp.Open([uri]'{path}'); $mp.Play(); Start-Sleep 5"],
                timeout=10, capture_output=True
            )
            return
        except Exception:
            pass

        print("[SPEAKER] Could not play audio. Install pygame: pip install pygame")

    def _speak_pyttsx3(self, text: str):
        """pyttsx3 fallback — works for English only."""
        if _is_hindi(text):
            # pyttsx3 can't speak Hindi — transliterate notice
            print(f"[SPEAKER] Hindi text (pyttsx3 cannot speak Hindi): {text}")
            try:
                self._engine.say("Hindi text received but voice engine does not support Hindi.")
                self._engine.runAndWait()
            except Exception:
                pass
            return
        try:
            self._engine.say(text)
            self._engine.runAndWait()
        except Exception as e:
            print(f"[SPEAKER] pyttsx3 error: {e}")


# Module-level alias for voice_engine.py import
def stop_speaking():
    """Legacy import stub — voice_engine does: from core.speaker import stop_speaking"""
    pass