# 04 — Software Design

How Vectra3D is built, and why it's built that way.

---

## 1. The libraries

### In plain words
Vectra3D is written in Python and builds on well-known free libraries instead of reinventing them: one to see hands, one to read the webcam, one to draw 3D graphics, one for the window and buttons, and one for the math.

### Technically

| Job | Library | Why |
|---|---|---|
| Hand tracking | MediaPipe (Tasks API) | Accurate, runs on CPU, recognizes common gestures out of the box |
| Webcam | OpenCV (headless) | Standard, reliable camera access |
| 3D graphics | PyVista + pyvistaqt | Arrows, labels, and camera controls built in; embeds in a Qt window |
| Window and panels | PySide6 (Qt) | Mature desktop UI toolkit; the official Python binding for Qt |
| Math | NumPy | Fast, well-tested vector operations |
| Tests | pytest | Standard Python testing tool |
| Environment | uv | Installs the right Python version and locks exact library versions |
| Packaging | PyInstaller | Turns the app into a Windows program that doesn't need Python |

### How it's implemented
The project is managed by **uv**, which downloads its own copy of **Python 3.12.14** (MediaPipe supports Python up to 3.12, so `pyproject.toml` sets `requires-python = ">=3.12,<3.13"` to make a newer Python impossible to pick by accident).

`pyproject.toml` lists the libraries with loose minimum versions; `uv.lock` records the exact version of every package actually installed, so the same versions are reinstalled on any machine. These are the versions locked in step G0.1:

| Package | Version |
|---|---|
| Python | 3.12.14 |
| mediapipe | 1.0.1 |
| opencv-python-headless | 5.0.0.93 |
| pyvista | 0.49.0 |
| pyvistaqt | 0.13.1 |
| PySide6 | 6.11.2 |
| numpy | 2.5.3 |
| pytest (dev) | 9.1.1 |
| pyinstaller (dev) | 6.22.3 |

Installing these pulls in 55 packages in total, because each one has its own dependencies (VTK under PyVista, shiboken6 under PySide6, matplotlib under PyVista, and so on).

Two notes on what actually got installed:
- **MediaPipe also installs `opencv-contrib-python` 5.0.0.93.** The project asks for the *headless* build of OpenCV on purpose, because Qt draws everything and a second GUI toolkit would only add weight. MediaPipe requires the regular build as one of its own dependencies, so both end up present. This is harmless — the app only ever uses OpenCV to read camera frames, never its display functions — but it does add to the size of the packaged app.
- **PySide6 6.11.2 is newer than the 6.10 release** that once caused pyvistaqt windows to hang. The project deliberately installs the current version first and only pins an older one if the 3D window actually misbehaves, so that the app isn't held back by a problem it may not have.

### Likely questions
- **Why Python and not a game engine or a web app?** Python has mature libraries for hand tracking, 3D graphics, and math, which let the project focus on the learning experience instead of low-level code.

---

## 2. Code organization: layers

### In plain words
The code is organized like floors in a building: the math is on the ground floor, the window and buttons are near the top, and each floor only relies on the floors below it. This means each part can be tested on its own.

### Technically
From bottom to top: `core` (pure vector math) → `state` (vectors, results, undo, settings) → `gestures` (gesture logic) → `tracking` (camera + MediaPipe) → `render` (3D drawing) → `ui` (window and panels) → `app` (wiring).
- `core` and `gestures` use no camera, graphics, or UI libraries, so they're testable with plain Python.
- **Single source of truth:** vector data exists only in `state`. The 3D view and info panel only display it.
- **One path for all changes:** both the panel and the gestures call the same functions in `state/actions.py`. This is what guarantees every gesture has a panel equivalent and that undo works everywhere.

### How it's implemented
*To be filled in by the agent as the layers are built (G0–G5).*

### Likely questions
- **What does "single source of truth" solve?** If the 3D view and the panel each kept their own copy of the vectors, they could disagree. With one copy, they can't.

---

## 3. Threads: keeping the app smooth

### In plain words
Reading the camera and finding hands takes time. If the app did that while also drawing the 3D scene, everything would stutter. So the camera work happens in a separate background worker, which just sends hand positions to the main part of the app.

### Technically
- **Tracker thread:** reads frames, runs MediaPipe in VIDEO mode, and emits plain hand data through Qt signals. It never touches the UI or the 3D scene, because those libraries aren't thread-safe.
- **Main thread:** everything else: gestures, state, rendering, and panels.
- If MediaPipe is slower than the camera, old frames are dropped rather than queued, so the app always reacts to the hand's *current* position.

### How it's implemented
*To be filled in by the agent after step G4.1.*

### Likely questions
- **What happens if the computer is slow?** Tracking updates less often, but the 3D view and panels stay responsive.

---

## 4. Testing

### In plain words
Most of the app is checked automatically by test programs with answers calculated by hand. The gesture logic is even tested with fake, pre-recorded hand movements, so it can be checked without anyone waving at a camera.

### Technically
- **pytest** tests cover all vector math (including edge cases like the zero vector and vectors along axes), naming and limits, locking, undo, and the gesture state machine.
- Gesture tests feed **synthetic hand-frame sequences** into the state machine and check the intents it outputs.
- Final gesture feel is confirmed by hand with a manual checklist, because thresholds depend on real hands, lighting, and cameras.
- The app was built in small steps, each tested and reviewed before the next began.

### How it's implemented
*To be filled in by the agent as tests are added (G1–G5).*

### Likely questions
- **How do you know the math is right?** Every formula is tested against hand-calculated examples, and identities like cos²α + cos²β + cos²γ = 1 are checked.

---

## 5. Packaging and distribution

### In plain words
Students download a zip, unzip it, and double-click the program. They don't need to install Python or anything else, and it works without internet.

### Technically
- **PyInstaller** bundles Python, the libraries, and the MediaPipe model into a one-folder build, shared as a zip. One-folder builds start faster and trigger fewer antivirus false alarms than single-file builds.
- The model file is located at runtime through a helper that checks PyInstaller's bundle folder, since PyInstaller doesn't include MediaPipe's model files automatically.
- The final build is tested on a Windows machine without Python, with the internet disconnected.

### How it's implemented
*To be filled in by the agent after steps G0.5 and G6.1.*

### Likely questions
- **Why is the download fairly large?** It contains a complete Python runtime, the 3D graphics library, and the machine-learning model.
- **Does it run on Mac?** Not in this version; it was built and tested for Windows only.
