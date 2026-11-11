import json
import os
from pathlib import Path

from app import secret_store

DEFAULTS = {
    "output_dir": str(Path.home() / "Downloads" / "yt-tool"),
    "model": "small",
    "markdown": True,
    "pdf": True,
    "audio_quality": "320 kbps",
    "video_quality": "Best",
    "language": "Auto",
    "subtitles": False,
    "sub_target": "Original (no translation)",
    "sub_video": "SRT file only",
    "sub_doc": False,
    "gemini_api_key": "",
    "translator": "Local (NLLB, offline)",
}


# Per-screen output folders; default to a subfolder of output_dir (keeps old configs working).
DIR_SUBFOLDERS = {"audio_dir": "audio", "video_dir": "video", "transcribe_dir": "transcripts"}


def config_path() -> Path:
    """Location of the JSON config file in %APPDATA%."""
    base = os.environ.get("APPDATA") or str(Path.home())
    return Path(base) / "yt-tool" / "config.json"


def load(path: Path | None = None) -> dict:
    """Load settings, filling in defaults for missing or unreadable values."""
    path = path or config_path()
    data = dict(DEFAULTS)
    try:
        data.update(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    if "gemini_api_key_enc" in data:
        enc = data.pop("gemini_api_key_enc")
        try:
            data["gemini_api_key"] = secret_store.unprotect(enc)
        except secret_store.SecretStoreError:
            data["gemini_api_key"] = ""
    base = Path(data["output_dir"])
    for key, sub in DIR_SUBFOLDERS.items():
        data.setdefault(key, str(base / sub))
    return data


def get_gemini_key(cfg: dict) -> str:
    """Gemini API key: the GEMINI_API_KEY environment variable wins over the saved key."""
    return (os.environ.get("GEMINI_API_KEY") or cfg.get("gemini_api_key") or "").strip()


def save(data: dict, path: Path | None = None) -> None:
    """Persist settings as JSON; the Gemini key is stored only DPAPI-encrypted."""
    path = path or config_path()
    out = dict(data)
    key = out.pop("gemini_api_key", "")
    out.pop("gemini_api_key_enc", None)
    if isinstance(key, str) and key.strip():
        out["gemini_api_key_enc"] = secret_store.protect(key.strip())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
