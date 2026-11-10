"""Offline transcript translation with NLLB-200 (distilled 600M) on CTranslate2."""
from typing import Callable

from app import transcriber
from app.transcriber import Segment

# Public CTranslate2 int8 conversion of facebook/nllb-200-distilled-600M (ships sentencepiece.bpe.model)
MODEL_REPO = "JustFrederik/nllb-200-distilled-600M-ct2-int8"
MODEL_REVISION = "302d78f00e6fdb50a1064059df7c392b735e9d05"
BATCH_SIZE = 16

ORIGINAL = "Original (no translation)"
SERBIAN_LATIN = "Serbian (Latin)"

# UI label -> NLLB code; None = keep the original text
TARGETS: dict[str, str | None] = {
    ORIGINAL: None, "English": "eng_Latn", "Serbian (Cyrillic)": "srp_Cyrl",
    SERBIAN_LATIN: "srp_Cyrl",  # translated to Cyrillic, then transliterated
    "Croatian": "hrv_Latn", "Bosnian": "bos_Latn", "German": "deu_Latn", "French": "fra_Latn",
    "Spanish": "spa_Latn", "Italian": "ita_Latn", "Russian": "rus_Cyrl",
    "Portuguese": "por_Latn", "Dutch": "nld_Latn", "Polish": "pol_Latn", "Turkish": "tur_Latn",
}

# Whisper ISO code -> NLLB code
WHISPER_TO_NLLB: dict[str, str] = {
    "en": "eng_Latn", "sr": "srp_Cyrl", "hr": "hrv_Latn", "bs": "bos_Latn", "de": "deu_Latn",
    "fr": "fra_Latn", "es": "spa_Latn", "it": "ita_Latn", "ru": "rus_Cyrl", "pt": "por_Latn",
    "nl": "nld_Latn", "pl": "pol_Latn", "tr": "tur_Latn",
}

_CYR = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "ђ": "đ", "е": "e", "ж": "ž", "з": "z",
    "и": "i", "ј": "j", "к": "k", "л": "l", "љ": "lj", "м": "m", "н": "n", "њ": "nj", "о": "o",
    "п": "p", "р": "r", "с": "s", "т": "t", "ћ": "ć", "у": "u", "ф": "f", "х": "h", "ц": "c",
    "ч": "č", "џ": "dž", "ш": "š",
}

def cyr_to_lat(text: str) -> str:
    """Transliterate Serbian Cyrillic to Latin (Lj, Nj, Dž; full caps inside upper-case words)."""
    out = []
    for i, ch in enumerate(text):
        lat = _CYR.get(ch.lower())
        if lat is None:
            out.append(ch)
        elif not ch.isupper():
            out.append(lat)
        elif len(lat) > 1 and i + 1 < len(text) and text[i + 1].isupper():
            out.append(lat.upper())
        else:
            out.append(lat.capitalize())
    return "".join(out)


_assets: dict = {}  # model repo -> (snapshot path, SentencePieceProcessor)
_models: dict = {}  # (model repo, device) -> ctranslate2.Translator


def _is_downloaded() -> bool:
    try:
        from huggingface_hub import snapshot_download
        snapshot_download(MODEL_REPO, revision=MODEL_REVISION, local_files_only=True)
        return True
    except Exception:
        return False


def _load_assets():
    from huggingface_hub import snapshot_download
    import sentencepiece
    path = snapshot_download(MODEL_REPO, revision=MODEL_REVISION)
    sp = sentencepiece.SentencePieceProcessor()
    sp.load(f"{path}/sentencepiece.bpe.model")
    return path, sp


def _make_translator(path: str, device: str, compute: str):
    import ctranslate2
    return ctranslate2.Translator(path, device=device, compute_type=compute)


def _fetch(log):
    """Download (first use) and load the tokenizer. Failures here are not GPU failures."""
    if MODEL_REPO in _assets:
        return _assets[MODEL_REPO]
    if log:
        if _is_downloaded():
            log("Loading translation model...")
        else:
            log("Downloading translation model (first use only)...")
    _assets[MODEL_REPO] = _load_assets()
    return _assets[MODEL_REPO]


def _get_model(device: str, compute: str, assets, log):
    path, sp = assets
    key = (MODEL_REPO, device)
    if key in _models:
        if log:
            log(f"Using already loaded translation model on {device}.")
    else:
        if log:
            log(f"Starting translation model on {device}...")
        _models[key] = _make_translator(path, device, compute)
    return _models[key], sp


def _translate_all(model, texts: list[str], src: str, tgt: str, cb) -> list[str]:
    translator, sp = model
    out = list(texts)  # empty segments stay as they are
    todo = [i for i, t in enumerate(texts) if t.strip()]
    total = len(texts)
    done = total - len(todo)
    for n in range(0, len(todo), BATCH_SIZE):
        idx = todo[n:n + BATCH_SIZE]
        batch = [sp.encode(texts[i], out_type=str) + ["</s>", src] for i in idx]
        results = translator.translate_batch(batch, target_prefix=[[tgt]] * len(batch), beam_size=4)
        for i, r in zip(idx, results):
            out[i] = sp.decode(r.hypotheses[0][1:]).strip()  # drop the leading target-language token
        done += len(idx)
        if cb:
            cb(min(done / total, 1.0))
    return out


def translate_segments(segments: list[Segment], src_iso: str, target_label: str,
                       cb: Callable[[float], None] | None = None,
                       log: Callable[[str], None] | None = None) -> list[Segment]:
    """Translate segments offline, keeping timestamps. A GPU failure falls back to CPU."""
    tgt = TARGETS.get(target_label)
    if tgt is None or not segments:
        return segments
    src = WHISPER_TO_NLLB.get(src_iso)
    if src is None:
        raise ValueError(f"Translation from language '{src_iso}' is not supported.")
    if src == tgt:  # same language: no model; only transliterate for Serbian (Latin)
        if target_label == SERBIAN_LATIN:
            return [Segment(s.start, s.end, cyr_to_lat(s.text)) for s in segments]
        return segments
    texts = [s.text for s in segments]
    if not any(t.strip() for t in texts):
        if cb:
            cb(1.0)
        return segments
    assets = _fetch(log)
    device, compute = transcriber._device()
    try:
        out = _translate_all(_get_model(device, compute, assets, log), texts, src, tgt, cb)
    except Exception as e:
        if device != "cuda":
            raise
        transcriber._cuda_broken = True
        _models.pop((MODEL_REPO, "cuda"), None)
        if log:
            log(f"GPU failed ({type(e).__name__}: {e}). Using CPU instead.")
        out = _translate_all(_get_model("cpu", "int8", assets, log), texts, src, tgt, cb)
    if target_label == SERBIAN_LATIN:
        out = [cyr_to_lat(t) for t in out]
    return [Segment(s.start, s.end, t) for s, t in zip(segments, out)]


LOCAL_ENGINE = "Local (NLLB, offline)"
GEMINI_ENGINE = "Gemini (online, better context)"
ENGINES = [LOCAL_ENGINE, GEMINI_ENGINE]


def translate(segments: list[Segment], src_iso: str, target_label: str, engine: str = LOCAL_ENGINE,
              api_key: str = "", cb: Callable[[float], None] | None = None,
              log: Callable[[str], None] | None = None, model: str | None = None) -> list[Segment]:
    """Translate with the chosen engine; Gemini falls back to local NLLB per failed chunk."""
    tgt = TARGETS.get(target_label)
    src = WHISPER_TO_NLLB.get(src_iso)
    if engine != GEMINI_ENGINE or tgt is None or not segments or (src is not None and src == tgt):
        return translate_segments(segments, src_iso, target_label, cb, log)
    from app import gemini

    def fallback(chunk: list[Segment]) -> list[Segment]:
        if src is None:
            if log:
                log(f"Local translation does not support '{src_iso}'; "
                    "keeping the original text for this part.")
            return chunk
        return translate_segments(chunk, src_iso, target_label, None, log)

    return gemini.translate_segments(segments, target_label, api_key, cb, log,
                                     model=model, fallback=fallback)
