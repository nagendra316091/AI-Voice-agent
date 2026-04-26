"""Central runtime configuration for the Voice AI Agent.

All paths, hotkey lists, and app/website catalogues live here so individual
modules stay clean. Tweak this file to extend what the agent can do without
touching code elsewhere.
"""
from __future__ import annotations

from pathlib import Path

BASE_DIR: Path = Path(__file__).resolve().parent.parent
MODELS_DIR: Path = BASE_DIR / "models"
DATA_DIR: Path = BASE_DIR / "data"
LOGS_DIR: Path = BASE_DIR / "logs"

# ---- STT -----------------------------------------------------------------
# Backend: "whisper" (faster-whisper, far more accurate) or "vosk" (light).
STT_BACKEND: str = "whisper"

# Whisper config (used when STT_BACKEND == "whisper").
# Sizes: tiny.en (~75MB), base.en (~145MB), small.en (~485MB), medium.en (~1.5GB).
# base.en is the sweet spot for an offline voice agent on CPU.
WHISPER_MODEL_SIZE: str = "base.en"
WHISPER_COMPUTE_TYPE: str = "int8"   # int8 = CPU friendly; "float16" if GPU.

# Vosk config (used when STT_BACKEND == "vosk").
VOSK_MODEL_NAME: str = "vosk-model-small-en-us-0.15"
VOSK_MODEL_PATH: Path = MODELS_DIR / VOSK_MODEL_NAME

SAMPLE_RATE: int = 16000
AUDIO_BLOCKSIZE: int = 8000

# ---- LLM intent fallback (Groq, free tier) -------------------------------
# Set GROQ_API_KEY in your environment (or .env) to enable smart intent
# parsing for utterances the regex doesn't catch. Free tier: 14k req/day.
# Get a key at: https://console.groq.com/keys
LLM_INTENT_ENABLED: bool = True
LLM_MODEL: str = "llama-3.1-8b-instant"

# ---- TTS (pyttsx3) -------------------------------------------------------
TTS_RATE: int = 185
TTS_VOLUME: float = 1.0
TTS_VOICE_HINT: str | None = None  # e.g. "Zira", "David" on Windows

# ---- Wake word / listening behaviour -------------------------------------
# Always-on by default. Set REQUIRE_WAKE_WORD=True for strict mode where the
# agent only acts when the utterance starts with one of WAKE_WORDS.
WAKE_WORDS: tuple[str, ...] = (
    "replica", "hey replica", "hello replica",
    "jarvis", "friday", "agent", "assistant",
)
REQUIRE_WAKE_WORD: bool = False

# ---- UI ------------------------------------------------------------------
UI_ALWAYS_ON_TOP: bool = True
UI_OPACITY: float = 0.95

# ---- Output --------------------------------------------------------------
DOCUMENTS_DIR: Path = Path.home() / "Documents"
RESULT_FILE: Path = DOCUMENTS_DIR / "result.txt"
HISTORY_FILE: Path = DATA_DIR / "history.jsonl"
SCREENSHOT_DIR: Path = Path.home() / "Pictures" / "VoiceAgent"

# ---- Application catalogue -----------------------------------------------
# Maps spoken name -> argv list. Unknown names fall back to the Windows
# `start` shell built-in, which resolves App Paths (works for most apps).
# Use ``%USERNAME%`` / ``%PROGRAMFILES%`` etc. — they are expanded at launch.
APP_COMMANDS: dict[str, list[str]] = {
    "calculator":           ["calc.exe"],
    "calc":                 ["calc.exe"],
    "notepad":              ["notepad.exe"],
    "paint":                ["mspaint.exe"],
    "snipping tool":        ["snippingtool.exe"],
    "explorer":             ["explorer.exe"],
    "file explorer":        ["explorer.exe"],
    "files":                ["explorer.exe"],
    "command prompt":       ["cmd.exe"],
    "cmd":                  ["cmd.exe"],
    "powershell":           ["powershell.exe"],
    "terminal":             ["wt.exe"],
    "windows terminal":     ["wt.exe"],
    "task manager":         ["taskmgr.exe"],
    "settings":             ["cmd", "/c", "start", "ms-settings:"],
    "control panel":        ["control.exe"],
    "chrome":               [r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"],
    "google chrome":        [r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"],
    "edge":                 [r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe"],
    "microsoft edge":       [r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe"],
    "firefox":              [r"%PROGRAMFILES%\Mozilla Firefox\firefox.exe"],
    "brave":                [r"%PROGRAMFILES%\BraveSoftware\Brave-Browser\Application\brave.exe"],
    "vs code":              [r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"],
    "visual studio code":   [r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"],
    "code":                 [r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"],
    "spotify":              ["spotify"],
    "word":                 ["winword.exe"],
    "microsoft word":       ["winword.exe"],
    "excel":                ["excel.exe"],
    "microsoft excel":      ["excel.exe"],
    "powerpoint":           ["powerpnt.exe"],
    "outlook":              ["outlook.exe"],
    "vlc":                  [r"%PROGRAMFILES%\VideoLAN\VLC\vlc.exe"],
    "discord":              [r"%LOCALAPPDATA%\Discord\Update.exe", "--processStart", "Discord.exe"],
    "whatsapp":             ["cmd", "/c", "start", "whatsapp://"],
}

# ---- Folder shortcuts ----------------------------------------------------
FOLDER_PATHS: dict[str, Path] = {
    "documents":   Path.home() / "Documents",
    "downloads":   Path.home() / "Downloads",
    "desktop":     Path.home() / "Desktop",
    "pictures":    Path.home() / "Pictures",
    "music":       Path.home() / "Music",
    "videos":      Path.home() / "Videos",
    "home":        Path.home(),
    "user":        Path.home(),
    "this pc":     Path("C:\\"),
    "c drive":     Path("C:\\"),
    "c":           Path("C:\\"),
    "recycle bin": Path("shell:RecycleBinFolder"),  # handled via explorer
}

# ---- Website catalogue ---------------------------------------------------
WEBSITE_SHORTCUTS: dict[str, str] = {
    "youtube":         "https://youtube.com",
    "google":          "https://google.com",
    "gmail":           "https://mail.google.com",
    "github":          "https://github.com",
    "twitter":         "https://twitter.com",
    "x":               "https://twitter.com",
    "reddit":          "https://reddit.com",
    "stack overflow":  "https://stackoverflow.com",
    "stackoverflow":   "https://stackoverflow.com",
    "chatgpt":         "https://chat.openai.com",
    "claude":          "https://claude.ai",
    "linkedin":        "https://linkedin.com",
    "facebook":        "https://facebook.com",
    "instagram":       "https://instagram.com",
    "netflix":         "https://netflix.com",
    "amazon":          "https://amazon.com",
    "whatsapp web":    "https://web.whatsapp.com",
    "news":            "https://news.google.com",
    "maps":            "https://maps.google.com",
    "translate":       "https://translate.google.com",
    "drive":           "https://drive.google.com",
    "google drive":    "https://drive.google.com",
}
