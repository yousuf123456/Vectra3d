# Vectra3D — Library Docs

Training data is wrong about parts of this stack. These libraries change often, and most tutorials and forum examples are outdated. This file records the rules for checking documentation, the version rules, and every known correction. **Entries here override memory and old examples.**

---

## 1. Documentation rules
- **Fetch the current official docs the first time you touch a library in a session.** Once per library per session, not per edit.
- Prefer, in order: the library's official docs, its official examples, then its GitHub repository and release notes. Never rely on memory, old tutorials, or forum code.
- Check against the version **actually installed in `uv.lock`**, not just the newest version online.
- If no documentation tool is available, say so rather than working from memory.
- If fetched docs contradict this file, **stop and ask.** Some entries here were decided deliberately.
- When a doc lookup reveals something important (an API change, a gotcha, a fix), add it to section 4 of this file so later sessions don't repeat the search.

---

## 2. Version rules
- **Python 3.12.** MediaPipe's package lists support up to 3.12. Do not use 3.13 or newer.
- Install the latest compatible versions, then run the smoke test (`build-plan.md` G0.4). Once it passes, the versions in `uv.lock` are frozen. **Do not upgrade any library without being asked.**
- **PySide6 fallback:** pyvistaqt has had compatibility problems with some PySide6 releases (a window hang with PySide6 6.10 was reported in February 2026 and later closed). If the 3D window hangs or does not respond, pin PySide6 below 6.10 and record it in section 4.

---

## 3. Known corrections by library

### MediaPipe (1.0.x)
- **Never use `mp.solutions`** (`mp.solutions.hands`, `mp.solutions.drawing_utils`, etc.). It was removed from current MediaPipe. Almost every tutorial uses it, and that code **will not run**. Use only the Tasks API: `from mediapipe.tasks.python import vision`.
- Use `GestureRecognizer`, which returns landmarks, handedness, and built-in gesture labels in one call.
- Run it in **VIDEO mode** (`recognize_for_video`) with increasing millisecond timestamps, called synchronously inside the tracker thread.
- `drawing_utils` is gone, so draw landmarks on the preview yourself (simple circles and lines).
- MediaPipe expects **RGB**; OpenCV gives **BGR**. Convert before recognition.
- Mirror the frame **before** recognition, so landmark positions match the mirrored preview.
- Image coordinates: x grows right, **y grows down**.
- The app does not use MediaPipe's left/right handedness labels.
- MediaPipe Tasks sends performance and usage metrics to Google when online (see `architecture.md` section 6). This is disclosed in the first-launch notice; do not try to disable it without being asked.

### Model file and PyInstaller
- The `gesture_recognizer.task` model is downloaded **once during setup** from the link in Google's current official docs, into `assets/models/`, and committed. The app never downloads it at runtime.
- **Always load it through `paths.resource_path()`.** The helper checks PyInstaller's `sys._MEIPASS` folder when running as an `.exe`, and the project folder otherwise. PyInstaller does not include `.task` files automatically.
- PyInstaller needs `--collect-all mediapipe`, plus the model added as data. On Windows the `--add-data` separator is `;`, not `:`.
- Build **one-folder**, not one-file.

### PyVista, pyvistaqt, and PySide6
- Embed the 3D view with `pyvistaqt.QtInteractor` inside the main window. Do not use `BackgroundPlotter`, which opens its own separate window.
- **Never call PyVista, VTK, or Qt widget methods from the tracker thread.** They are not thread-safe. The tracker thread only emits signals carrying plain data.

### OpenCV
- Use `opencv-python-headless`. Qt handles all display.
- On Windows, if opening the camera is slow, try the DirectShow backend (`cv2.CAP_DSHOW`).
- The app must start and work fully when no camera is available.

---

## 4. Findings log
Add verified findings here: date, library and version, what was found, and the source link.

| Date | Library | Finding | Source |
|---|---|---|---|
| 2026-09-20 | mediapipe 1.0.1 | MediaPipe depends on `opencv-contrib-python` (5.0.0.93), so the non-headless OpenCV is installed alongside `opencv-python-headless` and cannot be avoided by our own dependency choices. Harmless (the app never calls OpenCV display functions) but adds ~51 MB to the packaged app. Relevant at G6. | Observed during `uv add` resolution; `uv.lock`. |
| 2026-09-20 | PySide6 6.11.2 | Installed latest rather than pinning below 6.10 pre-emptively, per section 2. Whether the pyvistaqt hang applies to 6.11.2 is unknown until the G0.4 smoke test. | Section 2 of this file. |
| 2026-09-20 | mediapipe 1.0.1 | **Gesture recognizer model source.** Downloaded `gesture_recognizer.task` (float16, the only variant Google offers) and committed it to `assets/models/`. Size 8,373,440 bytes. SHA256 `97952348CF6A6A4915C2EA1496B4B37EBABC50CBBF80571435643C455F2B0482`. The URL contains `/latest/`, so the file behind it can change without notice; compare this checksum before trusting any re-download. | https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/latest/gesture_recognizer.task (linked from https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer, fetched 2026-09-20) |
| 2026-09-20 | mediapipe 1.0.1 | **Docs confirm this file's existing entries.** Tasks API only, VIDEO mode via `recognize_for_video` with millisecond timestamps, and `mp.Image(image_format=mp.ImageFormat.SRGB, data=<numpy array>)` for frames. Loading is `GestureRecognizerOptions(base_options=BaseOptions(model_asset_path=...), running_mode=VisionRunningMode.VIDEO)` then `GestureRecognizer.create_from_options(...)`. Results carry gestures, handedness, hand_landmarks (21 per hand, normalized 0-1) and world landmarks. No contradictions found. | https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer/python (fetched 2026-09-20) |
| 2026-09-20 | mediapipe 1.0.1 | **Canned gesture labels match `interaction-spec.md` section 7 exactly**: Unknown, Closed_Fist, Open_Palm, Pointing_Up, Thumb_Down, Thumb_Up, Victory, ILoveYou. The spec uses Pointing_Up, Thumb_Up and Victory, cancels on Open_Palm, and leaves the rest unused. No custom classifier is needed. | Same page as above. |
| 2026-09-20 | pytest | Loading the model makes the test suite take ~9 s instead of ~0.2 s. Only `tests/test_model_asset.py` touches MediaPipe; if the suite ever needs to be fast, deselect that file rather than weakening it. | Observed. |
| 2026-09-20 | pyvistaqt 0.13.1 / PySide6 6.11.2 | **The PySide6 fallback in section 2 is NOT needed.** The window opens, rotates and closes cleanly on 6.11.2, exit code 0, no hang. The pin below 6.10 stays unused unless a later step shows a problem. | Verified on this machine, G0.4. |
| 2026-09-20 | pyvistaqt 0.13.1 | **`QT_API` must be set before importing pyvistaqt.** pyvistaqt reaches Qt through qtpy, which chooses a binding at import time from the environment. `app.py` sets `os.environ.setdefault("QT_API", "pyside6")` above its imports; the `# noqa: E402` comments there mark that the import order is deliberate. | http://qt.pyvista.org/usage.html (fetched 2026-09-20) |
| 2026-09-20 | pyvista 0.49.0 | **PyVista's 8x multisampling default halves the frame rate on integrated graphics.** Measured on Intel HD Graphics 620 at 1200x749 with one sphere: 8x MSAA 33.1 fps, 4x 42.0, 2x 50.0, none 60.1. FXAA at `multi_samples=0` also measured 60.1 fps, so it is effectively free. The window therefore passes `multi_samples=0` to `QtInteractor` and calls `enable_anti_aliasing("fxaa")`. Set it per plotter, not through `pv.global_theme`, which is global mutable state. | Measured, G0.4. |
| 2026-09-20 | pyvista 0.49.0 | **The corner orientation widget (`add_axes()`) does not move or scale with pan and zoom.** It is drawn in its own fixed viewport and only reflects camera orientation. In an otherwise empty scene this makes working pan and zoom look broken, because nothing on screen responds. Confirmed by logging the camera: zoom changed the camera distance 3.35 -> 1.07 -> 12.71 and pan moved the focal point, while the view appeared static. | Diagnosed in G0.4. |
| 2026-09-20 | PySide6 6.11.2 | `int(event.modifiers())` raises `TypeError` on a `KeyboardModifier`. Use `event.modifiers().value` or compare against the flag directly. Cost a wasted diagnostic run. | Observed, G0.4. |
| 2026-09-20 | PyInstaller 6.22.3 | **One-folder build works first try** with `collect_all("mediapipe")` plus the model as its own `datas` entry. Output: 972 files, 0.66 GB. PyVista, VTK and PySide6 needed no `collect_all` of their own; nothing was added pre-emptively. | Built and run, G0.5. |
| 2026-09-20 | PyInstaller 6.22.3 | **In 6.x, one-folder builds put bundled data in `dist/<name>/_internal/`, and `sys._MEIPASS` points there** - not at the folder holding the .exe. `paths.resource_path()` handles this correctly because it reads `_MEIPASS` rather than assuming a layout. Confirmed live: the packaged app reported `dist/vectra3d/_internal/assets/models/gesture_recognizer.task`. | Observed, G0.5. |
| 2026-09-20 | pyvista 0.49.0 | **FXAA alone is not enough for thin lines.** After dropping to `multi_samples=0` + FXAA the axes looked jagged at shallow angles. Final setting is `multi_samples=2` + FXAA + `line_smoothing=True`, measured at 60 fps against a grid-of-lines scene - the same as FXAA alone, so the quality gain is free. 4x MSAA was the next step up but cost a third of the frame rate (47 fps). | Measured against a line-heavy scene, G0.5. |
| 2026-09-20 | uv 0.12.17 | `uv add` fails with "Failed to extract archive ... network timeout" on the large wheels (PySide6 addons is 160 MB) with the default 30 s `UV_HTTP_TIMEOUT`. Set `UV_HTTP_TIMEOUT=300` before installing on a slow connection. | uv error message; reproduced on this machine. |
