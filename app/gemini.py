"""Optional online subtitle translation with the Gemini REST API (standard library only).

Gemini receives the transcript text (never the video), in ordered chunks with a few preceding
lines as read-only context. Timestamps stay with Whisper. The API key is sent only in the
`x-goog-api-key` header and is never part of a URL, log line or exception message.
"""
import json
import re
import time
import urllib.error
import urllib.request
from typing import Callable

from app.transcriber import Segment

API_KEY_URL = "https://aistudio.google.com/apikey"
# Free-tier model per https://ai.google.dev/gemini-api/docs/pricing (gemini-3.5-flash-lite,
# "optimized for ... translation"; gemini-2.5-flash is deprecated there). Override: settings `gemini_model`.
MODEL = "gemini-3.5-flash-lite"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
TIMEOUT = 60
CHUNK_CHARS = 6000
CONTEXT_LINES = 5
BACKOFF = (5, 15, 30)  # seconds before retry 2, 3 (and a spare) after HTTP 429
MAX_TRIES = 3

INVALID_KEY_MSG = "Gemini API key invalid or not allowed"
NETWORK_MSG = "Cannot reach Gemini (check internet connection)"
RATE_MSG = "Gemini rate limit reached (try again later)"

# Labels whose Gemini language name differs from the UI label
_LANG_NAMES = {"Serbian (Latin)": "Serbian written in Latin script",
               "Serbian (Cyrillic)": "Serbian written in Cyrillic script"}

_SCHEMA = {"type": "ARRAY", "items": {"type": "OBJECT",
           "properties": {"i": {"type": "INTEGER"}, "t": {"type": "STRING"}},
           "required": ["i", "t"]}}


class GeminiError(Exception):
    """kind: invalid_key | rate_limited | network | other. The message never contains the key."""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse every redirect so the API key header never follows a Location to another host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_opener = urllib.request.build_opener(_NoRedirect)
_MODEL_RE = re.compile(r"[A-Za-z0-9.\-]+")


def _open(req, timeout=None):
    return _opener.open(req, timeout=timeout)


def _retry_delay(body: bytes) -> float | None:
    try:
        for d in json.loads(body)["error"].get("details", []):
            m = re.fullmatch(r"(\d+(?:\.\d+)?)s", str(d.get("retryDelay", "")))
            if m:
                return min(float(m.group(1)), 120.0)
    except Exception:
        pass
    return None


def _post(payload: dict, key: str, model: str | None = None) -> dict:
    """POST one generateContent request; maps failures to GeminiError, retries HTTP 429."""
    if not model or not _MODEL_RE.fullmatch(model):
        model = MODEL
    url = ENDPOINT.format(model=model)
    data = json.dumps(payload).encode("utf-8")
    for attempt in range(MAX_TRIES):
        req = urllib.request.Request(url, data=data, method="POST", headers={
            "Content-Type": "application/json", "x-goog-api-key": key})
        try:
            with _open(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (400, 401, 403):
                raise GeminiError("invalid_key", INVALID_KEY_MSG) from None
            if e.code in (429, 500, 503):
                if attempt + 1 >= MAX_TRIES:
                    if e.code == 429:
                        raise GeminiError("rate_limited", RATE_MSG) from None
                    raise GeminiError("other", f"Gemini request failed (HTTP {e.code})") from None
                try:
                    body = e.read()
                except Exception:
                    body = b""
                time.sleep(_retry_delay(body) or BACKOFF[attempt])
                continue
            raise GeminiError("other", f"Gemini request failed (HTTP {e.code})") from None
        except OSError:  # URLError, timeouts, connection resets
            raise GeminiError("network", NETWORK_MSG) from None
        except ValueError:
            raise GeminiError("other", "Gemini returned an unreadable response") from None
    raise GeminiError("rate_limited", RATE_MSG)  # pragma: no cover


def _text_of(resp: dict) -> str:
    try:
        return resp["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        raise GeminiError("other", "Gemini returned no text") from None


def check_key(key: str, model: str | None = None) -> None:
    """Tiny request to verify the key. Raises GeminiError on failure."""
    if not key:
        raise GeminiError("invalid_key", INVALID_KEY_MSG)
    _post({"contents": [{"role": "user", "parts": [{"text": "Reply with OK."}]}],
           "generationConfig": {"maxOutputTokens": 16}}, key, model)


def _system_prompt(target_label: str) -> str:
    lang = _LANG_NAMES.get(target_label, target_label)
    return (f"You translate subtitle lines into {lang}. Keep the meaning and tone. "
            "The input is JSON with 'context' (earlier lines, read-only, do NOT translate or return them) "
            "and 'items' (lines to translate). Keep the same ids and return exactly one item per id "
            "as a JSON array of {i, t}. Do not merge or split items.")


def _chunks(indexed: list[tuple[int, str]]) -> list[list[tuple[int, str]]]:
    out, cur, size = [], [], 0
    for item in indexed:
        if cur and size + len(item[1]) > CHUNK_CHARS:
            out.append(cur)
            cur, size = [], 0
        cur.append(item)
        size += len(item[1])
    if cur:
        out.append(cur)
    return out


def _translate_chunk(chunk, context, target_label, key, model) -> dict[int, str] | None:
    """Return {id: translation}, or None when the ids/shape of the response are wrong."""
    user = json.dumps({"context": [{"i": i, "t": t} for i, t in context],
                       "items": [{"i": i, "t": t} for i, t in chunk]}, ensure_ascii=False)
    resp = _post({
        "systemInstruction": {"parts": [{"text": _system_prompt(target_label)}]},
        "contents": [{"role": "user", "parts": [{"text": user}]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": _SCHEMA,
                             "temperature": 0.2},
    }, key, model)
    try:
        items = json.loads(_text_of(resp))
        if not all(type(x["i"]) is int for x in items):
            return None
        got = {x["i"]: x["t"] for x in items}
        if len(got) != len(items) or set(got) != {i for i, _ in chunk}:
            return None
        if not all(isinstance(t, str) for t in got.values()):
            return None
        return {i: t.strip() for i, t in got.items()}
    except (GeminiError, ValueError, KeyError, TypeError, ArithmeticError):
        return None


def translate_segments(segments: list[Segment], target_label: str, key: str,
                       cb: Callable[[float], None] | None = None,
                       log: Callable[[str], None] | None = None,
                       fallback: Callable[[list[Segment]], list[Segment]] | None = None,
                       model: str | None = None) -> list[Segment]:
    """Translate all segments in ordered chunks; one result per input, timestamps unchanged."""
    if not segments:
        return segments
    texts = [s.text for s in segments]
    out = list(texts)  # empty segments stay as they are
    indexed = [(i, t) for i, t in enumerate(texts) if t.strip()]
    chunks = _chunks(indexed)
    for n, chunk in enumerate(chunks):
        first = chunk[0][0]
        context = [(i, texts[i]) for i in range(max(0, first - CONTEXT_LINES), first) if texts[i].strip()]
        res = _translate_chunk(chunk, context, target_label, key, model)
        if res is None:
            if log:
                log(f"Gemini returned mismatched lines for part {n + 1}/{len(chunks)}; retrying.")
            res = _translate_chunk(chunk, context, target_label, key, model)
        if res is None:
            if fallback is None:
                raise GeminiError("other", "Gemini returned mismatched lines")
            if log:
                log(f"Gemini failed on part {n + 1}/{len(chunks)}; using local translation for it.")
            part = fallback([segments[i] for i, _ in chunk])
            res = {i: p.text for (i, _), p in zip(chunk, part)}
        for i, t in res.items():
            out[i] = t
        if cb:
            cb((n + 1) / len(chunks))
    if not chunks and cb:
        cb(1.0)
    return [Segment(s.start, s.end, t) for s, t in zip(segments, out)]
