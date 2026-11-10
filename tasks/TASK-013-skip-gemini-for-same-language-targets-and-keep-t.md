---
id: TASK-013
title: Skip Gemini for same-language targets and keep text when NLLB lacks the source
status: done
agent: implementer
skills: []
model_tier: coding
priority: p2
depends_on: []
files_allowed: ["app/translator.py", "tests/test_translator.py"]
files_excluded: []
review: ["code"]
validation:
  - cmd: .venv/Scripts/python -m pytest tests/test_translator.py -q
    expect: exit 0
  - cmd: .venv/Scripts/python -m pytest -q
    expect: exit 0
acceptance:
  - "same language, Gemini engine: translator.translate(segs, \"en\", \"English\", translator.GEMINI_ENGINE, \"k\") returns the input segments unchanged (same texts and timestamps) and never calls gemini.translate_segments or loads the NLLB model (_fetch / _get_model not called); the same holds for \"hr\" -> \"Croatian\" and \"sr\" -> \"Serbian (Cyrillic)\""
  - "same language with Serbian (Latin): translator.translate([Segment(1, 2, \"Љубав\"), Segment(2, 3, \"Zdravo\")], \"sr\", \"Serbian (Latin)\", translator.GEMINI_ENGINE, \"k\") returns texts [\"Ljubav\", \"Zdravo\"] with timestamps (1, 2) and (2, 3), without calling Gemini or loading the model (the existing cyr_to_lat rule)"
  - "different languages still go to Gemini: translate(segs, \"en\", \"German\", GEMINI_ENGINE, key, model=\"m\") calls gemini.translate_segments with that target, key and model (sr -> Croatian also goes to Gemini, since srp_Cyrl != hrv_Latn)"
  - "unsupported source with Gemini: when gemini.translate_segments calls its fallback for a chunk and src_iso is not in WHISPER_TO_NLLB (e.g. \"ja\", or None), the fallback returns that chunk's segments with their original text and timestamps, logs one line per failed chunk that contains the source code and the words \"original text\", and raises nothing; the NLLB model is not loaded"
  - "supported source with Gemini: the fallback still translates the failed chunk with local NLLB (translate_segments(chunk, src_iso, target_label, None, log)), as before"
  - "local engine unchanged: translate_segments(..., \"ja\", \"German\") still raises ValueError (test_unsupported_source_raises still passes), and all existing tests in tests/test_translator.py and tests/test_gemini.py (including test_translator_dispatch_gemini_with_local_fallback) pass"
  - "tests for every criterion above live in tests/test_translator.py; gemini.translate_segments is monkeypatched (no network); no real NLLB; no new dependency; full suite passes"
max_retries: 2
attempts: 0
created: 2026-11-10
updated: 2026-11-10
---

## Objective

Make `translator.translate` with the Gemini engine skip the API when the source already is the target language, and make its per-chunk local fallback keep the original text (with a log line) instead of raising when NLLB does not support the source language.

## Context

- Finding: `reports/reviews/TASK-008-code.md` CR-6 (info, `app/translator.py:170-175`): Gemini is called even when source and target are the same language (wasted quota); for sources NLLB lacks (e.g. `ja`), a twice-failed chunk falls back to `translate_segments`, which raises `ValueError` and aborts the whole run. It was deferred in `tasks/TASK-011-harden-gemini-retries-fallback-redirects-and-mod.md`.
- Testing rules: `project-context/project-profile.md` (Notes, Testing). Monkeypatching only. Reuse the `fake` fixture and the `boom` pattern in `tests/test_translator.py` (`test_no_model_for_original_or_same_language`, `test_serbian_source_to_latin_only_transliterates`). Monkeypatch `app.gemini.translate_segments` (import `from app import gemini` in the test) with a fake that records its args and/or calls `fallback(segments)`; its signature is `translate_segments(segments, target_label, key, cb, log, fallback=..., model=...)` (see the fake in `tests/test_gemini.py:199`).
- **Same-language shortcut** (`app/translator.py:166-175`, `translate`): the dispatcher sends to local `translate_segments` when the engine is not Gemini, the target is Original, or there are no segments. Decision: also send to local `translate_segments(segments, src_iso, target_label, cb, log)` when `WHISPER_TO_NLLB.get(src_iso)` equals `TARGETS[target_label]` (both non-None). The local function's existing `src == tgt` branch (lines 135-138) already returns the segments unchanged, or transliterated with `cyr_to_lat` for `Serbian (Latin)`, without loading a model. Do not duplicate that logic.
- **Unsupported-source fallback** (`translate`, the `fallback=lambda chunk: ...` argument): Decision: replace the lambda with a small inner function. If `WHISPER_TO_NLLB.get(src_iso)` is None, log (when `log` is given) a line such as `Local translation does not support '<src_iso>'; keeping the original text for this part.` and return the chunk unchanged. Otherwise call `translate_segments(chunk, src_iso, target_label, None, log)` as now. The chunk text is transcript text, not a secret; never log the API key.
- Do not change `translate_segments` itself: the local engine with an unsupported source keeps raising `ValueError`, which the Transcribe screen already reports.
- `app/gemini.py` and `tests/test_gemini.py` belong to TASK-012, which may run in parallel; do not edit them.
- Rules (CLAUDE.md): core modules stay UI-free; no new dependencies; `translator.py` module state (`_assets`, `_models`, shared `transcriber._cuda_broken`) is untouched by this change.

## Steps

1. Read `app/translator.py` (`translate_segments`, `translate`), `tests/test_translator.py`, and the dispatcher tests in `tests/test_gemini.py` (around lines 194-215).
2. Add failing tests in `tests/test_translator.py`: same-language skip (en/English, hr/Croatian, sr/Serbian (Cyrillic)), Serbian (Latin) transliteration via the Gemini engine, different-language dispatch to Gemini, unsupported-source fallback keeps text and logs (ja and None), supported-source fallback still uses NLLB.
3. Implement the shortcut and the fallback function in `translate`.
4. Run every validation command and record the exit codes and pass counts in the handoff.

## Blockers

Stop and write a handoff with `status: blocked` if:
- the change needs files outside `files_allowed` (for example `app/gemini.py` or `app/screens/transcribe.py`),
- an acceptance criterion is ambiguous,
- a dependency is missing, or
- a validation command cannot run in this environment.

Never widen scope silently.

## Deliverables

- Code/tests within `files_allowed`
- `reports/handoffs/TASK-013.md` (see templates/handoff.md)
