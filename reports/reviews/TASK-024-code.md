---
task: TASK-024
kind: code
reviewer: code-reviewer
model: claude-opus-5-5
round: 1
verdict: approve_with_notes
scope_checked:
  - app/screens/transcribe.py (full file and diff vs 6553031)
  - tests/test_transcribe_screen.py (full file, read directly; tests/ is gitignored)
  - app/transcript_import.py, app/translator.py, app/exporter.py, app/downloader.py safe_name, app/screens/base.py _start/_worker
  - reports/reviews/TASK-023-code.md CR-1, reports/reviews/TASK-023-security.md SEC-1
not_checked:
  - Real Tk file dialog filter (not visually verified)
  - Real NLLB / Gemini / ffmpeg
  - Byte diff of pre-existing tests (gitignored; checked by count only)
findings:
  - id: CR-1
    severity: low
    title: Overwrite guard runs after translation, so a doomed run still spends NLLB time or Gemini quota
    location: app/screens/transcribe.py:255-270
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-2
    severity: low
    title: Overwrite-guard tests cover only the SRT name, not the translated .md collision or case-insensitive match
    location: tests/test_transcribe_screen.py:539-549
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-3
    severity: info
    title: Valid but unlisted imported languages (e.g. ja) become unknown, so Original output is named .und
    location: app/screens/transcribe.py:27-36
    confidence: 95
    status: open
    verified: false
    acceptance_ref: null
  - id: CR-4
    severity: info
    title: _SAFE_LANGS duplicates transcript_import._KNOWN_CODES; transcript branch logs nothing before load
    location: app/screens/transcribe.py:27
    confidence: 90
    status: open
    verified: false
    acceptance_ref: null
---

## Findings

### CR-1 - Overwrite guard runs after translation (Low, 95)
- **Location:** `app/screens/transcribe.py:255-270`. The guard (267-270) runs after translate (256-263).
- **Impact:** Nothing is written, so acceptance 6 holds. But the user first waits for NLLB, or spends Gemini quota and sends text to Google, for a run that must fail. `lang`/`stem` depend only on target, `t.language` and title, so they are known before translating.
- **Reproduction:** I ran it with `translate_segments` faked. Input `Talk.de.srt` sits in the output dir, the Language menu is `en`, the target is German. The translate call was recorded `(en, German)`, then RuntimeError OVERWRITE_MSG. The input was unchanged.
- **Fix:** Compute `lang`/`stem` and run the `is_tr` guard at the top of `if subs:`, before the translate block.

### CR-2 - Guard tests miss .md and case collisions (Low, 90)
- **Location:** `tests/test_transcribe_screen.py:539-549` (acceptance 6/7)
- **Impact:** Only `Talk.en.srt` + Original against the .srt output is tested. If the guard is later narrowed to the SRT name, a silent overwrite of the input .md transcript would not be caught.
- **Reproduction:** I ran these manually and the current code is correct: `Talk.en.md` + Original + `sub_doc=(".md",)` raises and writes nothing; `Talk.en.SRT` + Original raises, because WindowsPath equality is case-insensitive. No test pins either case.
- **Fix:** Add both as real-file tests that assert RuntimeError and that only the input file exists.

### CR-3 - Unlisted languages become und (Info, 95)
- Whisper Auto may write `- Language: ja`. Re-importing that file with Original gives `Talk.und.srt` (confirmed). Gemini still works with an empty source. This is the intended SEC-1 trade-off. A two- or three-lowercase-letter rule would keep the code and still be path-safe.

### CR-4 - Maintainability (Info, 90)
- `_SAFE_LANGS`/`_clean_lang` repeat the `_KNOWN_CODES` and sr-Latn mapping in `transcript_import`, so the two can drift. The real fix belongs in `load` (TASK-023 scope).
- The transcript branch has no `_say` before `load()`, so the log stays empty until Translating.

## TASK-023 carry-over verification
- **SEC-1: handled at the wiring point.** `lang_in` (226) is the menu value (trusted `LANGUAGES` value) or `_clean_lang(...)`. `_clean_lang` allows only the 13 fixed codes; everything else becomes empty. `_lang_code` then yields a TARGETS-derived code, `sr-Latn`, `lang_in` or `und`. All are path-safe. The title goes through `safe_name` (249, 266), which covers TASK-023 CR-4. Checked: `und`, `en:evil`, a backslash dot-dot traversal string, `EN`, `None` and `ja` all map to empty, and `sr-Latn` maps to `sr`. Tests 521-526 cover `../../evil`, `xx` and `a/b`. `transcript_import.load` itself still returns the header unvalidated, so SEC-1 stays open in that module, but this caller is not exploitable.
- **CR-1 (sr-Latn/und header): handled.** sr-Latn maps to sr and und to empty (test 529-536 and my run).

## Acceptance check
1. Filter order: met (line 14, test 456). Not visually verified.
2. Transcribe mode returns TRANSCRIPT_ONLY_MSG before the MD/PDF check: met (167-168, test 440 with md=False).
3. Embed/Burn get the existing message; SRT-only gets None; the Gemini check is unchanged: met (tests 446-453).
4. No download/prepare/transcribe; load, 0.6, title, source; `Talk.de.srt`: met (tests 462-481, real SRT 552-557).
5. Menu override, unknown+Local raises before translation, Gemini passes empty, Original allowed: met (tests 484-518).
6. Overwrite raises and writes nothing: met (test 539 plus my manual .md/case checks). See CR-1 for the ordering.
7. Met. No new dependency. Existing tests cannot be diffed (gitignored). Counts are consistent: TASK-023 had 225 passed, now 243 = 225 + 18 new tests.

## Validation re-run
- `pytest tests/test_transcribe_screen.py tests/test_transcript_import.py -q`: exit 0, 101 passed.
- `pytest -q`: exit 0, 243 passed, 2 skipped. Both match the handoff.
- In-process stdin repro in a TemporaryDirectory: .md collision, .SRT case collision, translate-before-guard, ja to und, header title case, and the `_clean_lang` table.

## Coverage statement
I read the full transcribe.py and its diff, the full test file, and the related functions in transcript_import, translator, exporter, downloader and base. I re-ran both validation commands and the repros. Not checked: the real dialog, real NLLB/Gemini/ffmpeg, a byte diff of the old tests, and non-Windows paths. CLAUDE.md and docs/blueprint.md do not describe transcript input yet. They are outside files_allowed and are flagged for the orchestrator. A review without blocking findings does not prove correctness.
