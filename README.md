# Voice AI Agent

A fully local, offline voice assistant for Windows laptops. Ships with an
always-on-top floating bar, continuous two-way voice, and a modular skill
system for opening apps, browsing, system control, and more. No paid APIs,
no hosted LLMs, nothing ever leaves your machine.

---

## 1. Requirements

| Item | Version / Notes |
|---|---|
| OS | Windows 10 / 11 (primary). Linux & macOS work for most skills. |
| Python | 3.9 or newer (3.10+ recommended) |
| Hardware | Microphone + speakers / headphones |
| Disk | ~100 MB (Vosk model + deps) |
| Network | Only for the one-time `pip install` and model download. Runtime is offline. |

---

## 2. One-time install

Run these in **PowerShell** from anywhere. They create the project's virtual
environment, install dependencies, and download the offline speech model.

```powershell
# 1) Move into the project
cd C:\Users\Unify\voice_ai_agent

# 2) Create an isolated virtual environment
py -3 -m venv .venv

# 3) Activate it (PowerShell)
.\.venv\Scripts\Activate.ps1

# 4) Upgrade pip
python -m pip install --upgrade pip

# 5) Install all Python dependencies
pip install -r requirements.txt

# 6) Download the offline Vosk speech model (~50 MB, runs once)
python scripts\download_model.py
```

If step 3 fails with an execution-policy error, run PowerShell **as
administrator** once and execute:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Then retry `Activate.ps1`.

### What gets installed

From `requirements.txt`:

| Package | Purpose |
|---|---|
| `vosk` | Offline speech-to-text |
| `sounddevice` | Microphone capture (no PyAudio build pain) |
| `pyttsx3` | Offline text-to-speech (Windows SAPI5) |
| `PyQt6` | Floating always-on-top UI |
| `pyautogui` | Media keys, hotkeys, typing, screenshots |
| `Pillow` | Screenshot fallback |
| `psutil` | Process helpers |
| `pycaw` (Windows) | Precise volume control |
| `comtypes`, `pywin32` (Windows) | Windows COM bridge used by pycaw / SAPI5 |
| `pytest` | Tests |

### Optional: first-run Windows setup

If TTS is silent, finalise the SAPI5 bindings once:

```powershell
python -m pywin32_postinstall -install
```

---

## 3. Run the agent

Every time you want the agent:

```powershell
cd C:\Users\Unify\voice_ai_agent
.\.venv\Scripts\Activate.ps1
python main.py
```

A small dark pill appears at the top-centre of your primary screen and says
*"Voice agent ready. How can I help?"*. It stays above every window and can
be dragged anywhere. The status orb colour indicates state:

| Colour | State |
|---|---|
| Grey | Idle |
| Green (pulsing) | Listening |
| Amber | Thinking |
| Blue (pulsing) | Speaking |
| Red | Muted |

Controls on the bar:

- **🎙 / 🔇** — toggle mute
- **✕** — close the agent

Or say **"goodbye"** / **"close agent"**.

---

## 4. What you can say

Unknown phrases are silently ignored so you can talk freely without
triggering the agent.

### Open things

| Example | What happens |
|---|---|
| *open chrome* / *launch chrome* | Starts Chrome |
| *open notepad*, *open vs code*, *open spotify*, *open excel* | Starts that app |
| *open youtube*, *open github*, *open gmail* | Opens the site in your default browser |
| *open google.com* | Opens that URL directly |
| *open documents* / *open downloads* / *open desktop* / *open c drive* | Opens the folder in Explorer |

### Search the web

| Example |
|---|
| *search for python tutorials* |
| *google latest news* |
| *look up best coffee shops in london* |
| *play on youtube lofi beats* |
| *youtube rick astley* |

### System control

| Example |
|---|
| *volume up* / *volume down* |
| *set volume to 50* |
| *mute* / *unmute* |
| *lock my computer* |
| *put my laptop to sleep* |
| *shut down my pc* (10-second delay, say *cancel shutdown* to abort) |
| *restart my laptop* |

### Window / media

| Example |
|---|
| *minimize all* / *show desktop* |
| *close window* |
| *switch window* |
| *play music* / *pause music* |
| *next track* / *previous song* |

### Utilities

| Example | What happens |
|---|---|
| *take a screenshot* | Saves to `~/Pictures/VoiceAgent/` |
| *what time is it* / *what's the date* | Speaks it back |
| *type hello world* | Types into the currently focused window (half-second grace period) |
| *say good morning* | Agent repeats the phrase aloud |

### Math

| Example | Result |
|---|---|
| *multiply 72000 and 32* | Appends `72000 * 32 = 2304000` to `~/Documents/result.txt` |
| *add seventy two thousand and thirty two* | Works with English number words too |
| *divide 144 by 12* | |
| *subtract 40 and 15* | |

### Help / control

| Example |
|---|
| *help* / *what can you do* — lists capabilities |
| *goodbye* / *exit* / *close agent* — quits |

---

## 5. Configuration

All knobs live in [`config/settings.py`](config/settings.py). See
[`.env.example`](.env.example) for a compact reference of the same values in
dotenv form.

Common things you may want to tweak:

```python
# config/settings.py

TTS_RATE = 185            # words per minute
TTS_VOICE_HINT = "Zira"   # partial match against voice names (Windows: Zira/David/Mark)

REQUIRE_WAKE_WORD = False # True = only act on "hey replica ..." style commands
WAKE_WORDS = ("replica", "hey replica", "jarvis", "friday", "agent", "assistant")

UI_OPACITY = 0.95         # 1.0 = fully opaque, 0.8 = fairly see-through
```

### Add your own apps / sites

```python
# config/settings.py

APP_COMMANDS["figma"] = [r"%LOCALAPPDATA%\Figma\Figma.exe"]
APP_COMMANDS["obsidian"] = [r"%LOCALAPPDATA%\Obsidian\Obsidian.exe"]

WEBSITE_SHORTCUTS["hn"] = "https://news.ycombinator.com"
WEBSITE_SHORTCUTS["jira"] = "https://yourcompany.atlassian.net"

FOLDER_PATHS["projects"] = Path(r"D:\Projects")
```

Restart the agent — *"open figma"*, *"open hn"*, *"open projects"* all work.

### Strict wake-word mode

```python
REQUIRE_WAKE_WORD = True
```

Then the agent ignores every utterance that does not start with one of the
`WAKE_WORDS`. Useful on a shared/noisy desk.

---

## 6. Project layout

```
voice_ai_agent/
├── main.py                      # Qt launcher + wiring
├── requirements.txt
├── README.md                    # this file
├── .env.example                 # reference of all tunables
├── .gitignore
│
├── config/
│   └── settings.py              # ALL configuration lives here
│
├── modules/
│   ├── stt/vosk_stt.py          # offline speech-to-text
│   ├── nlp/intent_recognizer.py # rule-based intent matcher
│   ├── planner/planner.py       # intent -> task
│   ├── executor/
│   │   ├── executor.py          # dispatcher
│   │   └── skills/              # every capability is one file
│   │       ├── apps.py          # launch applications
│   │       ├── files.py         # folders, paths
│   │       ├── web.py           # URLs, Google/YouTube search
│   │       ├── system.py        # volume, lock, sleep, shutdown
│   │       ├── media.py         # play / pause / next / prev
│   │       ├── window.py        # minimize all, close, switch
│   │       └── utility.py       # time, date, screenshot, type, math
│   ├── memory/history.py        # JSONL conversation log
│   ├── tts/tts_engine.py        # offline speech output
│   └── ui/
│       ├── floating_widget.py   # the always-on-top pill
│       └── agent_controller.py  # QThread worker running the loop
│
├── scripts/
│   └── download_model.py        # one-time Vosk model downloader
│
├── tests/
│   └── test_intent.py           # parametrised pytest coverage
│
├── models/                      # Vosk model lives here after download
├── data/                        # history.jsonl
└── logs/                        # agent.log
```

### Output locations on disk

| Item | Path |
|---|---|
| Math results | `C:\Users\<you>\Documents\result.txt` |
| Screenshots | `C:\Users\<you>\Pictures\VoiceAgent\` |
| Conversation log | `voice_ai_agent\data\history.jsonl` |
| Runtime log | `voice_ai_agent\logs\agent.log` |

---

## 7. Adding a new skill

1. Drop a function into `modules/executor/skills/<file>.py`:

   ```python
   # modules/executor/skills/utility.py
   def tell_joke() -> dict:
       return {"ok": True, "speak": "Why did the developer go broke? "
                                    "Because he used up all his cache."}
   ```

2. Register it in `modules/executor/executor.py`:

   ```python
   "joke": utility.tell_joke,
   ```

3. Teach the NLP to recognise it in `modules/nlp/intent_recognizer.py`:

   ```python
   (r"\b(tell\s+(?:me\s+)?a?\s*joke)\b", "joke"),
   ```

4. Restart → *"tell me a joke"* works.

---

## 8. Tests

```powershell
pytest tests -v
```

Covers ~25 intent phrasings. Run this after editing
`intent_recognizer.py` to catch regressions.

---

## 9. Troubleshooting

| Symptom | Fix |
|---|---|
| `Vosk model not found` on first run | `python scripts\download_model.py` |
| Agent hears nothing | Check Windows *Sound settings → Input* and select the correct microphone. |
| TTS is silent | `pip install --upgrade pywin32` then `python -m pywin32_postinstall -install` |
| Floating bar doesn't appear | `pip install --upgrade PyQt6` |
| Volume commands don't do anything | `pip install pycaw comtypes` (auto-installed on Windows via `requirements.txt`) |
| An app doesn't open | Add its full path to `APP_COMMANDS` in `config/settings.py` |
| High CPU while idle | Raise `AUDIO_BLOCKSIZE` to `16000` in `settings.py` |
| Agent hears itself during TTS | Already handled — mic stream is muted while speaking. If you still see it, lower `TTS_VOLUME` or use headphones. |
| `Set-ExecutionPolicy` blocked | Run PowerShell as admin once: `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` |

Runtime issues are written to `logs/agent.log` — always check there first.

---

## 10. Uninstall

```powershell
# Just delete the folder. Nothing is installed system-wide.
Remove-Item -Recurse -Force C:\Users\Unify\voice_ai_agent
```

`~/Documents/result.txt` and `~/Pictures/VoiceAgent/` are left in place so
your data is preserved.
