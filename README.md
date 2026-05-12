# 👻 GHOST-141 — Autonomous AI Laptop Controller

```
  ██████  ██   ██  ██████  ███████ ████████       ██  ██  ██
 ██       ██   ██ ██    ██ ██         ██          ███████ ███
 ██   ███ ███████ ██    ██ ███████    ██    ████  ██   ██  ██
 ██    ██ ██   ██ ██    ██      ██    ██           ██  ██  ██
  ██████  ██   ██  ██████  ███████    ██            ██ ██  ██
```

**Ghost-141** is an advanced AI-powered voice assistant that fully automates your laptop.
Say `"Ghost-141"` as the wake word, speak your command, and watch it execute.

---

## Features

| Category | Capabilities |
|---|---|
| **Voice** | Wake word detection, real-time STT, natural TTS output |
| **Apps** | Open, close, focus any application |
| **Web** | Search, browse, YouTube, email, news, weather |
| **Files** | Create, read, move, delete, open files and folders |
| **System** | Screenshot, volume, brightness, hotkeys, typing, clicking |
| **Terminal** | Execute any shell command via voice |
| **Memory** | Learns your preferences and patterns automatically |
| **Automation** | Multi-step workflows (morning routine, etc.) |

---

## Quick Start

### 1. Install dependencies

```bash
# Linux: Install PortAudio first
sudo apt install portaudio19-dev python3-dev

# macOS
brew install portaudio

# Install Python packages
pip install -r requirements.txt
```

### 2. Set your API key

```bash
# Option A: environment variable
export ANTHROPIC_API_KEY="sk-ant-..."

# Option B: create ~/.ghost141/.env
mkdir -p ~/.ghost141
echo 'ANTHROPIC_API_KEY=sk-ant-...' > ~/.ghost141/.env
```

### 3. Run Ghost-141

```bash
python main.py
```

---

## Voice Commands (Examples)

```
"Ghost-141, open Chrome and search for the latest news"
"Ghost-141, play lo-fi music on YouTube"
"Ghost-141, take a screenshot and save it to my desktop"
"Ghost-141, open the Downloads folder"
"Ghost-141, set volume to 50 percent"
"Ghost-141, run the morning routine"
"Ghost-141, type Hello World in the current window"
"Ghost-141, remember I prefer dark mode"
"Ghost-141, lock the screen"
"Ghost-141, what's the weather in Mumbai?"
```

---

## Project Structure

```
ghost141/
├── main.py                    # Entry point
├── requirements.txt
├── core/
│   ├── brain.py               # AI command interpreter (Anthropic API)
│   ├── voice_engine.py        # Wake word + STT (SpeechRecognition)
│   └── speaker.py             # TTS output (pyttsx3)
├── modules/
│   ├── system_controller.py   # OS control: mouse, keyboard, screenshot
│   ├── app_controller.py      # Application management
│   ├── web_controller.py      # Web browsing and data extraction
│   └── file_controller.py     # File system operations
├── memory/
│   └── memory_store.py        # Persistent JSON-based memory
├── config/
│   └── settings.py            # All configuration options
└── logs/                      # Session logs (auto-created)
```

---

## Memory System

Ghost-141 automatically learns your patterns:
- Detects preferences from commands ("I prefer...", "always use...")
- Tracks command frequency
- Stores data in `~/.ghost141/memory.json`
- Injects context into every AI request

---

## Customizing

### Add a new app shortcut
Edit `modules/app_controller.py → APP_MAP`:
```python
"myapp": {"Linux": "myapp", "Darwin": "open -a MyApp", "Windows": "start myapp"},
```

### Add an automation routine
In `main.py` or directly via voice:
```
"Ghost-141, always open VS Code and terminal when I say start work mode"
```

### Change voice / speed
Edit `config/settings.py`:
```python
voice_rate = 180    # Faster speech
voice_volume = 0.8
```

---

## Safety

- Destructive actions (delete files, shutdown) require **confirmation** by default
- `pyautogui.FAILSAFE = True` — move mouse to top-left corner to abort automation
- API key is **never** hardcoded — always loaded from environment

---

## Troubleshooting

| Issue | Fix |
|---|---|
| No microphone detected | Install `portaudio`: `sudo apt install portaudio19-dev` |
| STT not working | Ensure internet connection (Google STT requires it) |
| App not opening | Add it to `APP_MAP` in `app_controller.py` |
| TTS silent | Check `pyttsx3` is installed; speaker volume is up |
| API errors | Verify `ANTHROPIC_API_KEY` is set correctly |

---

## License

MIT — Built with ❤️ and Anthropic Claude
