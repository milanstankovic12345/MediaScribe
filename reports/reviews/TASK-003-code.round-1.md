---
task: TASK-003
kind: code
reviewer: code-reviewer
model: claude-opus-5-5
round: 1
verdict: block
scope_checked:
  - app/translator.py
  - tests/test_translator.py
  - requirements.txt
  - app/transcriber.py
  - run.bat
not_checked:
  - Real model download and CTranslate2/NLLB inference
  - Callers of translator (none yet; UI wiring is a later task)
findings:
  - id: CR-1
    severity: high
    title: sr source + Serbian (Latin) loads the model and re-translates Serbian into Serbian instead of only transliterating (breaks the src==tgt acceptance criterion)
    location: app/translator.py:114
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-2
    severity: medium
    title: Non-GPU failures on the cuda path (offline download, missing sentencepiece) set transcriber._cuda_broken, disabling GPU for Whisper too
    location: app/translator.py:118
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-3
    severity: low
    title: cyr_to_lat gives mixed case for all-caps digraphs (LJUBAV becomes LjUBAV)
    location: app/translator.py:40
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-4
    severity: low
    title: No tests for unsupported source ISO, sr to Serbian (Latin), or all-empty segments (cb never called)
    location: tests/test_translator.py:72
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
---

## Validation re-run

- `.venv/Scripts/python -m pytest tests/test_translator.py -q`: exit 0, 8 passed (matches the handoff)
- `.venv/Scripts/python -m pytest -q`: exit 0, 37 passed (matches the handoff)
- HF API check: `JustFrederik/nllb-200-distilled-600M-ct2-int8` at `302d78f0...` exists and ships `sentencepiece.bpe.model` and `model.bin`. License CC-BY-NC-4.0, acceptable for personal use.

All other acceptance criteria verified as met. The src==tgt criterion ("src==tgt returns segments unchanged without loading a model") is not met for sr to Serbian (Latin) (CR-1).

## Findings

### CR-1 (High, 90): sr + Serbian (Latin) runs NLLB srp_Cyrl to srp_Cyrl
- **Location:** `app/translator.py:114`
- **Impact:** For a Serbian video with target Serbian (Latin), src == tgt, but the code downloads (about 600 MB) and runs the model. Same-language NLLB passes tend to paraphrase, drop text or hallucinate, so the user gets a rewritten transcript instead of the faithful Whisper text in Latin script. This is the most likely use of the feature for this user, and it breaks the acceptance criterion even though the handoff lists it as a decision.
- **Reproduction:** Make `_build` record calls, then call `translate_segments([Segment(0,1,"Zdravo")], "sr", "Serbian (Latin)")`. `_build` is called with cpu (reproduced).
- **Fix:** When `src == tgt`, return `[Segment(s.start, s.end, cyr_to_lat(s.text)) ...]` for SERBIAN_LATIN and otherwise return `segments`, without loading a model. Latin input passes through unchanged. Add a test.

### CR-2 (Medium, 95): any cuda-path error is treated as a GPU failure
- **Location:** `app/translator.py:118-127`. The try block covers `_build`, which does `snapshot_download` and the sentencepiece import and load.
- **Impact:** On a GPU machine, an offline first use, a missing sentencepiece, or a corrupt cache gets the log message "GPU failed" and sets the shared `transcriber._cuda_broken = True`. Every later Whisper run then stays on CPU until restart, and the CPU retry fails with the same error anyway. A missing sentencepiece is likely: the current .venv lacks it, and run.bat only installs requirements when it creates the venv.
- **Reproduction:** Make `_device` return cuda and `_build` raise `OSError("offline")`. The log shows "GPU failed ... Using CPU instead", the error is re-raised, and `_cuda_broken` is True (reproduced).
- **Fix:** Resolve the snapshot path and load the SentencePiece model before the try. Keep only `ctranslate2.Translator(...)` and `translate_batch` inside the cuda-fallback try.

### CR-3 (Low, 95): all-caps digraphs
- **Location:** `app/translator.py:40`
- **Impact/Reproduction:** `cyr_to_lat` on the all-caps Cyrillic word for LJUBAV returns `LjUBAV` (reproduced). Only all-caps text is affected.
- **Fix:** Emit full caps (LJ, NJ, and D plus Z-caron) when the next character is upper case.

### CR-4 (Low, 90): test gaps
- **Location:** `tests/test_translator.py`
- **Impact:** These paths have no tests: the ValueError for an unsupported source ISO (for example ja), sr to Serbian (Latin), and all-empty segments. In the all-empty case `_translate_all` never calls `cb`, so the progress bar never reaches 1.0.
- **Fix:** Add the tests, and call `cb(1.0)` when there is nothing to translate.

## Info
- sentencepiece is not installed in the current .venv. Tests pass only because `_build` is faked. Existing installs need `pip install -r requirements.txt` (run.bat/README are out of scope).
- The `log` parameter of `_build` is unused.

## Questions (below threshold)
- The source order `tokens + [</s>, src]` is the legacy NLLB order the task dictated. Current transformers and the CTranslate2 example put `src` first. Check quality on the first real run.

## Coverage statement
Read all of translator.py and test_translator.py, the requirements diff, transcriber.py (shared device and cache state) and run.bat. Re-ran both validation commands. Checked the HF revision. Reproduced CR-1 to CR-3 with monkeypatched scripts; nothing was downloaded. Not checked: real download and inference quality, real GPU behaviour, concurrent use of `_models`, UI integration. Having no further findings does not prove correctness.
