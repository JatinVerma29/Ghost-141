"""
memory/memory_store.py — Persistent memory for Ghost-141
"""
import json, os, re
from datetime import datetime
from collections import Counter


class MemoryStore:
    def __init__(self, settings):
        self.settings  = settings
        self.mem_dir   = os.path.expanduser("~/.ghost141")
        self.mem_file  = os.path.join(self.mem_dir, "memory.json")
        self.freq_file = os.path.join(self.mem_dir, "frequencies.json")
        os.makedirs(self.mem_dir, exist_ok=True)
        self.data      = self._load(self.mem_file)
        self.freqs     = self._load(self.freq_file)
        self.session_commands = []

    def _load(self, path):
        if os.path.exists(path):
            try:
                with open(path) as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save(self):
        with open(self.mem_file, "w") as f:
            json.dump(self.data, f, indent=2)
        with open(self.freq_file, "w") as f:
            json.dump(self.freqs, f, indent=2)

    def store(self, key: str, value: str, silent: bool = False):
        """Store a key-value pair. If key exists and value differs, ask for confirmation."""
        if not key or not value:
            return
        key = key.lower().strip()
        value = value.strip()

        existing = self.data.get(key, {}).get("value", "")

        # If same value already stored, skip silently
        if existing.lower() == value.lower():
            return

        # If updating an existing key, confirm
        if existing and not silent:
            print(f"[MEMORY] '{key}' is currently: '{existing}'")
            print(f"[MEMORY] Update to: '{value}'? (yes/no): ", end="", flush=True)
            try:
                ans = input().strip().lower()
            except Exception:
                ans = "yes"
            if ans not in ("yes", "y", ""):
                print(f"[MEMORY] Kept: {key} = {existing}")
                return

        self.data[key] = {
            "value": value,
            "saved_at": datetime.now().isoformat()
        }
        self._save()
        print(f"[MEMORY] Stored: {key} = {value}")

    def recall(self, key: str) -> str:
        key = key.lower().strip()
        entry = self.data.get(key)
        if entry:
            return entry.get("value", "")
        # Fuzzy match
        for k, v in self.data.items():
            if key in k or k in key:
                return v.get("value", "")
        return f"I don't have anything stored for '{key}'."

    def forget(self, key: str):
        k = key.lower().strip()
        deleted = []

        # Build prefix — e.g. "laptop_info" -> prefix "laptop"
        prefix = k.split("_")[0]

        # Delete ALL keys that start with this prefix
        to_delete = [dk for dk in list(self.data.keys()) if dk == k or dk.startswith(prefix + "_") or dk == prefix]
        for dk in to_delete:
            del self.data[dk]
            deleted.append(dk)

        if deleted:
            self._save()
            for d in deleted:
                print(f"[MEMORY] Forgotten: {d}")
        else:
            print(f"[MEMORY] Nothing found for: {key}")

    def forget_all(self):
        """Wipe entire memory."""
        self.data = {}
        self._save()
        print("[MEMORY] All memory cleared.")

    def auto_learn(self, command: str):
        """Extract facts from natural speech. Only runs if AI didn't already store them."""
        command = command.strip()
        cmd_lower = command.lower()
        self.session_commands.append(cmd_lower)

        # Frequency tracking
        words = re.findall(r'\b\w+\b', cmd_lower)
        for w in words:
            self.freqs[w] = self.freqs.get(w, 0) + 1

        # Only extract these specific high-confidence patterns
        # Use silent=True so auto_learn never double-prompts
        patterns = [
            (r"\bmy name is ([A-Za-z]+)\b",                  "user_name"),
            (r"\bcall me ([A-Za-z]+)\b",                     "user_name"),
            (r"\bmy email is ([^\s]+@[^\s]+)\b",             "user_email"),
            (r"\bmy browser is ([a-zA-Z]+)\b",               "browser"),
        ]

        for pattern, key in patterns:
            m = re.search(pattern, command, re.IGNORECASE)
            if m:
                value = m.group(1).strip()
                if value and len(value) > 1:
                    # silent=True: auto_learn never prompts, AI step handles confirmation
                    self.store(key, value, silent=True)

        self._save()

    def get_context_string(self) -> str:
        """Build memory context for AI prompt — clean and concise."""
        if not self.data:
            return ""
        # Group laptop specs into one readable line
        laptop_keys = ["laptop_model", "laptop_cpu", "laptop_generation",
                       "laptop_gpu", "laptop_ram", "laptop_info"]
        laptop_parts = []
        other_lines = []

        for k, v in self.data.items():
            val = v.get("value", "")
            if not val:
                continue
            if k in laptop_keys:
                if k == "laptop_info":
                    # Skip the raw blob if we have individual keys
                    individual = [kk for kk in laptop_keys[:-1] if kk in self.data]
                    if len(individual) >= 2:
                        continue
                laptop_parts.append(val)
            else:
                other_lines.append(f"- {k}: {val}")

        lines = other_lines.copy()
        if laptop_parts:
            lines.insert(0, f"- laptop: {', '.join(laptop_parts)}")

        return "\n".join(lines[:15])

    def get_frequent_commands(self, top_n: int = 5) -> list:
        counter = Counter(self.session_commands)
        return [cmd for cmd, _ in counter.most_common(top_n)]

    def all(self) -> dict:
        return self.data