import json
import os
from pathlib import Path

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
    base = Path(data["output_dir"])
    for key, sub in DIR_SUBFOLDERS.items():
        data.setdefault(key, str(base / sub))
    return data


def save(data: dict, path: Path | None = None) -> None:
    """Persist settings as JSON."""
    path = path or config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
