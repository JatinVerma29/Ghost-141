"""
core/voice_engine.py — Voice with stop command support
Say "stop", "enough", "quiet" to interrupt speech instantly
"""
import time
import threading
import re
from core.speaker import stop_speaking

VOICE_AVAILABLE = False
sr = None

try:
    import speech_recognition as _sr
    import pyaudio as _pa
    _test = _pa.PyAudio()
    _test.terminate()
    sr = _sr
    VOICE_AVAILABLE = True
except Exception as e:
    print(f"[VOICE] Disabled: {e}")

WAKE_WORDS = [
    "ghost", "ghost 141", "ghost-141", "ghost141",
    "ghost dash", "hey ghost", "ok ghost", "coast"
]

STOP_WORDS = ["stop", "enough", "quiet", "silence", "shut up", "pause", "ok stop", "stop it"]

STT_CORRECTIONS = {
    "charge jpt":  "ChatGPT",
    "charge gpt":  "ChatGPT",
    "chart gpt":   "ChatGPT",
    "chat gbt":    "ChatGPT",
    "coast 141":   "Ghost-141",
    "ghost 41":    "Ghost-141",
    "goes 141":    "Ghost-141",
    "most 141":    "Ghost-141",
    "host 141":    "Ghost-141",
    "you tube":    "YouTube",
    "what's app":  "WhatsApp",
}


class VoiceEngine:
    def __init__(self, settings, brain, speaker, wake_word="ghost-141"):
        self.settings   = settings
        self.brain      = brain
        self.speaker    = speaker
        self._active    = True
        self.recognizer = None

        if VOICE_AVAILABLE:
            self.recognizer = sr.Recognizer()
            self.recognizer.energy_threshold         = 50
            self.recognizer.dynamic_energy_threshold = False
            self.recognizer.pause_threshold          = 2.0
            self.recognizer.phrase_threshold         = 0.3
            # Device 2 = AirBass Headphone mic (confirmed working)
            # Device 15 = fallback laptop mic
            self.mic_index = self._find_best_mic([2, 15, 1, 0])
            self._calibrate_once()

    def _correct(self, text: str) -> str:
        result = text
        lower  = text.lower()
        for wrong, right in STT_CORRECTIONS.items():
            if wrong in lower:
                result = re.sub(re.escape(wrong), right, result, flags=re.IGNORECASE)
                print(f"  [STT FIX] '{wrong}' → '{right}'")
        return result

    def _is_stop(self, text):
        t = text.lower().strip()
        return any(w in t for w in STOP_WORDS)

    def _is_wake_only(self, text):
        t = text.lower().strip().rstrip('.')
        return t in WAKE_WORDS

    def _strip_wake(self, text):
        t = text.strip()
        for w in sorted(WAKE_WORDS, key=len, reverse=True):
            low = t.lower()
            if low.startswith(w + " "):
                return t[len(w):].strip()
            if low.startswith(w + ","):
                return t[len(w)+1:].strip()
        return t

    def _calibrate_once(self):
        """Calibrate noise threshold once at startup — faster loop, no per-cycle delay."""
        try:
            mic = sr.Microphone(device_index=self.mic_index) if self.mic_index is not None else sr.Microphone()
            with mic as source:
                print("[VOICE] Calibrating microphone...")
                self.recognizer.adjust_for_ambient_noise(source, duration=1.5)
                print(f"[VOICE] Ready — threshold: {self.recognizer.energy_threshold:.0f}")
        except Exception as e:
            print(f"[VOICE] Calibration skipped: {e}")

    def _find_best_mic(self, candidates):
        """Try each device index and return the first one that opens successfully."""
        for idx in candidates:
            try:
                with sr.Microphone(device_index=idx) as source:
                    pass
                print(f"[VOICE] Using mic device [{idx}]")
                return idx
            except Exception:
                continue
        print("[VOICE] No specific mic found, using system default.")
        return None

    def listen_loop(self):
        if not VOICE_AVAILABLE:
            return

        print("[VOICE] Active — wake word: 'ghost-141' | Say 'stop' to interrupt Ghost.")

        while self._active:
            try:
                # When muted — skip mic entirely, just idle
                if self.brain.voice_muted:
                    time.sleep(0.5)
                    continue

                mic = sr.Microphone(device_index=self.mic_index) if self.mic_index is not None else sr.Microphone()
                with mic as source:
                    # No per-loop calibration — done once at startup for speed
                    try:
                        audio = self.recognizer.listen(source, timeout=4, phrase_time_limit=20)
                    except sr.WaitTimeoutError:
                        continue  # no speech — loop back, re-check mute

                text = self._transcribe(audio)
                if not text or len(text.strip()) < 2:
                    continue

                # Apply STT corrections
                text = self._correct(text)
                print(f"  [HEARD] {text}")
                text_lower = text.lower().strip()

                # Stop command — interrupt speech immediately
                if self._is_stop(text_lower):
                    stop_speaking()
                    print("  [STOPPED]")
                    continue

                # Pure wake word — acknowledge
                if self._is_wake_only(text_lower):
                    self.speaker.say("Yes, sir?")
                    continue

                # Strip wake word prefix and send to brain
                command = self._strip_wake(text)
                if command.strip():
                    threading.Thread(
                        target=self.brain.process,
                        args=(command.strip(),),
                        daemon=True
                    ).start()

            except sr.WaitTimeoutError:
                pass
            except Exception:
                time.sleep(0.3)

    def _transcribe(self, audio):
        try:
            return sr.Recognizer().recognize_google(audio)
        except sr.UnknownValueError:
            return None
        except Exception:
            return None

    def stop(self):
        self._active = False