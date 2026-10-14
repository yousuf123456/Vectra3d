# Vectra3D — Agent Instructions

Vectra3D is a Windows desktop app that lets first-year university students create, move, and analyze 3D vectors with their hands through a webcam, with an on-screen panel as a precise fallback.

## Read Before Anything Else

In this order, before any implementation:

1. context/project-overview.md
2. context/features.md
3. context/interaction-spec.md
4. context/architecture.md
5. context/code-standards.md
6. context/library-docs.md
7. context/build-plan.md
8. context/progress-tracker.md

## Stack

Python 3.12 · uv · MediaPipe 1.0.x (Tasks API) · OpenCV (headless) · PyVista +
pyvistaqt · PySide6 · NumPy · pytest · PyInstaller

Windows only, shipped as a one-folder `.exe`. English only. Works offline.
No accounts, no cloud, no saved camera data.

## Rules That Never Change

- Never use `mp.solutions` — it was removed from MediaPipe. Tasks API only
- Load the model file only through `paths.resource_path()`, from day one
- Never call PyVista, VTK, or Qt widgets from the tracker thread
- Every vector change goes through `state/actions.py`. Gestures output intents;
  they never change vectors directly
- Webcam frames are never saved to disk or sent anywhere
- Every tunable value lives in `config.py`, and changes only after real testing,
  recorded in `progress-tracker.md`
- Follow the step workflow in `build-plan.md` exactly: plan with `/architect`,
  wait for approval, build, test, report, wait for review, then mark, update
  `progress-tracker.md`, and commit
- Never weaken an acceptance criterion, skip a test, or change a tunable value
  to make something pass. Stop and report instead
- Write only the code the current step needs (`code-standards.md`)
- After every approved step, update the matching "How it's implemented"
  sections in `docs/` (see `build-plan.md`). `docs/` is for people, not agent
  instructions, and is not part of the read order
- Do not build post-MVP features until the user asks
- If the same problem persists after one corrective prompt — stop and run
  `/recover`

## Documentation

Training data is wrong about this stack. `mp.solutions` no longer exists,
most MediaPipe tutorials will not run, and pyvistaqt has had PySide6 version
problems. Assume the same of anything not covered in `context/library-docs.md`.

- Fetch current official docs the first time you touch a library in a session.
  Once per library, not per edit. If no documentation tool is available, say
  so rather than working from memory
- Check against the versions installed in `uv.lock`
- If fetched docs contradict `context/library-docs.md`, **stop and ask.** Some
  entries there are deliberate decisions
- Record important findings in the findings log in `context/library-docs.md`

## Working Practices

- **Panel first, gestures second.** Every feature is built and proven with
  typed input before any hand gesture touches it
- **Math is tested without the app.** Vector math and gesture logic get pytest
  tests with hand-calculated values; the gesture engine is tested with
  synthetic hand data before real hands are used
- **Check the 3D view visually.** After every visual change, tell the user
  exactly what to look at, rather than assuming the rendering is correct
- **Gestures need real hands.** Final gesture behavior is confirmed by the user
  with the checklist in `interaction-spec.md` section 11

## Available Skills

- `/architect` — at the planning step of every build step. Plan before building.
- `/review` — at the end of every group, and on the whole app before the student trial.
- `/recover` — when something breaks after one failed correction.
- `/remember restore` — at the start of every session.
- `/remember save` — at the end of every group, or mid-group when a session gets long.

## Commands

- Install: `uv sync`
- Run: `uv run python -m vectra3d`
- Test: `uv run pytest`
- Build: `uv run pyinstaller packaging/vectra3d.spec --noconfirm --clean`
- Zip: `uv run python -m zipfile -c dist/Vectra3D-0.1.0-windows.zip dist/Vectra3D`
- Installer (after Build): `& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" packaging\vectra3d.iss` (PowerShell)
- Check the packaged model (PowerShell): `.\dist\Vectra3D\Vectra3D.exe --check-model | Out-String`
