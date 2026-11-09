---
task: TASK-003
kind: code
reviewer: code-reviewer
model: claude-opus-5-5
round: 2
verdict: approve_with_notes
scope_checked:
  - app/translator.py
  - tests/test_translator.py
  - requirements.txt
  - app/transcriber.py
not_checked:
  - Real model download and CTranslate2/NLLB inference
  - Real GPU behaviour
  - Callers of translator (none yet; UI wiring is a later task)
findings:
  - id: CR-1
    severity: high
    title: sr source + Serbian (Latin) loads the model and re-translates Serbian into Serbian instead of only transliterating (breaks the src==tgt acceptance criterion)
    location: app/translator.py:135
    confidence: 95
    status: fixed
    verified: true
    acceptance_ref: null
  - id: CR-2
    severity: medium
    title: Non-GPU failures on the cuda path (offline download, missing sentencepiece) set transcriber._cuda_broken, disabling GPU for Whisper too
    location: app/translator.py:144
    confidence: 95
    status: fixed
    verified: true
    acceptance_ref: null
  - id: CR-3
    severity: low
    title: cyr_to_lat still gives mixed case for all-caps words that end in a digraph letter (KONJ becomes KONj, PRIJATELJ becomes PRIJATELj)
    location: app/translator.py:47
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-4
    severity: low
    title: No tests for unsupported source ISO, sr to Serbian (Latin), or all-empty segments (cb never called)
    location: tests/test_translator.py:107
    confidence: 95
    status: fixed
    verified: true
    acceptance_ref: null
---

## Validation re-run

- `.venv/Scripts/python -m pytest tests/test_translator.py -q`: exit 0, 12 passed (matches the handoff)
- `.venv/Scripts/python -m pytest -q`: exit 0, 41 passed (matches the handoff)
- `git diff eab24b9 -- requirements.txt`: only `+sentencepiece` (acceptance met)

All acceptance criteria are verified as met, including "src==tgt returns segments unchanged without loading a model".

## Prior findings

### CR-1: fixed (verified)
`translate_segments` returns before `_fetch` when `src == tgt` (lines 135-138). Reproduced with `_fetch` and `_get_model` instrumented: `translate_segments([Seg("Здраво Љубо"), Seg("Zdravo")], "sr", "Serbian (Latin)")` returns `["Zdravo Ljubo", "Zdravo"]` with no fetch or model calls. `sr` to "Serbian (Cyrillic)" returns the input unchanged, also with no calls. This is covered by `test_serbian_source_to_latin_only_transliterates`.

### CR-2: fixed (verified)
`_fetch` (download plus SentencePiece load) now runs before the try block (line 144). Only `_make_translator` and `translate_batch` are inside the cuda fallback. Reproduced: with `_device` set to cuda and `_load_assets` raising `OSError("offline")`, the OSError propagates, `_cuda_broken` stays False, and the only log line is "Downloading translation model (first use only)...". This is covered by `test_download_failure_does_not_mark_cuda_broken`.

### CR-3 (Low, 95): partially fixed, still open
- **Location:** `app/translator.py:47-50`
- **Impact:** All-caps words that start with Љ/Њ/Џ are now correct (`ЉУБАВ` gives `LJUBAV`). All-caps words that **end** in one of these letters are still mixed case, because the last character has no following character to check, so it falls into `capitalize()`. Words like КОЊ and ПРИЈАТЕЉ are common in Serbian, so this shows up in caps titles and shouted text. It is cosmetic only.
- **Reproduction (run in this session):** `cyr_to_lat("КОЊ")` gives `KONj`. `cyr_to_lat("ПРИЈАТЕЉ!")` gives `PRIJATELj!`. A lone `Љ` gives `Lj`, which is correct.
- **Fix:** Use full upper case when the next character is upper case, or when the next character is missing or not a letter and the previous character is upper case. For example: `nxt = text[i+1] if i+1 < len(text) else ""; prv = text[i-1] if i else ""; full = nxt.isupper() or (not nxt.isalpha() and prv.isupper())`. Add `assert cyr_to_lat("КОЊ") == "KONJ"` to the tests.

### CR-4: fixed (verified)
New tests cover the unsupported source (`ja` raises ValueError), sr to Serbian (Latin), and all-empty segments. `cb(1.0)` is called once and no model loads (lines 140-143). The new download-failure test also covers CR-2.

## New findings
None at or above the reporting threshold.

## Info
- If CUDA fails partway through a multi-batch run, `cb` has already reported partial progress, so the CPU retry makes the progress bar jump back. This is cosmetic and matches the transcriber's restart behaviour.
- A non-GPU error raised by `ctranslate2.Translator(...)` on cuda, such as a corrupt `model.bin`, still sets `_cuda_broken`. This case is rare, the CPU retry re-raises it anyway, and the narrowed try block is the reasonable trade-off.
- sentencepiece is still missing from the existing .venv. Users need `pip install -r requirements.txt` (carried over from round 1; run.bat and the README are out of scope).

## Coverage statement
Read all of `app/translator.py` and `tests/test_translator.py`, the requirements diff, and the `_device`/`_cuda_broken` code in `app/transcriber.py`. Re-ran both validation commands. Reproduced CR-1, CR-2 and CR-3 against the new code with monkeypatched inline scripts; nothing was downloaded. Not checked: real Hugging Face download, real NLLB inference quality and token order, real GPU fallback, thread safety of `_assets`/`_models`, UI integration (a later task). Having no further findings does not prove correctness.
