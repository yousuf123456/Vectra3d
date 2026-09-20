# Vectra3D — Progress Tracker

Updated after every approved step. Read this at the start of every session to see where things stand.

---

## Current status
- **Current group:** G0 — Project setup
- **Next step:** G0.2
- **Blocked on:** nothing

## Completed steps

| Step | Description | Date | Commit | Notes |
|---|---|---|---|---|
| G0.1 | Initialize Git and uv project | 2026-09-20 | `G0.1: initialize git and uv project` | Python 3.12.14. Own repo rooted at the project folder, nested inside the Desktop-level repo; remote `github.com/yousuf123456/Vectra3d` (public). `uv sync` succeeds, 55 packages installed. |

## Groups

| Group | Name | Status |
|---|---|---|
| G0 | Project setup | In progress |
| G1 | Foundation | Not started |
| G2 | Vector math and display | Not started |
| G3 | Operations | Not started |
| G4 | Hand tracking | Not started |
| G5 | Gesture control | Not started |
| G6 | Packaging | Not started |

---

## Decisions log
Decisions made during planning (2026-09-19). Add new decisions below with the date and reason.

| Date | Decision | Reason |
|---|---|---|
| 2026-09-19 | Python + PySide6 + PyVista + MediaPipe Tasks API, managed with uv | Python libraries cover CV, 3D, and math; uv locks exact versions. |
| 2026-09-19 | Python 3.12 | Highest version MediaPipe lists as supported. |
| 2026-09-19 | Entry file is `CLAUDE.md`, not `AGENTS.md` | Claude Code reads `CLAUDE.md`. |
| 2026-09-19 | Right-handed coordinates, z up; physics angle convention | Matches most physics textbooks. |
| 2026-09-19 | Screen-relative steering | Hand direction always matches the screen, even when the view is rotated. |
| 2026-09-19 | Resizing adds at the same rate as creation, not by ratio | Ratio barely responds on small vectors. |
| 2026-09-19 | First-launch privacy notice about MediaPipe metrics | MediaPipe Tasks sends usage metrics to Google; students must be told. |
| 2026-09-19 | Packaging smoke test in G0 | Catch `.exe` and model-path problems before any feature exists. |
| 2026-09-20 | Vectra3D gets its own Git repo nested inside the Desktop-level repo, pushed to a new public remote `Vectra3d` | The Desktop folder is already a Git repo for an unrelated project (Handouts, detached HEAD, large dirty tree). A nested repo keeps Vectra3D history clean without touching that project. |
| 2026-09-20 | `requires-python = ">=3.12,<3.13"` rather than `>=3.12` | An upper bound makes it impossible to resolve Python 3.13+, which MediaPipe does not support. The machine has 3.14 installed, so this is a real risk. |
| 2026-09-20 | `.venv` kept in the project folder (inside OneDrive) | Standard location that every `uv run` command expects. It is gitignored; OneDrive sync of its 1.23 GB is a user-side setting, not a code concern. |
| 2026-09-20 | Installed PySide6 6.11.2 without pre-emptively pinning below 6.10 | `library-docs.md` section 2 applies the pin only if the 3D window actually hangs. That is decided by the G0.4 smoke test. |

---

## Tuning changes
Every change to a value in `config.py` / `interaction-spec.md` section 9, with the reason from real testing.

| Date | Value | Old | New | Reason |
|---|---|---|---|---|
| | | | | |

---

## Known issues

| Found | Issue | Status |
|---|---|---|
| | | |
