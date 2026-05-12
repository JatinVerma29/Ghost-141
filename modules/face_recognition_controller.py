"""
modules/face_recognition_controller.py — Ghost-141 Face Recognition v3.0
SECURITY MODE:
  - Face recognised     → Full access, memories unlocked, greets by name
  - Face NOT recognised → Guest mode, no memories, no personal data exposed
  - Guest cannot access user memories even if they ask
"""
import os, json, threading, time
import numpy as np

FACES_DIR = os.path.expanduser("~/.ghost141/faces")
FACES_DB  = os.path.expanduser("~/.ghost141/faces/db.json")


class FaceController:
    def __init__(self, settings, speaker, memory):
        self.settings  = settings
        self.sp        = speaker
        self.memory    = memory
        self.running   = False
        self.greeted   = False
        self._known_encodings = []
        self._known_names     = []
        self._cv2       = None
        self._fr        = None
        self._available = False
        self._load_libs()
        self._load_known_faces()

    def _load_libs(self):
        try:
            import cv2
            import face_recognition as fr
            self._cv2 = cv2
            self._fr  = fr
            self._available = True
            print("[FACE] Face recognition ready.")
        except ImportError:
            print("[FACE] face_recognition not installed. Face features disabled.")

    def _load_known_faces(self):
        if not self._available:
            return
        os.makedirs(FACES_DIR, exist_ok=True)
        if not os.path.exists(FACES_DB):
            return
        try:
            with open(FACES_DB) as f:
                db = json.load(f)
            for name, enc_list in db.items():
                self._known_names.append(name)
                self._known_encodings.append(np.array(enc_list))
            print(f"[FACE] Loaded {len(self._known_names)} known face(s): {self._known_names}")
        except Exception as e:
            print(f"[FACE] Error loading face DB: {e}")

    def register_face(self, name: str, num_samples: int = 8):
        if not self._available:
            print("[FACE] face_recognition not installed."); return False
        cv2 = self._cv2
        fr  = self._fr
        print(f"[FACE] Registering face for: {name}")
        self.sp.say(f"I will capture your face now. Please look at the camera, sir.")
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[FACE] Cannot open webcam."); return False
        encodings = []
        attempts  = 0
        while len(encodings) < num_samples and attempts < 80:
            ret, frame = cap.read()
            if not ret:
                attempts += 1; continue
            rgb  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            locs = fr.face_locations(rgb, model="hog")
            encs = fr.face_encodings(rgb, locs)
            if encs:
                encodings.append(encs[0].tolist())
                print(f"[FACE] Sample {len(encodings)}/{num_samples} captured.")
                time.sleep(0.3)
            attempts += 1
            cv2.waitKey(100)
        cap.release()
        cv2.destroyAllWindows()
        if len(encodings) < 2:
            print("[FACE] Not enough samples."); return False
        avg_enc = np.mean([np.array(e) for e in encodings], axis=0).tolist()
        os.makedirs(FACES_DIR, exist_ok=True)
        db = {}
        if os.path.exists(FACES_DB):
            with open(FACES_DB) as f:
                db = json.load(f)
        db[name] = avg_enc
        with open(FACES_DB, "w") as f:
            json.dump(db, f)
        if name not in self._known_names:
            self._known_names.append(name)
            self._known_encodings.append(np.array(avg_enc))
        print(f"[FACE] Registered: {name}")
        self.sp.say(f"Face registered successfully for {name}. I will recognise you from now on, sir.")
        return True

    def recognize_once(self, timeout: int = 8):
        """
        Scan webcam. Returns recognised name string, or None if not seen/matched.
        None means GUEST — no personal data should be shared.
        """
        if not self._available or not self._known_encodings:
            return None
        cv2 = self._cv2
        fr  = self._fr
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return None
        found_name = None
        deadline   = time.time() + timeout
        while time.time() < deadline:
            ret, frame = cap.read()
            if not ret:
                continue
            rgb  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            locs = fr.face_locations(rgb, model="hog")
            encs = fr.face_encodings(rgb, locs)
            for enc in encs:
                distances = fr.face_distance(self._known_encodings, enc)
                if len(distances) == 0:
                    continue
                best_idx = int(np.argmin(distances))
                if distances[best_idx] < 0.48:   # Slightly tighter threshold for security
                    found_name = self._known_names[best_idx]
                    break
            if found_name:
                break
            time.sleep(0.2)
        cap.release()
        return found_name

    def greet_on_startup(self, brain=None):
        """
        SECURITY LOGIC:
        - Face seen + matched  → Full profile unlocked, greet by name
        - Face seen + unknown  → Guest mode, warn unknown user
        - No face detected     → Guest mode, generic greeting
        """
        if not self._available:
            def _generic():
                time.sleep(2)
                if brain: brain.set_guest_mode()
                self.sp.say("Ghost-141 online. Identity not verified. Running in guest mode, sir.")
            threading.Thread(target=_generic, daemon=True).start()
            return

        def _task():
            time.sleep(2)
            if self.greeted:
                return

            print("[FACE] Scanning for known face...")
            name = self.recognize_once(timeout=7)

            hour = time.localtime().tm_hour
            if   hour < 12: tod = "Good morning"
            elif hour < 17: tod = "Good afternoon"
            else:           tod = "Good evening"

            self.greeted = True

            if name:
                # ── OWNER RECOGNISED ────────────────────────────────────────
                self.memory.store("user_name", name, silent=True)
                if brain:
                    brain.face_confirmed = True
                    brain.set_owner_mode(name)
                self.sp.say(f"{tod}, {name}. Identity confirmed. Ghost-141 fully operational.")
                print(f"[FACE] OWNER: {name} — Full access granted.")
            else:
                # ── GUEST / UNKNOWN ──────────────────────────────────────────
                if brain:
                    brain.set_guest_mode()
                self.sp.say(
                    f"{tod}. Identity not recognised. Running in guest mode. "
                    f"Personal data is protected. Please look at the camera and say 'verify my identity' to authenticate."
                )
                print("[FACE] GUEST MODE — No face matched. Personal data locked.")

        threading.Thread(target=_task, daemon=True).start()

    def stop(self):
        self.running = False

    @property
    def is_available(self):
        return self._available

    @property
    def known_faces(self):
        return list(self._known_names)