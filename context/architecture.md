# Vectra3D — Architecture

How the code is organized, which libraries are used and why, and how data flows. Library-specific pitfalls and version rules are in `library-docs.md`; coding rules are in `code-standards.md`.

---

## 1. Tech stack

| Purpose | Library | Notes |
|---|---|---|
| Language | **Python 3.12** | MediaPipe officially lists support up to 3.12. Do not use 3.13+. |
| Environment and packages | **uv** | Manages the Python version, virtual environment, and a lock file with exact versions. |
| Hand tracking | **MediaPipe** (1.0.x), **Tasks API** | Use `GestureRecognizer`, which returns landmarks, handedness, and built-in gestures in one call. |
| Webcam | **OpenCV** (`opencv-python-headless`) | Only for reading camera frames. Headless, because Qt handles all display; this avoids bundling a second GUI toolkit. |
| 3D rendering | **PyVista** + **pyvistaqt** | 3D view embedded in the Qt window with `pyvistaqt.QtInteractor`. |
| Window and panels | **PySide6** | Main window, info panel, action panel, dialogs. |
| Math | **NumPy** | All vector math. |
| Tests | **pytest** | Automated tests for math and gesture logic. |
| Packaging | **PyInstaller** | One-folder Windows build, shared as a zip. |

Version rules and known library pitfalls: see `library-docs.md`.

---

## 2. Layered design
The code is split into layers. **A layer may only use layers below it**, never above. This keeps each part testable on its own.

```
app        ← wires everything together, starts the program
ui         ← Qt window, info panel, action panel, dialogs
render     ← draws the scene with PyVista
tracking   ← camera + MediaPipe, runs in a background thread
gestures   ← gesture state machine (pure logic, no camera, no UI)
state      ← the vectors, the result, undo history, settings
core       ← pure vector math (NumPy only)
```

Key rules:
- **`core` and `gestures` import no Qt, PyVista, OpenCV, or MediaPipe.** This is what makes them testable with pytest alone.
- **`state` is the single source of truth.** Nothing else stores vector data. The info panel and 3D view only *display* state; they never own it.
- **All changes go through actions.** Creating, editing, locking, deleting, and so on are functions in `state/actions.py`. Both the panel and the gesture engine call these same actions. This guarantees every gesture has a panel equivalent and every change is recorded for undo in one place.
- **The gesture engine does not change vectors directly.** It outputs *intents* (for example "begin create," "update create preview," "commit," "cancel"), and the app turns those into actions.

---

## 3. Folder structure

```
vectra3d/
├── pyproject.toml
├── uv.lock
├── CLAUDE.md                           ← entry point for Claude Code
├── context/                            ← project-overview, features, interaction-spec,
│                                          architecture, code-standards, library-docs,
│                                          build-plan, progress-tracker
├── docs/                               ← how-it-works explanations for people
├── assets/
│   └── models/
│       └── gesture_recognizer.task     ← bundled MediaPipe model
├── src/
│   └── vectra3d/
│       ├── __main__.py                 ← entry point: python -m vectra3d
│       ├── app.py
│       ├── paths.py                    ← resource_path() helper (see `library-docs.md`)
│       ├── config.py                   ← all tunable values (interaction-spec.md §9)
│       ├── core/
│       │   ├── vector_math.py          ← components, magnitude, angles, unit vector
│       │   ├── operations.py           ← resultant, subtraction, scalar multiplication
│       │   ├── spherical.py            ← r, θ, φ conversions
│       │   └── formatting.py           ← 2 decimals, degrees, no "-0.00"
│       ├── state/
│       │   ├── models.py               ← Vector, Result, Settings (dataclasses)
│       │   ├── store.py                ← holds all vectors, emits change events
│       │   ├── actions.py              ← every allowed change
│       │   ├── undo.py                 ← snapshot-based undo/redo
│       │   └── naming.py               ← letters A–J, colors
│       ├── gestures/
│       │   ├── hand_frame.py           ← plain data: landmarks + gesture label per hand
│       │   ├── hand_metrics.py         ← hand scale, pinch detection, smoothing
│       │   ├── state_machine.py        ← IDLE / CREATING / RESIZING / STEERING / HOLDING
│       │   └── intents.py              ← what the engine outputs
│       ├── tracking/
│       │   ├── camera.py               ← opens the webcam
│       │   └── tracker_thread.py       ← QThread: camera → MediaPipe → HandFrame
│       ├── render/
│       │   ├── scene.py                ← axes, grid, scale changes
│       │   ├── vector_actor.py         ← arrows, labels, highlight
│       │   ├── overlays.py             ← components, projections, angle arcs
│       │   └── animations.py           ← transitions, head-to-tail
│       └── ui/
│           ├── main_window.py
│           ├── info_panel.py
│           ├── action_panel.py
│           ├── camera_preview.py
│           └── dialogs.py              ← confirmations
├── tests/
│   ├── core/                           ← math tests
│   ├── state/                          ← actions, naming, undo tests
│   └── gestures/                       ← gesture tests with synthetic hand data
└── packaging/
    └── vectra3d.spec                   ← PyInstaller build file
```

---

## 4. Data flow

### 4.1 Panel input
```
User clicks / types → ui → state.actions → store updates → change event
    → render redraws + info panel refreshes
```

### 4.2 Hand input
```
Webcam frame
  → [tracker thread] flip (mirror) → BGR→RGB → MediaPipe GestureRecognizer
  → HandFrame (plain data) + preview image
  → Qt signal to the main thread
  → [main thread] gestures.state_machine → intents
  → app turns intents into state.actions → store → render + info panel
```

### 4.3 Threads
- **Background thread (`tracker_thread`):** reads the camera and runs MediaPipe. It never touches Qt widgets, PyVista, or the store. It only emits signals carrying plain data.
- **Main thread:** everything else, including all Qt and PyVista calls. VTK/PyVista is not thread-safe; calling it from the tracker thread will cause crashes.
- MediaPipe runs in **VIDEO mode** (`recognize_for_video`), called synchronously inside the tracker thread with increasing millisecond timestamps. This is simpler than LIVE_STREAM mode's callbacks.
- If MediaPipe is slower than the camera, frames are dropped, not queued, so the app never lags behind the hand.

---

## 5. Testing strategy
- **`core`:** every function tested against hand-calculated values, including edge cases (zero vector, vectors along axes, negative components).
- **`state`:** actions, naming (lowest free letter), 10-vector limit, locking rules, undo/redo, and result live updates.
- **`gestures`:** the state machine is tested by feeding it **synthetic sequences of hand frames** (e.g. "two pinches close together, then moving apart over 20 frames") and checking the intents it outputs. This lets most gesture logic be tested without a webcam. Final tuning still needs real hands (see `interaction-spec.md` section 11).
- Run all tests with `uv run pytest`. All tests must pass before a feature group is marked complete.

---

## 6. Privacy and network
- Webcam frames are processed in memory only. They are never saved to disk and never sent anywhere.
- **MediaPipe Tasks sends performance and usage metrics to Google** when a network is available. Google's privacy notice (updated June 5, 2026) says input images are processed on-device and not sent, but performance and utilization metrics are, and that apps are responsible for informing users. No off switch is documented.
- The app was to show a first-launch notice saying so (F-21). **That notice was deleted on 2026-09-24 at the user's decision**, so the app itself does not tell students. This was done knowing that Google's notice puts the duty to inform users on the app; the decision is recorded in `progress-tracker.md`.
- The packaging phase still verifies the app works fully with the internet disconnected.

---

## 7. Commands

| Task | Command |
|---|---|
| Install everything | `uv sync` |
| Run the app | `uv run python -m vectra3d` |
| Run tests | `uv run pytest` |
| Build the `.exe` | `uv run pyinstaller packaging/vectra3d.spec` |

**Smoke test** (build-plan step G0.4, before any feature work): the app opens a window with an empty 3D view that can be rotated with the mouse, and closes cleanly. If this fails, fix it before anything else.
