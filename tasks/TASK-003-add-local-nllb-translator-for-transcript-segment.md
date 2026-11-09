---
id: TASK-003
title: Add local NLLB translator for transcript segments
status: done
agent: implementer
skills: []
model_tier: coding
priority: p2
depends_on: []
files_allowed: ["app/translator.py", "tests/test_translator.py", "requirements.txt"]
files_excluded: []
review: ["code"]
validation:
  - cmd: .venv/Scripts/python -m pytest tests/test_translator.py -q
    expect: exit 0
  - cmd: .venv/Scripts/python -m pytest -q
    expect: exit 0
acceptance:
  - TARGETS maps UI labels to NLLB codes and includes 'Original (no translation)' -> None and 'Serbian (Latin)'
  - WHISPER_TO_NLLB covers every non-None code in transcriber.LANGUAGES
  - cyr_to_lat('Љубав и ђак') == 'Ljubav i đak' (incl. lj/nj/dž and upper-case)
  - translate_segments with a fake ctranslate2 translator keeps start/end, preserves order, batches requests and reports progress
  - "'Original' target or src==tgt returns segments unchanged without loading a model"
  - a CUDA failure falls back to CPU using transcriber's _device/_cuda_broken state
  - first-use model download logs a 'first use only' message
  - requirements.txt adds sentencepiece only
max_retries: 2
attempts: 1
created: 2026-11-09
updated: 2026-11-09
---

## Objective

Create `app/translator.py` that translates transcript segments offline with NLLB-200 (distilled 600M) on CTranslate2, keeping timestamps.

## Context

Feature plan: `C:\Users\milla\.claude\plans\analyze-this-project-and-purrfect-flute.md`.
- Decision: local NLLB-200 distilled 600M, CTranslate2 int8 conversion, downloaded on first use with `huggingface_hub.snapshot_download` (already installed via faster-whisper). Pin the Hugging Face repo id AND revision in a module constant; pick a public CTranslate2 conversion that ships `sentencepiece.bpe.model`, and name it in the handoff.
- Tokenisation with `sentencepiece`: source tokens = `sp.encode(text, out_type=str) + ["</s>", src_code]`; call `translate_batch(batch, target_prefix=[[tgt_code]] * n, beam_size=4)`; drop the leading target-language token from the hypothesis before `sp.decode`.
- Public API: `TARGETS` (label -> NLLB code or None), `WHISPER_TO_NLLB` (Whisper ISO -> NLLB code), `cyr_to_lat(text)`, `translate_segments(segments, src_iso, target_label, cb=None, log=None) -> list[Segment]`.
- NLLB only has Serbian in Cyrillic (`srp_Cyrl`): "Serbian (Latin)" translates to `srp_Cyrl` and then runs `cyr_to_lat`. Other targets mirror `transcriber.LANGUAGES` (English eng_Latn, Croatian hrv_Latn, Bosnian bos_Latn, German deu_Latn, French fra_Latn, Spanish spa_Latn, Italian ita_Latn, Russian rus_Cyrl, Portuguese por_Latn, Dutch nld_Latn, Polish pol_Latn, Turkish tur_Latn).
- Device: reuse `transcriber._device()` and set `transcriber._cuda_broken = True` on a CUDA failure, then retry on CPU/int8 (same pattern as `transcriber.transcribe`). Cache loaded translators in a module dict keyed by `(model, device)`; log "Downloading translation model (first use only)..." vs "Loading..." vs "Using already loaded..." like `transcriber._get_model`.
- Batch ~16 segments; call `cb(done / total)` after each batch. Lazy-import `ctranslate2`, `sentencepiece`, `huggingface_hub` inside functions.
- Tests go in the new file `tests/test_translator.py`; monkeypatch the model loader with a fake translator/tokenizer.
- Rules (CLAUDE.md): core modules are UI-free and take plain callbacks (`cb: Callable[[float], None]`, `log: Callable[[str], None]`); no new dependencies without a reason in docs/techstack.md; tests never hit the network or run real Whisper/ffmpeg/models. Adding `sentencepiece` to requirements.txt is approved by the plan; the techstack.md entry is done in TASK-007.

## Steps

1. Write failing tests in `tests/test_translator.py` for each acceptance criterion using fakes (no downloads).
2. Implement mappings, `cyr_to_lat`, model loading/cache, batching and the GPU->CPU fallback.
3. Add `sentencepiece` to `requirements.txt`.
4. Run every validation command and record exit codes and the pinned model repo/revision in the handoff.

## Blockers

Stop and write a handoff with `status: blocked` when: the change needs files
outside `files_allowed`, an acceptance criterion is ambiguous, a dependency
is missing, or a validation command cannot run in this environment. Never
widen scope silently.

## Deliverables

- Code/tests within `files_allowed`
- `reports/handoffs/TASK-003.md` (see templates/handoff.md)
