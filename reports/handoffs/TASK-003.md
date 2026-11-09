---
task: TASK-003
agent: implementer
model: claude-sonnet-5-5
attempt: 1
status: done
summary: Fixed review round-1 findings CR-1 to CR-4 in the NLLB translator. Same-language Serbian now only transliterates, download and tokenizer failures no longer mark CUDA broken, all-caps digraphs are fixed, and the missing tests are added.
files_modified:
  - app/translator.py
  - tests/test_translator.py
tests:
  - cmd: .venv/Scripts/python -m pytest tests/test_translator.py -q
    exit_code: 0
    summary: 12 passed, 0 failed
  - cmd: .venv/Scripts/python -m pytest -q
    exit_code: 0
    summary: 41 passed, 0 failed
unresolved: []
risks:
  - Real download and inference are still unverified, because tests use fakes.
  - sentencepiece must be installed in existing venvs (pip install -r requirements.txt).
decisions:
  - Split _build into _fetch (download plus SentencePiece load, cached in _assets) and _make_translator (ctranslate2). Only the translator creation and translate_batch sit inside the cuda-fallback try.
  - Model pinned to JustFrederik/nllb-200-distilled-600M-ct2-int8 at revision 302d78f00e6fdb50a1064059df7c392b735e9d05.
next_steps: []
blocker: null
---

## What changed
- CR-1: when src equals tgt, translate_segments loads no model. It returns segments unchanged, or transliterated with cyr_to_lat for Serbian (Latin).
- CR-2: _fetch runs before the try block, so offline or sentencepiece errors propagate without setting transcriber._cuda_broken.
- CR-3: cyr_to_lat is now a loop and emits LJ, NJ and DŽ when the next character is upper case.
- CR-4: new tests for the unsupported source ISO, sr to Serbian (Latin), all-empty segments and the download failure on cuda. All-empty input calls cb(1.0) and loads no model.

## Evidence
Both validation commands exit 0 (12 and 41 passed).

## Notes for the next session
Test fixtures now patch _load_assets and _make_translator instead of _build. The "first use only" log is emitted by _fetch.
