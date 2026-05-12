"""
core/brain.py — Ghost-141 Brain v5.6
Fixes:
  - Email edits NO LONGER create new drafts — intercepted BEFORE hitting Groq
  - Mute flag checked in voice_engine via brain.voice_muted
  - All 6 previous fixes retained
"""
import re, json, time, requests, math, threading, os
from datetime import datetime
from collections import deque

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
}

def now():
    return datetime.now().strftime("%A %B %d %Y, %I:%M %p")

def _is_hindi(text: str) -> bool:
    return bool(re.search(r'[\u0900-\u097F]', text))

def _safe_print(text: str):
    try:
        print(text)
    except (UnicodeEncodeError, UnicodeDecodeError):
        print(text.encode('ascii', errors='replace').decode('ascii'))


# ── SYSTEM PROMPTS ──────────────────────────────────────────────────────────────
OWNER_SYSTEM = """You are Ghost-141, an AI modelled after J.A.R.V.I.S from Iron Man.
Sharp, confident, slightly witty, deeply loyal. Address owner as "sir".
Be concise — max 2 sentences unless explaining something complex.

Return ONLY a single valid JSON object. No markdown. No explanation outside JSON.
Format: {"speak":"response","steps":[],"confirmation_needed":false}

MODULES:
- app: open/close — chrome, firefox, edge, notepad, vscode, whatsapp, telegram, discord,
       spotify, youtube, calculator, files, explorer, terminal, cmd, powershell, zoom,
       slack, teams, paint, settings, task manager, steam, xbox, camera, photos, store, gmail, google
- web: search(query), youtube(query), navigate(url), news(topic)
- system: screenshot, volume(level), brightness(level), lock, type_text(text),
          run_cmd(command), show_info, check_updates, remind(message, seconds)
- file: open(path), list(directory), create(path, content)
- email: draft(to, subject, body), read_draft, update_draft(field, new_value), open_draft
- memory: remember(key, value), recall(key), forget(key), forget_all
- realtime: weather(city), news(topic), cricket_score, ipl_points, wikipedia(query)
- smarthome: light(room, action, brightness), thermostat(temp), scene(name)

EMAIL RULES — CRITICAL:
- READ email → email → read_draft
- MODIFY/ADD/REMOVE/CHANGE/EDIT/UPDATE email → email → update_draft
- OPEN/SEND email → email → open_draft
- NEW draft ONLY when user says "draft", "write", "compose", "new email"
- NEVER use action "draft" when user wants to edit an existing email

update_draft fields:
  "subject"         → change subject line
  "to"              → change recipient
  "add_to_body"     → append text to body (value = text to add)
  "remove_from_body"→ remove text from body (value = text to remove, or "last line")
  "replace"         → replace old text with new (old = old text, new = new text)
  "body"            → replace entire body

LANGUAGE: Respond in the SAME language the user uses. Hindi → full Hindi, Devanagari script.
WRITING: Generate complete content (300+ words if asked).
IDENTITY: Owner is verified via face recognition.

EXAMPLES:
draft email to teacher about sick leave →
{"speak":"Drafting your email, sir.","steps":[{"module":"email","action":"draft","to":"","subject":"Sick Leave Application","body":"Respected Sir/Ma'am,\n\nI hope this message finds you well. I am writing to inform you that I am unable to attend classes today due to illness. I have been suffering from fever and am under medical supervision.\n\nI will ensure I cover all missed topics and submit any pending assignments upon recovery.\n\nKindly grant me leave for today.\n\nThank you for your understanding.\n\nYours sincerely,\nJatin Verma"}],"confirmation_needed":false}

add my name / also add Jatin / just add Jatin Verma →
{"speak":"Added your name, sir.","steps":[{"module":"email","action":"update_draft","field":"add_to_body","value":"Jatin Verma"}],"confirmation_needed":false}

remove Jatin Verma / remove my name →
{"speak":"Removed, sir.","steps":[{"module":"email","action":"update_draft","field":"remove_from_body","value":"Jatin Verma"}],"confirmation_needed":false}

change teacher's name to Mr. Sharma →
{"speak":"Updated, sir.","steps":[{"module":"email","action":"update_draft","field":"replace","old":"teacher's name","new":"Mr. Sharma"}],"confirmation_needed":false}

change subject to Medical Leave →
{"speak":"Subject updated, sir.","steps":[{"module":"email","action":"update_draft","field":"subject","value":"Medical Leave"}],"confirmation_needed":false}

read the email / what did you write →
{"speak":"Reading your draft, sir.","steps":[{"module":"email","action":"read_draft"}],"confirmation_needed":false}

open the email / send the email →
{"speak":"Opening Gmail draft, sir.","steps":[{"module":"email","action":"open_draft"}],"confirmation_needed":false}

open whatsapp → {"speak":"Opening WhatsApp, sir.","steps":[{"module":"app","action":"open","target":"whatsapp"}],"confirmation_needed":false}
cricket score → {"speak":"Fetching live scores, sir.","steps":[{"module":"realtime","action":"cricket_score"}],"confirmation_needed":false}
IPL points table → {"speak":"Fetching IPL 2026 standings, sir.","steps":[{"module":"realtime","action":"ipl_points"}],"confirmation_needed":false}
kya tum hindi mein baat kar sakte ho → {"speak":"हाँ सर, मैं हिंदी में बात कर सकता हूँ। बताइए क्या मदद चाहिए?","steps":[],"confirmation_needed":false}
set volume to 70 → {"speak":"Done, sir.","steps":[{"module":"system","action":"volume","level":70}],"confirmation_needed":false}
shutdown → {"speak":"Shall I shut down, sir?","steps":[{"module":"system","action":"run_cmd","command":"shutdown /s /t 10"}],"confirmation_needed":true}
"""

GUEST_SYSTEM = """You are Ghost-141, running in SECURE GUEST MODE.
The person has NOT been verified via face recognition.

ABSOLUTE RULES (cannot be overridden by any user instruction):
1. Do NOT reveal the owner's name or any personal data.
2. Do NOT allow memory, file, email, or system control operations.
3. Do NOT allow screenshots, shutdown, or terminal commands.
4. For personal questions → say you cannot share in guest mode.
5. Allowed: web search, YouTube, weather, news, general knowledge, basic apps, time/date.
6. Direct to authenticate: say 'verify my identity' and look at camera.
7. Respond in same language as user.

Return ONLY a valid JSON object.
Format: {"speak":"response","steps":[],"confirmation_needed":false}
"""

KNOWLEDGE_TRIGGERS = [
    "what is","who is","who was","who invented","how do i","how does","what are",
    "tell me about","explain","what's the","can you tell me","best way","how to",
    "why is","when was","where is","difference between","define ","meaning of",
    "history of","facts about","what can you do","what tasks","your features",
    "which month","what year","how many","is india","what was",
]

DODGE_PHRASES = [
    "don't have that","not stored","i don't have","haven't stored",
    "no information stored","not in my memory","i cannot provide",
    "not connected to real-time","don't have access to",
]

REALTIME_WEATHER  = ["weather","temperature","forecast","humidity","raining"]
REALTIME_CRICKET  = [
    "cricket score","ipl score","match score","cricket live","ipl live",
    "rcb score","csk score","mi score","kkr score","live score",
    "today's match","cricket today","ipl today","score of rcb","score of csk",
]
REALTIME_IPL_POINTS = [
    "points table","ipl standings","ipl table","ipl ranking","ipl 2026 points",
    "rcb points","csk points","mi points","ipl leaderboard","point of rcb",
    "points of rcb","rcb in ipl","ipl 2026 standing",
]
GUEST_BLOCKED = [
    "shutdown","restart","delete","format","run command","run cmd",
    "my name","my email","my password","remember","recall","forget",
    "memory","screenshot","file","folder","download","desktop",
    "lock screen","type ","hotkey",
]

# ── Email intent triggers — checked BEFORE hitting Groq ─────────────────────────
EMAIL_READ_TRIGGERS = [
    "read the email","read email","what did you write","what is in the email",
    "show me the email","what's the email","read it out","read that email",
    "tell me the email","what's written","what have you written",
]
EMAIL_OPEN_TRIGGERS = [
    "open the email","send the email","open gmail","open draft",
    "send it","open it in gmail","launch the email",
]
# These cause AI to wrongly call "draft" — intercept them locally
EMAIL_UPDATE_TRIGGERS = [
    "add ", "remove ", "change ", "modify ", "update the email",
    "replace ", "insert ", "edit the email", "fix the email",
    "also add", "also remove", "just add", "just remove",
    "put ", "delete from", "take out", "rewrite",
    "change subject", "change the subject", "change recipient",
    "change the recipient", "add my name", "remove my name",
    "add name", "add jatin", "remove jatin",
]


def try_local_math(cmd: str):
    cmd_l = cmd.lower().strip()
    m = re.fullmatch(r'\s*(sin|cos|tan|asin|acos|atan)\s*\(?\s*(\d+(?:\.\d+)?)\s*[°]?\s*\)?\s*', cmd_l)
    if m:
        fn, val = m.group(1), float(m.group(2))
        fns = {"sin":math.sin,"cos":math.cos,"tan":math.tan,
               "asin":math.asin,"acos":math.acos,"atan":math.atan}
        try:
            res = fns[fn](math.radians(val))
            return f"{fn}({int(val) if val==int(val) else val}deg) = {round(res,6)}"
        except: pass
    m = re.fullmatch(r'\s*sqrt\s*\(?\s*(\d+(?:\.\d+)?)\s*\)?\s*', cmd_l)
    if m:
        return f"sqrt({m.group(1)}) = {round(math.sqrt(float(m.group(1))),6)}"
    if re.fullmatch(r'[\d\s\+\-\*\/\.\(\)\%\^]+', cmd_l.strip()):
        if re.search(r'[\+\*\/\%]', cmd_l) or re.search(r'\d\s*\-\s*\d', cmd_l):
            try:
                return f"{cmd_l.strip()} = {eval(cmd_l.replace('^','**'),{'__builtins__':{}})}"
            except: pass
    if re.match(r'^(calculate|compute|evaluate|solve)\s+', cmd_l):
        expr = re.sub(r'^(calculate|compute|evaluate|solve)\s+','',cmd_l).replace('^','**').strip()
        if expr and re.fullmatch(r'[\d\s\+\-\*\/\.\(\)\%\*]+', expr):
            try:
                return f"{expr.replace('**','^').strip()} = {eval(expr,{'__builtins__':{}})}"
            except: pass
    return None


# ── Email edit AI helper ──────────────────────────────────────────────────────────
def _ai_parse_email_edit(cmd: str, draft: dict, groq_key: str, model: str) -> dict | None:
    """
    Ask AI to figure out WHAT to edit in the draft and return structured edit instruction.
    Returns dict with keys: field, value, old, new — or None on failure.
    """
    headers = {"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"}
    system  = f"""You are an email editing assistant. The user wants to modify this email draft:
To: {draft['to']}
Subject: {draft['subject']}
Body:
{draft['body']}

Based on the user's instruction, return ONLY a JSON object describing the edit.
Fields: field (one of: subject, to, add_to_body, remove_from_body, replace, body), value, old, new
Examples:
"add Jatin Verma"       → {{"field":"add_to_body","value":"Jatin Verma"}}
"remove Jatin Verma"    → {{"field":"remove_from_body","value":"Jatin Verma"}}
"remove last line"      → {{"field":"remove_from_body","value":"last line"}}
"change subject to X"   → {{"field":"subject","value":"X"}}
"replace teacher with Sir" → {{"field":"replace","old":"teacher","new":"Sir"}}
"add my phone number 9999" → {{"field":"add_to_body","value":"Phone: 9999"}}
Return ONLY the JSON. No explanation."""
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": cmd}
        ],
        "temperature": 0.1,
        "max_tokens":  200,
    }
    try:
        r = requests.post(GROQ_URL, headers=headers, json=body, timeout=15)
        if r.status_code == 200:
            raw = r.json()["choices"][0]["message"]["content"].strip()
            raw = re.sub(r"```json|```","",raw).strip()
            m   = re.search(r'\{.*\}', raw, re.DOTALL)
            if m:
                return json.loads(m.group())
    except Exception as e:
        _safe_print(f"  [EMAIL EDIT AI ERR] {e}")
    return None


# ── Real-time fetchers ─────────────────────────────────────────────────────────
def fetch_weather(city="Delhi"):
    try:
        r   = requests.get(f"https://wttr.in/{city.replace(' ','+')}?format=j1",
                           headers=BROWSER_HEADERS, timeout=8)
        cur = r.json()["current_condition"][0]
        return (f"Weather in {city}: {cur['weatherDesc'][0]['value']}, "
                f"{cur['temp_C']}C, feels like {cur['FeelsLikeC']}C. "
                f"Humidity {cur['humidity']}%, wind {cur['windspeedKmph']} km/h.")
    except:
        return f"Could not fetch weather for {city}."


def fetch_cricket_scores():
    from bs4 import BeautifulSoup
    for url in ["https://www.cricbuzz.com/cricket-match/live-scores",
                "https://www.espncricinfo.com/live-cricket-score"]:
        try:
            r = requests.get(url, headers=BROWSER_HEADERS, timeout=10)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                matches = []
                for sel in [".cb-lv-scrs-col",".cb-scr-wll-chvrn","[class*='score']"]:
                    for card in soup.select(sel)[:4]:
                        text = card.get_text(" ", strip=True)
                        if text and len(text) > 10: matches.append(text[:150])
                    if matches: break
                if matches: return "Live scores: " + " | ".join(matches)
        except: pass
    try:
        r = requests.get(
            "https://news.google.com/rss/search?q=IPL+2026+live+score+today&hl=en-IN&gl=IN&ceid=IN:en",
            headers=BROWSER_HEADERS, timeout=8)
        if r.status_code == 200:
            items = re.findall(r'<title>(.*?)</title>', r.text)[1:4]
            items = [re.sub(r'<[^>]+>','',h).strip() for h in items]
            if items: return "Latest: " + " | ".join(items)
    except: pass
    return "No live matches right now."


def fetch_ipl_points_table():
    from bs4 import BeautifulSoup
    try:
        r = requests.get(
            "https://www.cricbuzz.com/cricket-series/9237/indian-premier-league-2026/points-table",
            headers=BROWSER_HEADERS, timeout=10)
        if r.status_code == 200:
            soup  = BeautifulSoup(r.text, "html.parser")
            table = soup.select_one("table")
            if table:
                rows  = table.select("tr")
                lines = []
                for row in rows[1:11]:
                    cols = [td.get_text(strip=True) for td in row.select("td")]
                    if len(cols) >= 4: lines.append(f"{cols[0]}: {cols[1]}pts")
                if lines: return "IPL 2026 Points Table: " + ", ".join(lines)
    except: pass
    try:
        r = requests.get(
            "https://news.google.com/rss/search?q=IPL+2026+points+table&hl=en-IN&gl=IN&ceid=IN:en",
            headers=BROWSER_HEADERS, timeout=8)
        if r.status_code == 200:
            items = re.findall(r'<title>(.*?)</title>', r.text)[1:4]
            items = [re.sub(r'<[^>]+>','',h).strip() for h in items]
            if items: return "IPL 2026 standings: " + " | ".join(items)
    except: pass
    return None


def fetch_news_headlines(topic="world"):
    try:
        r     = requests.get(
            f"https://news.google.com/rss/search?q={topic.replace(' ','+')}&hl=en-IN&gl=IN&ceid=IN:en",
            headers=BROWSER_HEADERS, timeout=8)
        items = re.findall(r'<title>(.*?)</title>', r.text)[1:6]
        return [re.sub(r'<[^>]+>','',h).strip() for h in items]
    except: return []


def fetch_wikipedia_summary(query):
    try:
        r = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ','_')}",
            timeout=8)
        ext = r.json().get("extract","")
        return ". ".join(ext.split(". ")[:3])+"." if ext else None
    except: return None


# ── Smart Home ─────────────────────────────────────────────────────────────────
class SmartHomeController:
    def __init__(self, settings):
        self.url   = getattr(settings,"ha_url","")
        self.token = getattr(settings,"ha_token","")
        self.ready = bool(self.url and self.token)
        print(f"[SMARTHOME] {'Connected: '+self.url if self.ready else 'Not configured (HA_URL + HA_TOKEN in .env)'}")

    def _h(self):
        return {"Authorization":f"Bearer {self.token}","Content-Type":"application/json"}

    def light(self, room="living room", action="on", brightness=255):
        if not self.ready: return "Smart home not connected yet, sir."
        try:
            svc  = "turn_on" if action in ("on","dim","brighten") else "turn_off"
            data = {"entity_id":f"light.{room.lower().replace(' ','_')}"}
            if action != "off": data["brightness"] = max(0,min(255,brightness))
            r = requests.post(f"{self.url}/api/services/light/{svc}",headers=self._h(),json=data,timeout=5)
            return f"{room.title()} light turned {action}, sir." if r.status_code in (200,201) else "Command failed."
        except Exception as e: return f"Smart home error: {e}"

    def thermostat(self, temp=22, unit="C"):
        if not self.ready: return "Smart home not connected yet, sir."
        try:
            tc = temp if unit=="C" else (temp-32)*5/9
            r  = requests.post(f"{self.url}/api/services/climate/set_temperature",
                               headers=self._h(),json={"entity_id":"climate.main","temperature":tc},timeout=5)
            return f"Thermostat set to {temp} degrees, sir." if r.status_code in (200,201) else "Failed."
        except Exception as e: return f"Smart home error: {e}"

    def scene(self, name=""):
        if not self.ready: return "Smart home not connected yet, sir."
        try:
            r = requests.post(f"{self.url}/api/services/scene/turn_on",
                              headers=self._h(),
                              json={"entity_id":f"scene.{name.lower().replace(' ','_')}"},timeout=5)
            return f"Scene '{name}' activated, sir." if r.status_code in (200,201) else "Scene not found."
        except Exception as e: return f"Smart home error: {e}"


# ── Brain ───────────────────────────────────────────────────────────────────────
class Brain:
    def __init__(self, settings, memory, sys_ctrl, web_ctrl, file_ctrl, app_ctrl, speaker):
        self.settings        = settings
        self.memory          = memory
        self.sc              = sys_ctrl
        self.wc              = web_ctrl
        self.fc              = file_ctrl
        self.ac              = app_ctrl
        self.sp              = speaker
        self.smarthome       = SmartHomeController(settings)
        self.session_history = deque(maxlen=12)
        self._last_app_wait  = 0

        # Security
        self.is_owner       = False
        self.face_confirmed = False
        self.owner_name     = ""

        # Email draft state
        self.last_draft = {"to": "", "subject": "", "body": ""}
        self.has_draft  = False

        # Mute
        self.voice_muted   = False
        self.mute_password = "1234"

        # Face controller reference (set by main.py)
        self.face_ctrl = None

    # ── Security ──────────────────────────────────────────────────────────────
    def set_owner_mode(self, name: str):
        self.is_owner       = True
        self.face_confirmed = True
        self.owner_name     = name
        _safe_print(f"[BRAIN] OWNER MODE — {name}. Full access granted.")

    def set_guest_mode(self):
        self.is_owner       = False
        self.face_confirmed = False
        self.owner_name     = ""
        self.session_history.clear()
        _safe_print("[BRAIN] GUEST MODE — Personal data locked. Restricted access.")

    # ── Prompt ────────────────────────────────────────────────────────────────
    def _build_messages(self, cmd):
        messages = [{"role":"system","content":self._build_system_prompt()}]
        if self.is_owner:
            for e in self.session_history:
                messages += [{"role":"user","content":e["user"]},
                             {"role":"assistant","content":e["assistant"]}]
        messages.append({"role":"user","content":cmd})
        return messages

    def _build_system_prompt(self):
        if self.is_owner:
            prompt = OWNER_SYSTEM + f"\ncurrent_date: {now()}\nowner_name: {self.owner_name}"
            if self.has_draft:
                prompt += (f"\n\nACTIVE EMAIL DRAFT (do NOT create a new draft unless explicitly asked):\n"
                           f"To: {self.last_draft['to']}\n"
                           f"Subject: {self.last_draft['subject']}\n"
                           f"Body:\n{self.last_draft['body']}")
            ctx = self.memory.get_context_string()
            if ctx and ctx != "No stored preferences yet.":
                prompt += f"\n\nOwner profile:\n{ctx}"
            if self.smarthome.ready:
                prompt += "\n\nSmart home IS connected."
        else:
            prompt = GUEST_SYSTEM + f"\ncurrent_date: {now()}"
        return prompt

    def _add_to_history(self, user_cmd, reply):
        if reply and self.is_owner:
            self.session_history.append({"user": user_cmd, "assistant": str(reply)})

    def _is_blocked_in_guest(self, cmd_l: str) -> bool:
        return any(b in cmd_l for b in GUEST_BLOCKED)

    # ── Verify identity ────────────────────────────────────────────────────────
    def verify_identity_now(self):
        if not self.face_ctrl:
            self.sp.say("Face recognition not initialised, sir."); return
        self.sp.say("Scanning now, sir. Please look directly at the camera.")
        name = self.face_ctrl.recognize_once(timeout=8)
        if name:
            self.set_owner_mode(name)
            self.sp.say(f"Identity confirmed. Welcome, {name}. Full access restored, sir.")
        else:
            self.sp.say(
                "Face not recognised, sir. Ensure good lighting and face the camera directly, then try again."
            )

    # ── Main entry ────────────────────────────────────────────────────────────
    def process(self, cmd: str):
        cmd_l = cmd.lower().strip()
        _safe_print(f"\n[GHOST-141] <- {cmd}")
        key = self.settings.groq_api_key
        if not key:
            self.sp.say("No API key."); return

        # ── Mute/unmute ────────────────────────────────────────────────────
        if any(x in cmd_l for x in ["mute yourself","stop listening","mute voice",
                                     "disable voice","silence yourself","stop taking voice",
                                     "stop voice input"]):
            self.voice_muted = True
            self.sp.say(f"Voice input muted, sir. Type your PIN {self.mute_password} or press Enter to unmute.")
            _safe_print(f"[VOICE] MUTED — Type PIN ({self.mute_password}) to unmute.")
            return

        if cmd_l in (self.mute_password, "unmute", "unmute yourself",
                     "enable voice", "start listening", "resume voice"):
            self.voice_muted = False
            self.sp.say("Voice input restored, sir.")
            _safe_print("[VOICE] UNMUTED")
            return

        # ── Verify identity ────────────────────────────────────────────────
        if any(x in cmd_l for x in ["verify my identity","verify identity","authenticate",
                                     "scan my face","unlock access"]):
            self.verify_identity_now(); return

        # ── Guest block ────────────────────────────────────────────────────
        if not self.is_owner:
            if self._is_blocked_in_guest(cmd_l):
                self.sp.say(
                    "That is restricted in guest mode. "
                    "Look at the camera and say 'verify my identity' to authenticate."
                )
                return

        # ── Instant: time/date ─────────────────────────────────────────────
        if any(x in cmd_l for x in ["what time","current time","time is it","time now"]):
            msg = f"It is {datetime.now().strftime('%I:%M %p')}" + (", sir." if self.is_owner else ".")
            self.sp.say(msg); self._add_to_history(cmd, msg); return

        if any(x in cmd_l for x in ["what date","today's date","what day","which month",
                                     "what month","what year","what's today"]):
            msg = f"Today is {datetime.now().strftime('%A, %B %d, %Y')}" + (", sir." if self.is_owner else ".")
            self.sp.say(msg); self._add_to_history(cmd, msg); return

        if any(x in cmd_l for x in ["what is my name","what's my name"]) and self.is_owner:
            msg = f"Your name is {self.owner_name}, sir."
            self.sp.say(msg); self._add_to_history(cmd, msg); return

        # ── Local math ─────────────────────────────────────────────────────
        math_result = try_local_math(cmd_l)
        if math_result:
            self.sp.say(math_result); self._add_to_history(cmd, math_result); return

        # ── EMAIL INTERCEPTS (BEFORE hitting Groq) ─────────────────────────
        if self.is_owner and self.has_draft:

            # Read draft
            if any(t in cmd_l for t in EMAIL_READ_TRIGGERS):
                self._read_draft()
                self._add_to_history(cmd, "[draft read]"); return

            # Open/send draft
            if any(t in cmd_l for t in EMAIL_OPEN_TRIGGERS):
                self._open_draft()
                self._add_to_history(cmd, "[draft opened]"); return

            # Edit draft — intercept locally, use AI only to parse WHAT to change
            if any(t in cmd_l for t in EMAIL_UPDATE_TRIGGERS):
                self.sp.say("Updating the email, sir.")
                edit = _ai_parse_email_edit(
                    cmd, self.last_draft,
                    self.settings.groq_api_key,
                    self.settings.groq_model
                )
                if edit:
                    self._update_draft(edit)
                else:
                    self.sp.say("I could not understand what to change, sir. Please be more specific.")
                self._add_to_history(cmd, "[draft updated]"); return

        # ── IPL / cricket shortcuts ────────────────────────────────────────
        if any(t in cmd_l for t in REALTIME_IPL_POINTS):
            self.sp.say("Fetching IPL 2026 points table.")
            result = fetch_ipl_points_table()
            if result: self.sp.say(result)
            else:
                self.sp.say("Opening in browser."); self.wc.search("IPL 2026 points table")
            self._add_to_history(cmd, result or "opened browser"); return

        if any(t in cmd_l for t in REALTIME_CRICKET):
            self.sp.say("Pulling live cricket scores.")
            result = fetch_cricket_scores()
            self.sp.say(result); self._add_to_history(cmd, result); return

        # ── Groq API ───────────────────────────────────────────────────────
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        body    = {
            "model":       self.settings.groq_model,
            "messages":    self._build_messages(cmd),
            "temperature": 0.3,
            "max_tokens":  1400,
        }
        try:
            r = requests.post(GROQ_URL, headers=headers, json=body, timeout=25)
            if r.status_code == 200:
                raw = r.json()["choices"][0]["message"]["content"].strip()
                raw = re.sub(r"```json|```","",raw).strip()
                raw = raw.replace("{{","{").replace("}}","}")
                m   = re.search(r'\{.*\}', raw, re.DOTALL)
                if m: raw = m.group()
                speak_text = self._run(raw, cmd)
                self._add_to_history(cmd, speak_text)
                if self.is_owner: self.memory.auto_learn(cmd)
            elif r.status_code == 429:
                self.sp.say("Rate limit. One moment.")
            else:
                _safe_print(f"  [HTTP {r.status_code}] {r.text[:200]}")
                self.sp.say("AI service error.")
        except Exception as e:
            _safe_print(f"  [ERR] {e}")
            self.sp.say("Connection issue.")

    # ── Step runner ───────────────────────────────────────────────────────────
    def _run(self, raw, original_cmd=""):
        try:
            p = json.loads(raw)
        except Exception:
            msg = re.sub(r'[{}\[\]":]',' ', raw).strip()[:300]
            self.sp.say(msg); return msg

        msg = p.get("speak","")

        # Strip JSON leak from speak text
        if msg and ('"steps"' in msg or '"module"' in msg):
            m2 = re.search(r'"speak"\s*:\s*"([^"]+)"', msg)
            msg = m2.group(1) if m2 else re.sub(r'[{}":\[\]]',' ',msg).strip()[:300]

        # Guest: strip owner name
        if not self.is_owner and msg and self.owner_name:
            if self.owner_name.lower() in msg.lower():
                msg = "I cannot share personal information in guest mode."
            p["steps"] = [s for s in p.get("steps",[])
                          if s.get("module") not in ("memory","file","email","smarthome")
                          and s.get("action") not in ("run_cmd","show_info","screenshot","check_updates")]

        if msg and any(x in msg.lower() for x in DODGE_PHRASES):
            cmd_l = original_cmd.lower()
            if any(t in cmd_l for t in REALTIME_WEATHER):
                city_m = re.search(r'(?:weather|temperature|forecast)\s+(?:in|at|for)?\s*([A-Za-z ]+)', original_cmd, re.I)
                city   = city_m.group(1).strip() if city_m else "Delhi"
                w = fetch_weather(city); self.sp.say(w); return w
            if any(t in cmd_l for t in KNOWLEDGE_TRIGGERS):
                return self._ask_knowledge_only(original_cmd)

        if msg:
            self.sp.say(msg)

        if p.get("confirmation_needed") and self.is_owner:
            ans = input("[GHOST-141] Confirm? (yes/no): ").strip().lower()
            if ans not in ("yes","y"):
                self.sp.say("Cancelled, sir."); return msg

        for s in p.get("steps",[]):
            mod = s.get("module","")
            act = s.get("action","")

            if not self.is_owner and mod in ("memory","file","email","smarthome"):
                _safe_print(f"  [SECURITY] Blocked {mod}/{act} in guest mode."); continue
            if not self.is_owner and act in ("run_cmd","show_info","screenshot","check_updates","lock"):
                _safe_print(f"  [SECURITY] Blocked system/{act} in guest mode."); continue

            _safe_print(f"  [EXEC] {mod} -> {act}")
            try:
                if mod == "app":
                    if act == "open":    self._last_app_wait = self.ac.open(s.get("target",""))
                    elif act == "close": self.ac.close(s.get("target",""))

                elif mod == "web":
                    if act == "search":     self.wc.search(s.get("query",""))
                    elif act == "youtube":  self.wc.youtube(s.get("query",""))
                    elif act == "navigate": self.wc.navigate(s.get("url",""))
                    elif act == "news":     self._fetch_and_speak_news(s.get("topic","world"))

                elif mod == "system":
                    if act == "screenshot":
                        if not self.is_owner: self.sp.say("Locked in guest mode."); continue
                        self.sc.screenshot(); self.sp.say("Screenshot saved, sir.")
                    elif act == "volume":      self.sc.set_volume(s.get("level",50))
                    elif act == "brightness":  self.sc.set_brightness(s.get("level",70))
                    elif act == "lock":
                        if self.is_owner: self.sc.lock_screen()
                    elif act == "notify":      self.sc.notify(s.get("message",""))
                    elif act == "type_text":
                        time.sleep(self._last_app_wait or 2.0)
                        self._last_app_wait = 0
                        self.sc.type_text(s.get("text",""))
                    elif act == "run_cmd":
                        if not self.is_owner: self.sp.say("Locked in guest mode."); continue
                        out = self.sc.run_command(s.get("command",""))
                        _safe_print(f"  [OUTPUT] {out}")
                        if out and len(out.strip()) < 300: self.sp.say(out)
                    elif act == "show_info":
                        if self.is_owner: self._show_system_info()
                        else: self.sp.say("Locked in guest mode.")
                    elif act == "check_updates":
                        if self.is_owner: self._check_updates()
                    elif act == "remind":
                        self._set_reminder(s.get("message","Reminder."), int(s.get("seconds",60)))

                elif mod == "file":
                    if not self.is_owner: self.sp.say("Locked in guest mode."); continue
                    if act == "open":   self.fc.open(s.get("path",""))
                    elif act == "list":
                        _safe_print(self.fc.list_dir(s.get("directory","~")))
                        self.sp.say("Directory listed, sir.")
                    elif act in ("create","write"):
                        self.fc.create(s.get("path","~/Desktop/ghost_note.txt"),s.get("content",""))
                        self.sp.say("File saved, sir.")

                elif mod == "email":
                    if not self.is_owner: self.sp.say("Locked in guest mode."); continue
                    if act == "draft":
                        self.last_draft = {
                            "to":      s.get("to",""),
                            "subject": s.get("subject",""),
                            "body":    s.get("body",""),
                        }
                        self.has_draft = True
                        _safe_print(f"\n[EMAIL DRAFT]\nTo: {self.last_draft['to']}\n"
                                   f"Subject: {self.last_draft['subject']}\n"
                                   f"Body:\n{self.last_draft['body']}\n")
                        self.sp.say("Email drafted, sir. Say 'read the email', 'open the email', or ask me to change anything.")
                    elif act == "read_draft":   self._read_draft()
                    elif act == "open_draft":   self._open_draft()
                    elif act == "update_draft":  self._update_draft(s)

                elif mod == "memory":
                    if not self.is_owner: self.sp.say("Locked in guest mode."); continue
                    if act == "remember":
                        k,v = s.get("key",""),s.get("value","")
                        bad = ["insert","placeholder","value here","your","<","[","none","unknown","null"]
                        if k and v and str(v).lower() not in ("none","null","") and not any(b in str(v).lower() for b in bad):
                            self.memory.store(k,v,silent=False)
                    elif act == "recall":
                        res = self.memory.recall(s.get("key",""))
                        if res and "don't have" not in res.lower(): self.sp.say(res)
                    elif act == "forget":      self.memory.forget(s.get("key",""))
                    elif act == "forget_all":
                        self.memory.forget_all(); self.sp.say("All memory cleared, sir.")

                elif mod == "realtime":
                    if act == "weather":
                        res = fetch_weather(s.get("city","Delhi"))
                        self.sp.say(res); _safe_print(f"  [WEATHER] {res}")
                    elif act == "cricket_score":
                        res = fetch_cricket_scores()
                        self.sp.say(res); _safe_print(f"  [CRICKET] {res}")
                    elif act == "ipl_points":
                        res = fetch_ipl_points_table()
                        if res: self.sp.say(res); _safe_print(f"  [IPL] {res}")
                        else:
                            self.sp.say("Opening in browser."); self.wc.search("IPL 2026 points table")
                    elif act == "news":  self._fetch_and_speak_news(s.get("topic","world"))
                    elif act == "wikipedia":
                        res = fetch_wikipedia_summary(s.get("query",original_cmd))
                        if res: self.sp.say(res)
                        else:   self.wc.search(s.get("query",""))

                elif mod == "smarthome":
                    if not self.is_owner: self.sp.say("Locked in guest mode."); continue
                    if act == "light":
                        self.sp.say(self.smarthome.light(s.get("room","living room"),s.get("action","on"),s.get("brightness",255)))
                    elif act == "thermostat":
                        self.sp.say(self.smarthome.thermostat(s.get("temp",22),s.get("unit","C")))
                    elif act == "scene":
                        self.sp.say(self.smarthome.scene(s.get("name","")))

            except Exception as e:
                _safe_print(f"  [ERR] {mod}/{act}: {e}")
            time.sleep(0.3)

        return msg

    # ── Email helpers ──────────────────────────────────────────────────────────
    def _read_draft(self):
        if not self.has_draft:
            self.sp.say("No email draft found, sir."); return
        d = self.last_draft
        _safe_print(f"\n[EMAIL DRAFT]\nTo: {d['to'] or '(not set)'}\n"
                   f"Subject: {d['subject']}\nBody:\n{d['body']}\n")
        preview = d['body'].replace('\n',' ')[:150]
        self.sp.say(
            f"Your email, sir. "
            f"To: {d['to'] or 'not set'}. "
            f"Subject: {d['subject']}. "
            f"Body: {preview}..."
        )

    def _open_draft(self):
        if not self.has_draft:
            self.sp.say("No draft to open, sir."); return
        import webbrowser, urllib.parse
        d   = self.last_draft
        url = (f"https://mail.google.com/mail/?view=cm"
               f"&to={urllib.parse.quote(d['to'])}"
               f"&su={urllib.parse.quote(d['subject'])}"
               f"&body={urllib.parse.quote(d['body'])}")
        webbrowser.open(url)
        self.sp.say("Gmail draft opened, sir. Review and send it from there.")

    def _update_draft(self, s: dict):
        if not self.has_draft:
            self.sp.say("No draft to update, sir."); return
        field = s.get("field","")
        value = str(s.get("value",""))
        old   = str(s.get("old",""))
        new   = str(s.get("new",""))

        if field == "subject":
            self.last_draft["subject"] = value
            self.sp.say(f"Subject updated to '{value}', sir.")

        elif field == "to":
            self.last_draft["to"] = value
            self.sp.say(f"Recipient updated to {value}, sir.")

        elif field == "add_to_body":
            # Add on new line at end
            self.last_draft["body"] = self.last_draft["body"].rstrip() + f"\n{value}"
            self.sp.say(f"Added to the email, sir.")

        elif field == "remove_from_body":
            body = self.last_draft["body"]
            if value.lower() == "last line":
                lines = body.rstrip().split("\n")
                removed = lines.pop() if lines else ""
                self.last_draft["body"] = "\n".join(lines)
                self.sp.say(f"Last line removed, sir.")
            else:
                # Remove lines containing the value
                lines    = body.split("\n")
                filtered = [l for l in lines if value.lower() not in l.lower()]
                self.last_draft["body"] = "\n".join(filtered)
                self.sp.say(f"Removed from the email, sir.")

        elif field == "replace":
            body = self.last_draft["body"]
            subj = self.last_draft["subject"]
            if old and old.lower() in body.lower():
                self.last_draft["body"] = re.sub(re.escape(old), new, body, flags=re.IGNORECASE)
                self.sp.say(f"Replaced in the email body, sir.")
            elif old and old.lower() in subj.lower():
                self.last_draft["subject"] = re.sub(re.escape(old), new, subj, flags=re.IGNORECASE)
                self.sp.say(f"Replaced in the subject, sir.")
            else:
                self.sp.say(f"Could not find '{old}' in the email, sir.")

        elif field == "body":
            self.last_draft["body"] = value
            self.sp.say("Email body replaced, sir.")

        else:
            self.sp.say("Not sure what to update, sir. Try: 'add X', 'remove Y', 'change subject to Z'.")
            return

        _safe_print(f"\n[EMAIL UPDATED]\nTo: {self.last_draft['to']}\n"
                   f"Subject: {self.last_draft['subject']}\nBody:\n{self.last_draft['body']}\n")

    # ── Knowledge fallback ─────────────────────────────────────────────────────
    def _ask_knowledge_only(self, cmd):
        headers = {"Authorization":f"Bearer {self.settings.groq_api_key}","Content-Type":"application/json"}
        body    = {
            "model": self.settings.groq_model,
            "messages":[
                {"role":"system","content":(
                    f"You are Ghost-141. Current date: {now()}. "
                    "Answer directly and factually. "
                    f"{'Address user as sir.' if self.is_owner else 'User is a guest.'} "
                    "Max 3 sentences. Respond in the same language as the user."
                )},
                {"role":"user","content":cmd}
            ],
            "temperature":0.3,"max_tokens":400
        }
        try:
            r = requests.post(GROQ_URL,headers=headers,json=body,timeout=20)
            if r.status_code == 200:
                ans = r.json()["choices"][0]["message"]["content"].strip()
                self.sp.say(ans); return ans
        except Exception as e:
            _safe_print(f"  [KNOWLEDGE ERR] {e}")
        return None

    def _fetch_and_speak_news(self, topic="world"):
        self.sp.say(f"Pulling {topic} news.")
        headlines = fetch_news_headlines(topic)
        if not headlines:
            self.sp.say("Could not fetch news right now.")
            self.wc.search(f"{topic} news today"); return
        _safe_print(f"\n{'='*55}\n  TOP NEWS -- {topic.upper()}\n{'='*55}")
        for i,h in enumerate(headlines,1): _safe_print(f"  {i}. {h}")
        _safe_print(f"{'='*55}\n")
        suffix = ", sir." if self.is_owner else "."
        self.sp.say(f"Here are the top {min(len(headlines),5)} {topic} headlines{suffix}")
        time.sleep(0.4)
        for i,h in enumerate(headlines[:3],1):
            self.sp.say(f"{i}. {h[:90]+'...' if len(h)>90 else h}")
            time.sleep(0.3)

    def _show_system_info(self):
        try:
            import psutil,platform
            cpu  = psutil.cpu_percent(interval=0.5)
            ram  = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            bat  = psutil.sensors_battery()
            info = (f"System: {platform.system()} {platform.release()} | "
                    f"CPU: {cpu}% | Cores: {psutil.cpu_count()} | "
                    f"RAM: {ram.used//1024//1024}MB/{ram.total//1024//1024}MB ({ram.percent}%) | "
                    f"Disk: {disk.used//1024**3}GB/{disk.total//1024**3}GB ({disk.percent}%)")
            if bat: info += f" | Battery: {bat.percent:.0f}%"
            _safe_print(f"\n[SYSTEM INFO]\n{info}\n")
            self.sc.notify(info,"Ghost-141: System Info")
            bat_msg = f" Battery at {bat.percent:.0f}%." if bat else ""
            self.sp.say(f"CPU at {cpu}%, RAM at {ram.percent}%, disk {disk.percent}% full, sir.{bat_msg}")
        except Exception as e:
            _safe_print(f"[INFO ERR] {e}")

    def _check_updates(self):
        self.sp.say("Opening Windows Update, sir.")
        self.sc.run_command("start ms-settings:windowsupdate")

    def _set_reminder(self, message:str, seconds:int):
        def _remind():
            time.sleep(seconds)
            suffix = ", sir." if self.is_owner else "."
            self.sp.say(f"Reminder{suffix}: {message}")
            try: self.sc.notify(message,"Ghost-141 Reminder")
            except: pass
        threading.Thread(target=_remind,daemon=True).start()
        _safe_print(f"  [REMINDER] '{message}' in {seconds}s")