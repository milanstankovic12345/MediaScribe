"""Pure helpers that turn timed Segments into subtitle cues and an SRT file."""
import math
import shutil
import subprocess
import sys
import tempfile
from collections import deque
from pathlib import Path
from typing import Callable

from app.transcriber import Segment

LINE_CHARS = 42


def fmt_srt_time(seconds: float) -> str:
    """Format seconds as HH:MM:SS,mmm."""
    ms = int(round(max(0.0, seconds) * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _split_point(text: str, limit: int, max_chars: int) -> int:
    """Index at which to cut `text` (longer than `limit`); never mid-word
    unless a single word exceeds `max_chars`."""
    window = text[:limit + 1]
    min_pos = max(1, limit // 3)
    for chars in (".!?", ",;:"):
        for i in range(min(limit, len(window)) - 1, -1, -1):
            if window[i] in chars and (i + 1 >= len(text) or text[i + 1] == " "):
                if i + 1 >= min_pos:
                    return i + 1
                break
    early = window.rfind(" ")
    if early >= min_pos:
        return early
    late = text.find(" ", limit)
    if late == -1:
        late = len(text)
    if late <= max_chars:
        return late
    if early >= 1:
        return early
    return max_chars


def _chunks(text: str, limit: int, max_chars: int) -> list[str]:
    text = " ".join(text.split())
    out: list[str] = []
    while len(text) > limit:
        cut = _split_point(text, limit, max_chars)
        out.append(text[:cut].strip())
        text = text[cut:].strip()
    if text:
        out.append(text)
    return [c for c in out if c]


def _wrap(text: str, width: int = LINE_CHARS) -> str:
    """Wrap into at most 2 balanced lines."""
    if len(text) <= width:
        return text
    spaces = [i for i, c in enumerate(text) if c == " "]
    if not spaces:
        cut = width if len(text) <= 2 * width else len(text) // 2
        return text[:cut] + "\n" + text[cut:]
    i = min(spaces, key=lambda p: max(p, len(text) - p - 1))
    return text[:i].strip() + "\n" + text[i:].strip()


def to_cues(segments: list[Segment], max_chars: int = 84,
            max_dur: float = 6.0) -> list[Segment]:
    """Split segments into readable cues (<= max_chars, <= max_dur, 2 lines)."""
    cues: list[Segment] = []
    for seg in segments:
        text = " ".join(seg.text.split())
        if not text:
            continue
        seg_end = max(seg.start, seg.end)
        dur = seg_end - seg.start
        limit = max_chars
        if dur > max_dur:
            pieces = math.ceil(dur / max_dur)
            limit = min(limit, max(1, math.ceil(len(text) / pieces)))
        parts = _chunks(text, limit, max_chars)
        total = sum(len(p) for p in parts)
        done = 0
        for idx, part in enumerate(parts):
            start = seg.start + dur * done / total
            done += len(part)
            end = seg_end if idx == len(parts) - 1 else seg.start + dur * done / total
            end = min(end, start + max_dur)
            cues.append(Segment(start, end, _wrap(part)))
    return cues


def to_srt(cues: list[Segment]) -> str:
    blocks = [f"{i}\n{fmt_srt_time(c.start)} --> {fmt_srt_time(c.end)}\n{c.text}\n"
              for i, c in enumerate(cues, 1)]
    return "\n".join(blocks)


def write_srt(cues: list[Segment], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_srt(cues), encoding="utf-8-sig")
    return path


_ISO3 = {
    "en": "eng", "sr": "srp", "hr": "hrv", "bs": "bos", "de": "deu", "fr": "fra",
    "es": "spa", "it": "ita", "pt": "por", "ru": "rus", "pl": "pol", "cs": "ces",
    "sk": "slk", "sl": "slv", "mk": "mkd", "bg": "bul", "uk": "ukr", "nl": "nld",
    "sv": "swe", "no": "nor", "da": "dan", "fi": "fin", "el": "ell", "tr": "tur",
    "hu": "hun", "ro": "ron", "ja": "jpn", "ko": "kor", "zh": "zho", "ar": "ara",
    "hi": "hin", "he": "heb",
}


def iso639_2(code: str) -> str:
    """Map a 2-letter Whisper code to ISO 639-2; unknown codes become 'und'."""
    code = (code or "").strip().lower()
    if len(code) == 3 and code.isalpha():
        return code
    return _ISO3.get(code, "und")


def _flags() -> int:
    return subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def _tail(text: str, n: int = 5) -> str:
    return "\n".join(text.strip().splitlines()[-n:])


def embed(video: Path, srt: Path, dst: Path, lang_iso: str,
          log: Callable[[str], None] | None = None) -> Path:
    """Add `srt` as a soft subtitle track without re-encoding."""
    dst = Path(dst)
    codec = "srt" if dst.suffix.lower() == ".mkv" else "mov_text"
    cmd = ["ffmpeg", "-y", "-i", str(video), "-i", str(srt), "-map", "0:v", "-map", "0:a?",
           "-map", "1:0", "-c", "copy", "-c:s", codec,
           "-metadata:s:s:0", f"language={iso639_2(lang_iso)}", str(dst)]
    if log:
        log("Embedding subtitle track...")
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", creationflags=_flags())
    except OSError as e:
        raise RuntimeError(f"ffmpeg could not be started: {e}") from e
    if r.returncode != 0:
        raise RuntimeError("ffmpeg failed:\n" + _tail(r.stderr or ""))
    return dst


def burn(video: Path, srt: Path, dst: Path, duration: float | None = None,
         cb: Callable[[float], None] | None = None,
         log: Callable[[str], None] | None = None) -> Path:
    """Hard-code `srt` into the video (re-encodes video, copies audio)."""
    dst = Path(dst).resolve()
    video = Path(video).resolve()
    if log:
        log("Burning subtitles into video...")
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copyfile(srt, Path(tmp) / "subs.srt")
        cmd = ["ffmpeg", "-y", "-i", str(video), "-vf", "subtitles=subs.srt",
               "-c:v", "libx264", "-crf", "20", "-preset", "veryfast",
               "-c:a", "copy", "-progress", "pipe:1", "-nostats", str(dst)]
        try:
            proc = subprocess.Popen(cmd, cwd=tmp, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True,
                                    encoding="utf-8", errors="replace",
                                    creationflags=_flags())
        except OSError as e:
            raise RuntimeError(f"ffmpeg could not be started: {e}") from e
        tail: deque[str] = deque(maxlen=5)
        try:
            for line in proc.stdout:
                line = line.strip()
                if line.startswith("out_time_ms="):
                    try:
                        t = int(line.split("=", 1)[1]) / 1_000_000
                    except ValueError:
                        continue
                    if cb and duration:
                        cb(max(0.0, min(t / duration, 1.0)))
                elif line and "=" not in line.split(" ", 1)[0]:
                    tail.append(line)
            code = proc.wait()
        except BaseException:
            try:
                proc.kill()
                proc.wait()
            except Exception:
                pass
            raise
    if code != 0:
        raise RuntimeError("ffmpeg failed:\n" + "\n".join(tail))
    if cb:
        cb(1.0)
    return dst
