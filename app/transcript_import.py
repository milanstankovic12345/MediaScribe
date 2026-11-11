"""Parse existing .srt files and app-written Markdown transcripts into a Transcript."""
import re
from pathlib import Path

from app.transcriber import LANGUAGES, Segment, Transcript
from app.translator import WHISPER_TO_NLLB

TRANSCRIPT_EXTS = {".srt", ".md"}
MAX_BYTES = 20 * 1024 * 1024

_KNOWN_CODES = ({v for v in LANGUAGES.values() if v} | set(WHISPER_TO_NLLB) | {"sr-Latn", "und"})

_TIMING = re.compile(
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})[ \t]*-->[ \t]*(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})")
_TAG = re.compile(r"</?(?:i|b|u|s|font)\b[^<>]*>", re.IGNORECASE)
_BRACES = re.compile(r"\{[^{}]*\}")
_MD_SEG = re.compile(r"^\*\*\[(\d{1,4}):(\d{2})(?::(\d{2}))?\]\*\*[ \t]*(.*)$")


def _ts(h: str, m: str, s: str, ms: str) -> float:
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000


def parse_srt(text: str) -> list[Segment]:
    """Parse SRT text into one Segment per valid cue, in file order."""
    text = text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n")
    segments: list[Segment] = []
    block: list[str] = []

    def flush() -> None:
        lines, block[:] = list(block), []
        for i in range(min(2, len(lines))):
            m = _TIMING.fullmatch(lines[i].strip())
            if m:
                break
        else:
            return
        g = m.groups()
        start, end = _ts(*g[0:4]), _ts(*g[4:8])
        body = " ".join(lines[i + 1:])
        body = _BRACES.sub("", _TAG.sub("", body))
        body = " ".join(body.split())
        if body:
            segments.append(Segment(start, max(start, end), body))

    for line in text.split("\n"):
        if line.strip():
            block.append(line)
        else:
            flush()
    flush()
    return segments


def parse_markdown(text: str) -> tuple[list[Segment], str | None, str | None]:
    """Parse the app's Markdown transcript into (segments, title, language)."""
    title: str | None = None
    language: str | None = None
    items: list[list] = []  # [start, text]
    for raw in text.lstrip("﻿").splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _MD_SEG.match(line)
        if m:
            a, b, c, body = m.groups()
            start = int(a) * 3600 + int(b) * 60 + int(c) if c is not None else int(a) * 60 + int(b)
            items.append([float(start), body.strip()])
            continue
        if not items:
            if title is None and line.startswith("# "):
                title = line[2:].strip() or None
            elif language is None and line.startswith("- Language:"):
                language = line[len("- Language:"):].strip() or None
            continue
        if line.startswith("# ") and title is None:
            title = line[2:].strip() or None
            continue
        items[-1][1] = (items[-1][1] + " " + line).strip()

    items = [it for it in items if it[1]]
    segments: list[Segment] = []
    for i, (start, body) in enumerate(items):
        cap = start + max(2.0, len(body) / 15)
        end = min(items[i + 1][0], cap) if i + 1 < len(items) else cap
        segments.append(Segment(start, max(start, end), body))
    return segments, title, language


def _split_suffix(stem: str) -> tuple[str, str | None]:
    base, dot, suffix = stem.rpartition(".")
    if dot and base and suffix in _KNOWN_CODES:
        return base, suffix
    return stem, None


def _decode(data: bytes, name: str) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            return data.decode("cp1250")
        except UnicodeDecodeError:
            raise ValueError(f"Cannot decode {name}: unsupported text encoding.") from None


def load(path) -> tuple[Transcript, str]:
    """Load an .srt or app Markdown file; return (Transcript, title)."""
    p = Path(path)
    name = p.name
    if p.suffix.lower() not in TRANSCRIPT_EXTS:
        raise ValueError(f"{name}: unsupported file type (expected .srt or .md).")
    if p.stat().st_size > MAX_BYTES:
        raise ValueError(f"{name}: file is larger than 20 MB.")
    text = _decode(p.read_bytes(), name)

    base, suffix = _split_suffix(p.stem)
    file_lang = None if suffix is None else {"sr-Latn": "sr", "und": ""}.get(suffix, suffix)
    title: str | None = None
    language: str | None = None
    if p.suffix.lower() == ".md":
        segments, title, language = parse_markdown(text)
    else:
        segments = parse_srt(text)
    if not segments:
        raise ValueError(f"{name}: no transcript segments found.")
    return Transcript(segments, language or file_lang or ""), (title or base)
