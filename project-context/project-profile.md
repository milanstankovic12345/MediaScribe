---
profile_version: 1
source_hash: e2bc0e3404fdfa28
generated: 2026-10-29
generator: project-kickstarter bootstrap 0.2.0
---

# Project profile — youtube-downloader

<!-- project-kickstarter:profile:start -->
## Summary (generated — do not edit inside the markers)

- **Languages:** Python (15)
- **Package managers:** pip
- **Manifests:** `requirements-dev.txt`, `requirements.txt`
- **Monorepo:** no
- **Size:** 30 files

## Frameworks and libraries

_none detected_

## Commands

| Purpose | Command | Evidence |
|---|---|---|
| test | `pytest` | pytest detected |

## Testing

- Frameworks: pytest
- Test files: 1

## Data and APIs

- Databases: none detected
- ORM / migrations: none detected
- API styles: none detected; route dirs: none
- Integrations: none detected

## UI system

- UI present: no
- Frameworks: -; component libraries: -; styling: -
- Token/theme sources: none detected; Storybook: no; a11y tooling: none

## Delivery

- CI: none detected
- Containers: none; IaC: none

## Security-relevant

- Auth libraries: none detected
- Sensitive paths (review required): none detected
- Secret-bearing files present (names only, never read): none
- .gitignore covers .env: NO
- Threat model: missing

## Existing agent configuration

- CLAUDE.md: yes; AGENTS.md: no
- .claude/agents: builder, reviewer, tester; .claude/skills: none
- Other tools: none
<!-- project-kickstarter:profile:end -->

## Notes

Maintained by humans and the project-discoverer agent: architecture narrative,
conventions, domain glossary, known risks. Bootstrap never edits this part.

- **Corrections to the generated summary:** The UI is a CustomTkinter desktop app (Windows), so "UI present: no" is wrong. There is no web UI, no a11y tooling and no CI. Libraries in use include yt-dlp, faster-whisper, CustomTkinter and a PDF exporter. See `requirements.txt`.
- **Architecture:** see `CLAUDE.md` and `docs/blueprint.md`. Core modules (`downloader`, `audio_prep`, `transcriber`, `exporter`, `settings`) are UI-free. Screens live in `app/screens/` on a shared `Screen` base class. Workers talk to the UI through a `queue.Queue`.
- **Conventions:** long work only in worker threads. Sanitize filenames with `downloader.safe_name`. No new dependencies without a reason in `docs/techstack.md`. Personal use only, with no bypasses of site protections.
- **Testing:** `.venv\Scripts\python -m pytest`. All tests are in `tests/test_core.py`, use monkeypatching, and never hit the network.
- **Agents:** the existing `builder`, `reviewer` and `tester` agents are kept and can be assigned in tasks.
- **Known risks:** `transcriber.py` keeps module-level state (model cache, `_cuda_broken`). Any Spotify work has legal and ToS implications and needs a user decision on how the audio is sourced.
