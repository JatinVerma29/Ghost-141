"""
modules/app_controller.py — Ghost-141 App Controller v2
Correct Windows shell commands for all major apps.
"""

import subprocess
import platform
import psutil
import time


class AppController:
    def __init__(self, settings):
        self.settings = settings
        self.os = platform.system()

        self.APP_MAP = {
            # ── Browsers ─────────────────────────────────────────────────────
            "chrome":        {"Linux": "google-chrome",           "Darwin": "open -a 'Google Chrome'",        "Windows": "start chrome"},
            "firefox":       {"Linux": "firefox",                 "Darwin": "open -a Firefox",                "Windows": "start firefox"},
            "edge":          {"Linux": "microsoft-edge",          "Darwin": "open -a 'Microsoft Edge'",       "Windows": "start msedge"},
            "brave":         {"Linux": "brave-browser",           "Darwin": "open -a Brave",                  "Windows": "start brave"},
            "opera":         {"Linux": "opera",                   "Darwin": "open -a Opera",                  "Windows": "start opera"},

            # ── Dev tools ────────────────────────────────────────────────────
            "vscode":        {"Linux": "code",                    "Darwin": "open -a 'Visual Studio Code'",   "Windows": "start code"},
            "vs code":       {"Linux": "code",                    "Darwin": "open -a 'Visual Studio Code'",   "Windows": "start code"},

            # ── Terminals ────────────────────────────────────────────────────
            "terminal":      {"Linux": "gnome-terminal",          "Darwin": "open -a Terminal",               "Windows": "start wt"},
            "cmd":           {"Linux": "gnome-terminal",          "Darwin": "open -a Terminal",               "Windows": "start cmd"},
            "powershell":    {"Linux": "gnome-terminal",          "Darwin": "open -a Terminal",               "Windows": "start powershell"},

            # ── Text / Office ────────────────────────────────────────────────
            "notepad":       {"Linux": "gedit",                   "Darwin": "open -a TextEdit",               "Windows": "notepad"},
            "wordpad":       {"Linux": "gedit",                   "Darwin": "open -a TextEdit",               "Windows": "start wordpad"},
            "word":          {"Linux": "libreoffice --writer",    "Darwin": "open -a 'Microsoft Word'",       "Windows": "start winword"},
            "excel":         {"Linux": "libreoffice --calc",      "Darwin": "open -a 'Microsoft Excel'",      "Windows": "start excel"},
            "powerpoint":    {"Linux": "libreoffice --impress",   "Darwin": "open -a 'Microsoft PowerPoint'", "Windows": "start powerpnt"},
            "onenote":       {"Linux": "",                        "Darwin": "open -a 'Microsoft OneNote'",    "Windows": "start onenote"},
            "outlook":       {"Linux": "",                        "Darwin": "open -a 'Microsoft Outlook'",    "Windows": "start outlook"},

            # ── File managers ─────────────────────────────────────────────────
            "files":         {"Linux": "nautilus",                "Darwin": "open -a Finder",                 "Windows": "explorer"},
            "explorer":      {"Linux": "nautilus",                "Darwin": "open -a Finder",                 "Windows": "explorer"},

            # ── System tools ──────────────────────────────────────────────────
            "calculator":    {"Linux": "gnome-calculator",        "Darwin": "open -a Calculator",             "Windows": "calc"},
            "paint":         {"Linux": "gimp",                    "Darwin": "open -a Preview",                "Windows": "mspaint"},
            "settings":      {"Linux": "gnome-control-center",    "Darwin": "open -a 'System Preferences'",   "Windows": "start ms-settings:"},
            "task manager":  {"Linux": "gnome-system-monitor",    "Darwin": "open -a 'Activity Monitor'",     "Windows": "taskmgr"},
            "snipping tool": {"Linux": "",                        "Darwin": "",                               "Windows": "snippingtool"},
            "camera":        {"Linux": "cheese",                  "Darwin": "",                               "Windows": "start microsoft.windows.camera:"},
            "clock":         {"Linux": "",                        "Darwin": "",                               "Windows": "start ms-clock:"},
            "weather":       {"Linux": "",                        "Darwin": "",                               "Windows": "start bingweather:"},
            "maps":          {"Linux": "",                        "Darwin": "",                               "Windows": "start bingmaps:"},
            "photos":        {"Linux": "eog",                     "Darwin": "open -a Photos",                 "Windows": "start ms-photos:"},
            "store":         {"Linux": "",                        "Darwin": "",                               "Windows": "start ms-windows-store:"},
            "defender":      {"Linux": "",                        "Darwin": "",                               "Windows": "start windowsdefender:"},

            # ── Media ─────────────────────────────────────────────────────────
            "spotify":       {"Linux": "spotify",                 "Darwin": "open -a Spotify",                "Windows": "start spotify"},
            "vlc":           {"Linux": "vlc",                     "Darwin": "open -a VLC",                    "Windows": "start vlc"},
            "media player":  {"Linux": "vlc",                     "Darwin": "open -a 'QuickTime Player'",     "Windows": "start wmplayer"},

            # ── Communication ─────────────────────────────────────────────────
            "whatsapp":      {
                "Linux":   "whatsapp-desktop",
                "Darwin":  "open -a WhatsApp",
                "Windows": r'explorer shell:AppsFolder\5319275A.WhatsApp_cv1g1gvanyjgm!WhatsApp'
            },
            "telegram":      {
                "Linux":   "telegram-desktop",
                "Darwin":  "open -a Telegram",
                "Windows": r'explorer shell:AppsFolder\TelegramMessengerLLP.TelegramDesktop_t4vj0pshhgkwm!TelegramDesktop'
            },
            "discord":       {"Linux": "discord",                 "Darwin": "open -a Discord",                "Windows": "start discord"},
            "zoom":          {"Linux": "zoom",                    "Darwin": "open -a zoom.us",                "Windows": "start zoom"},
            "slack":         {"Linux": "slack",                   "Darwin": "open -a Slack",                  "Windows": "start slack"},
            "teams":         {"Linux": "teams",                   "Darwin": "open -a 'Microsoft Teams'",      "Windows": "start ms-teams:"},
            "skype":         {"Linux": "skype",                   "Darwin": "open -a Skype",                  "Windows": "start skype"},

            # ── Gaming ────────────────────────────────────────────────────────
            "xbox":          {
                "Linux":   "",
                "Darwin":  "",
                "Windows": r'explorer shell:AppsFolder\Microsoft.XboxApp_8wekyb3d8bbwe!Microsoft.XboxApp'
            },
            "xbox game bar": {"Linux": "",                        "Darwin": "",                               "Windows": "start ms-gamebar:"},
            "steam":         {"Linux": "steam",                   "Darwin": "open -a Steam",                  "Windows": "start steam"},

            # ── Web shortcuts ─────────────────────────────────────────────────
            "youtube":       {
                "Linux":   "xdg-open https://www.youtube.com",
                "Darwin":  "open https://www.youtube.com",
                "Windows": "start https://www.youtube.com"
            },
            "gmail":         {
                "Linux":   "xdg-open https://mail.google.com",
                "Darwin":  "open https://mail.google.com",
                "Windows": "start https://mail.google.com"
            },
            "google":        {
                "Linux":   "xdg-open https://www.google.com",
                "Darwin":  "open https://www.google.com",
                "Windows": "start https://www.google.com"
            },
        }

        self.OPEN_WAIT = {
            "word": 4.0, "excel": 4.0, "powerpoint": 4.0,
            "notepad": 1.5, "wordpad": 2.0,
            "vscode": 3.0, "vs code": 3.0,
            "chrome": 2.5, "edge": 2.5, "firefox": 2.5, "brave": 2.5,
            "terminal": 1.5, "cmd": 1.5, "powershell": 1.5,
            "whatsapp": 4.0, "telegram": 4.0, "discord": 4.0,
            "zoom": 4.0, "slack": 3.0, "teams": 4.0,
            "spotify": 3.0, "steam": 5.0,
        }

    def open(self, app_name: str) -> float:
        name  = app_name.lower().strip()
        entry = self.APP_MAP.get(name)

        if entry:
            cmd = entry.get(self.os, "")
            if not cmd:
                print(f"[APP] {app_name} not supported on {self.os}")
                return 0.0
        else:
            cmd = name  # Fallback: try as raw command

        try:
            subprocess.Popen(cmd, shell=True)
            print(f"[APP] Opened: {app_name}")
        except Exception as e:
            print(f"[APP] Failed to open {app_name}: {e}")

        return self.OPEN_WAIT.get(name, 2.0)

    def close(self, app_name: str):
        name = app_name.lower().strip()
        PROC_MAP = {
            "chrome": "chrome", "firefox": "firefox", "edge": "msedge",
            "brave": "brave", "word": "winword", "excel": "excel",
            "powerpoint": "powerpnt", "notepad": "notepad", "wordpad": "wordpad",
            "vscode": "code", "vs code": "code", "spotify": "spotify",
            "vlc": "vlc", "zoom": "zoom", "slack": "slack",
            "discord": "discord", "telegram": "telegram", "whatsapp": "whatsapp",
            "teams": "teams", "skype": "skype", "steam": "steam",
        }
        target = PROC_MAP.get(name, name)
        killed = False
        for proc in psutil.process_iter(["name"]):
            try:
                if target in proc.info["name"].lower():
                    proc.terminate()
                    killed = True
            except Exception:
                pass
        print(f"[APP] {'Closed' if killed else 'Not found'}: {app_name}")

    def focus(self, app_name: str):
        if self.os == "Linux":
            subprocess.Popen(["wmctrl", "-a", app_name])
        elif self.os == "Darwin":
            subprocess.Popen(["osascript", "-e", f'tell app "{app_name}" to activate'])

    def list_open(self) -> list:
        return list({p.name() for p in psutil.process_iter(["name"])
                     if p.name() and not p.name().startswith("[")})