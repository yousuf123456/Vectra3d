# Vectra3D

## [⬇ Download Vectra3D for Windows (setup.exe, 155 MB)](https://github.com/yousuf123456/Vectra3d/releases/latest/download/Vectra3D-0.1.0-setup.exe)

Run the file and follow the steps. No Python and no administrator password are needed. If Windows says "Windows protected your PC", click **More info**, then **Run anyway**: the app is not code-signed. The first launch can take a minute.

---

Vectra3D is a Windows desktop app for first-year university students. It lets you create, move and analyse 3D vectors with your hands through a webcam, while every value updates live. Everything can also be done from the on-screen panels, with no camera.

- **Hand gestures:** pinch and pull to create or resize a vector, pinch and drag to steer it.
- **Exact input:** type components (x, y, z) or magnitude and direction angles (α, β, γ).
- **See the maths:** magnitude, angles, unit vector, components and projections.
- **Operations:** resultant with a head-to-tail animation, and subtraction.

Works offline. Camera images are used only while the app is open and are never saved or sent anywhere by the app. MediaPipe, the hand-tracking library, sends anonymous performance statistics to Google when a network is available.

## Technical details

### Stack

| Part | Used for |
|---|---|
| **Python 3.12**, managed with **uv** | The whole app, with exact versions pinned in `uv.lock` |
| **MediaPipe 1.0** (Tasks API, `GestureRecognizer`) | 21 landmarks per hand for two hands, handedness and built-in gesture labels, in one call |
| **OpenCV** (headless) | Reading webcam frames only; Qt does all the drawing |
| **PyVista / VTK** + **pyvistaqt** | The interactive 3D scene, embedded in the Qt window |
| **PySide6** (Qt 6) | Window, panels, camera strip, dialogs |
| **NumPy** | All vector maths |
| **pytest** | 923 automated tests |
| **PyInstaller** + **Inno Setup** | One-folder Windows build, wrapped in a per-user installer |

### Architecture

The code is in layers, and each layer may only use the ones below it:

```
app       wires everything together
ui        Qt window, info panel, action panel, camera strip
render    draws the scene with PyVista
tracking  camera + MediaPipe, on a background thread
gestures  gesture state machine (pure logic)
state     the vectors, the result, undo history, settings
core      pure vector maths (NumPy only)
```

- **`core` and `gestures` import no Qt, VTK, OpenCV or MediaPipe**, so the maths and the whole gesture engine are tested with pytest alone.
- **One source of truth.** Every change, whether from a typed form or a hand, goes through the same functions in `state/actions.py`. Gestures only output *intents* ("begin create", "update", "commit", "cancel"), which the app turns into actions. That is why every gesture has a panel equivalent and every change can be undone (snapshot-based, last 20 steps).
- **Two threads.** A background `QThread` reads the camera and runs MediaPipe in VIDEO mode, sending plain data to the main thread with Qt signals. All Qt and VTK calls stay on the main thread, because VTK is not thread-safe. If MediaPipe falls behind, frames are dropped rather than queued, so the vector never lags behind the hand.

### From hand to vector

1. **Hand scale.** Distances are measured in *hand-scale units* (wrist to the base of the middle finger), so gestures feel the same whether you sit close to the camera or lean back.
2. **No depth.** A single webcam measures depth poorly, so no gesture relies on moving a hand towards or away from the camera. 3D direction comes from steering instead.
3. **Pinch detection with hysteresis.** A pinch starts when thumb and index tips are closer than 0.25 hand-scale units, and ends above 0.35, so it doesn't flicker on and off when a hand is held still.
4. **Smoothing.** A One Euro filter steadies the landmarks: strong smoothing when the hand is still, little lag when it moves fast.
5. **Gesture state machine:** `IDLE`, `CREATING`, `RESIZING`, `STEERING` and `HOLDING`. A second pinch within 0.5 s makes it a two-hand gesture, and a hand missing for 0.3 s ends the gesture as a release.
   - **Create:** two pinches start together, then pull apart. A full stretch (8 hand-scale units) gives 25 units of length, adjustable from 5 to 50.
   - **Steer:** grab and drag, turning the vector 90° per hand-scale unit. Up and down tilt it round a vertical great circle, so it passes over the pole without reversing; sideways always spins it the same way round the z axis.
   - **Snap:** on release, an angle within 5° of an axis or plane lands exactly on it.
   - **Holds:** MediaPipe's `Pointing_Up`, `Thumb_Up` and `Victory`, held for 0.5 s at 0.6 confidence or more, select the next vector, lock it and show its components.

Every threshold lives in one file, `src/vectra3d/config.py`, and was changed only after testing with real hands.

### The maths

Components, magnitude, direction angles α, β, γ, unit vector, projections on the three planes, resultant (with a head-to-tail animation) and subtraction. Typed angles are checked against cos²α + cos²β + cos²γ = 1. Every function is tested against hand-calculated values, including zero vectors, vectors along the axes and negative components.

### Testing and performance

- **923 tests.** The gesture engine is tested with *synthetic hand data*: scripted sequences of hand frames, such as "two pinches close together, then moving apart over 20 frames", checked against the intents it should output. Final behaviour was then confirmed with real hands against a written checklist.
- **Built for laptops with integrated graphics** (tested on Intel HD Graphics 620). Swapping PyVista's default 8× MSAA for 2× MSAA + FXAA took a scene of thin lines from 37 to 60 fps. While a hand moves a vector, only that vector and its numbers are redrawn, cutting each update from about 300 ms to 48 ms. Hand tracking measured 32 frames per second idle and 21 while steering.

### Packaging

- **One-folder PyInstaller build.** The MediaPipe model is bundled and loaded through one path helper, so the app needs no internet and no Python.
- **Loading window.** It appears within about 2 s, while the heavy libraries load lazily behind it.
- **Inno Setup installer.** It installs per user with no administrator prompt, adds Start menu and desktop shortcuts, and includes an uninstaller.

How each part works, in plain words and in detail, is explained in [`docs/`](docs/).

## For developers

Requires Windows and [uv](https://docs.astral.sh/uv/). Python 3.12 is installed by uv.

```
uv sync                       # install
uv run python -m vectra3d     # run
uv run pytest                 # test
uv run pyinstaller packaging/vectra3d.spec --noconfirm --clean   # build the .exe
```
