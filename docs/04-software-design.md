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
| Math | NumPy, and Python's own `math` | Array work goes to NumPy; the per-vector arithmetic uses `math`, for the reason below |
| Tests | pytest | Standard Python testing tool |
| Environment | uv | Installs the right Python version and locks exact library versions |
| Packaging | PyInstaller | Turns the app into a Windows program that doesn't need Python |

### How it's implemented
**Why some maths avoids NumPy.** The table above credits NumPy with the vector maths, and that is still the rule wherever the data is genuinely an array. But a single vector here is three numbers, not an array, and for three numbers Python's own `math` module is both simpler and more accurate at the extremes. `core/vector_math.py` uses `math.hypot` for magnitude because NumPy's `linalg.norm` squares the components first and so overflows to infinity for very large vectors (G2.1), and `core/operations.py` adds with `math.fsum` so that a resultant does not depend on the order its vectors were added in (G3.1). Both departures are deliberate and are explained in the modules themselves.

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
*Filled in as each layer is built. `state` was built in step G1.1; `core`, `gestures`, `tracking` and `render` will be added here as they arrive.*

**`state` (G1.1).** `state/store.py` holds a `VectorStore`: the vectors, keyed by their letter, and which one is active. One store is created when the app starts and passed to the parts that need it. It reports every change to listeners that registered with `subscribe()` — plain Python callables, not Qt signals, so the whole layer can be tested without starting an application. The window wraps a listener around a Qt signal where it needs one.

A change event carries no detail: it simply says "something changed, read me again". With at most ten vectors there is nothing to gain from describing the change, and a listener that re-reads the store cannot drift out of step with it.

**`ui` (G1.3–G1.5).** The window is a 3D view on the left and two panels on the right, with a splitter between the view and the panels so either can be given more room. `ui/action_panel.py` is where vectors are typed and where **Clear all** lives; `ui/info_panel.py` lists what exists, one card per vector; `ui/dialogs.py` holds the prompts that ask before something irreversible.

Each card shows about a dozen values in a 300px column, which is why the panel is a list of cards rather than a table: a table would have to scroll sideways to reach them. A card is two pairs of columns — what the vector *is* on the left, its components and length; which way it *points* on the right, its three direction angles and unit vector. The header, with the tick box and the delete button, is laid out separately from that table. It used to share one grid with it, and the stretch that pushes the delete button to the right edge was stretching a column of the numbers underneath too, which left every angle stranded away from its value.

The panels never touch vector data directly. They call `state/actions.py` and then wait to be told the store changed, exactly as the gesture engine will from G5. That is what keeps the two ways of working in step: there is no path through the panel that gestures cannot also take, and no order of events where the 3D view and the panel disagree.

Deleting a vector is the one change the info panel makes, and it is a button on the card rather than a list to pick from, so the thing being removed is the thing being looked at. **Clear all** asks first, warns that locked vectors go too, and defaults to Cancel, so a stray press of Enter keeps the student's work. There is deliberately no delete gesture at all (see `03-gestures-and-interaction.md`).

**`ui/theme.py` (UI pass).** One palette and spacing scale for the whole application, applied once before the window is built. The panels are themed by `qdarktheme`, a small library that sets an application-wide Qt stylesheet; the light variant is used, because the app is meant to survive being projected in a lecture and because the ten vector colours were chosen against a light scene. Anything the app colours for itself — the tint on the active vector's card, the card borders, the 3D background — is defined here rather than in the widget that draws it, so the hand-picked colours and the theme agree instead of clashing.

**`render` (G1.2).** `render/scene.py` draws the world the vectors live in — grid, axes, origin — and resizes it to fit them. It holds no vector data: the window subscribes it to the store, and it is handed the vectors to draw to. The camera's default angle and the **Reset view** toolbar button live here too.

Two choices here came from measuring rather than from reading. PyVista's `add_point_labels` is the obvious way to put numbers on the axes and it cost more than half the frame rate, because it runs a pass to stop labels overlapping; `pv.Label` billboards draw the same thirty numbers for free. A wireframe plane is the obvious way to draw a grid and it was the most expensive thing in the scene, because a wireframe draws all four edges of each of its four hundred squares; the forty-two lines actually wanted cost a fraction of that. Both are recorded in `context/library-docs.md`.

**`render/overlays.py` (G2.6).** What a vector is *made of*, drawn separately from the vector itself because the two are switched on and off independently. It owns its actors by name and replaces them in place, the same way `render/vector_actor.py` does, so switching from one vector to another cannot leave the first one's arrows behind. `01-vector-math.md` section 2 explains the geometry and the three rounds it took to make the arrows readable. The same file holds `ProjectionOverlays` (G2.7) for the shadows on the three planes — a second class rather than more branches in the first, because the two overlays are switched on and off separately and neither should have to know whether the other is showing.

**Picking vectors (G2.2).** The store remembers two different marks, and keeping them apart matters. The **active** vector is the single one that edits and hand gestures act on; it is tinted in the panel and haloed in the 3D view. The **ticked** vectors are a separate set, possibly empty, marking which ones an operation such as the resultant should use. Clicking a card's body sets the active one; clicking its tick box changes the other. Neither affects the other, so a student can tick A and B to add them while keeping C active to steer by hand.

The ticks are kept in the store rather than in the checkboxes, which looks roundabout until you notice that the card list is rebuilt from scratch every time anything changes. A tick living in a checkbox would vanish the moment an unrelated vector was created. They are also cleared the instant a vector leaves the store, because letters are reused: without that, deleting a ticked B and creating a new one would hand the newcomer a tick it never earned.

**Editing a vector (G2.4).** Below **New vector** sits a second form, **Edit vector A**, which changes the active vector rather than making another one. Two separate boxes rather than one form with a mode: the same filled-in fields meaning two different things is how a student ends up creating an eleventh vector when they meant to change one.

Both boxes are the same widget, `VectorForm`, so the toggle between components and magnitude + angles, and the rules for reading the fields, exist once. The edit fields are filled from the active vector at two decimals, matching the card beside them, and pressing **Apply** — or Enter in any field — replaces that vector's components. It keeps its letter, its colour, its tail and its lock state; only what it points at changes.

The fields are refilled only when the vector they are showing actually changes, never on every store event. This matters more than it sounds: any change at all notifies every listener, so refilling unconditionally would wipe a half-typed number the moment an unrelated card was ticked. From G5 the same rule keeps a vector steered by hand from leaving stale numbers in the form that **Apply** would quietly put back.

A locked vector is refused in two places — the form is greyed out, and `actions.edit_vector` refuses it regardless. The second is the one that counts: in G5 the gesture engine reaches the same function, and a rule kept only in the widget would have to be written again there.

**Room for the vectors (G2.4 UI fix).** Two stacked forms took 498px of an 800px window, leaving room for two of the ten cards. Three fixes: each form's three fields share one row instead of three, the error line is hidden until there is an error, and either box can be folded away by clicking its title. Open, the list now gets three cards; fold one form and it gets four, both and it gets six.

The panels used to share a splitter, which had to go for the folding to do anything. A splitter hands out the sizes it was last given and does not ask again when a child shrinks — so folding a form freed nothing, the box just shrank and left the gap behind as padding. A plain layout re-reads what each side needs, which gives the action panel exactly the height of its forms and the vector list everything that remains.

**Locking (G2.5).** Each card carries a lock control beside its ✕. It reads **Lock** in muted grey while the vector is free, and **Locked** in the accent colour while it is not. A locked vector keeps its components, refuses to be deleted on its own, and greys out both the edit form and its own ✕ — each with a line saying why and pointing at the control that lifts it. Everything else still works on it: it can be the active vector, it can be ticked for an operation, and it shows every one of its numbers, because locking is about protecting a vector rather than setting it aside.

**Clear all** is the deliberate exception: it takes locked vectors too, and its prompt has said so since it was written. Protecting a vector from a single stray ✕ is a different question from what happens when a student asks to empty the scene, and the prompt is where that is made clear.

The control started as a padlock, 🔒 and 🔓, and had to be rewritten as words: Windows draws emoji as colour bitmaps, so they ignore the colour and weight the two states were relying on, and at that size the two padlocks were not tellable apart. Text obeys both.

`state/actions.py` holds the changes themselves — creating, editing, locking, deleting, and clearing vectors, choosing the active one, and ticking and unticking. The store stores; the actions decide what is allowed. Each action makes all of its changes and then notifies listeners exactly once, so nothing ever redraws a half-finished change. Creating an eleventh vector is refused: the action returns nothing and the panel shows the limit message.

### Likely questions
- **What does "single source of truth" solve?** If the 3D view and the panel each kept their own copy of the vectors, they could disagree. With one copy, they can't.
- **Why is the ticked set not the same as the active vector?** They answer different questions. "Which vector am I shaping right now?" has exactly one answer; "which vectors go into this sum?" has any number. Merging them would make it impossible to add two vectors while working on a third.

---

## 3. Threads: keeping the app smooth

### In plain words
Reading the camera and finding hands takes time. If the app did that while also drawing the 3D scene, everything would stutter. So the camera work happens in a separate background worker, which just sends hand positions to the main part of the app.

### Technically
- **Tracker thread:** reads frames, runs MediaPipe in VIDEO mode, and emits plain hand data through Qt signals. It never touches the UI or the 3D scene, because those libraries aren't thread-safe.
- **Main thread:** everything else: gestures, state, rendering, and panels.
- If MediaPipe is slower than the camera, old frames are dropped rather than queued, so the app always reacts to the hand's *current* position.

### How it's implemented
Built in G4.1.

- `TrackerThread` (`tracking/tracker_thread.py`) is a `QThread` whose `run()` method is the loop itself. The other common Qt pattern — a worker object moved onto a thread — was not used, because it relies on the thread's own event loop, which a loop that never stops would never let run.
- It talks to the rest of the app through three Qt signals: `frame_ready` (the picture and a `HandFrame`), `camera_unavailable` and `camera_lost`. A signal emitted on one thread and connected to a widget on another is **queued** by Qt and delivered on the widget's thread, which is what makes it safe for the preview to draw what the tracker sends. A test sends real frames from a real thread to a real preview widget to prove the connection works, because Qt silently swallows an error raised inside a slot.
- **Frames are dropped, not queued**, in two places. The loop reads, recognizes and sends in order, so a frame that arrives while one is being recognized is simply never read. And the preview keeps only the latest picture: if several arrive before the window next repaints, Qt merges the repaint requests and only the last is drawn.
- The window owns the tracker and starts it with `start_camera()`, called from `app.py` once the window is showing. It is a separate call so tests can build a window without opening a camera. Closing the window stops the thread and waits for it before the 3D view shuts down.
- No camera, or a camera that stops sending pictures, ends the thread and puts a plain message in the preview; everything else carries on.

**What it costs.** Measured on the target laptop (Intel HD Graphics 620) with ten vectors and the view rotating continuously, camera off and on in alternation: about 54 fps without the camera and 47 with it, an 11-13% drop. Almost all of that is MediaPipe itself competing for the processor — with recognition replaced by a stub the drop disappears — and painting the preview costs about 1 ms a picture. Recognition takes about 16 ms per frame with no hands in view and about 35 ms with hands, whether the picture is 640x480 or 320x240. The drop is above the 10% line set for F-02 and is carried into G5 to be measured again under full gesture load.

One effect runs the other way. While the 3D view is redrawing continuously — as it does while being dragged with the mouse — the tracker slows from about 30 frames a second to about 10. The likely cause is that VTK holds Python's global lock while it draws, so the tracker thread waits for it. This matters in G5, when steering redraws the view on every frame.

**Screen space.** Adding the preview strip exposed an older fault: with all three form boxes open, the right-hand column made the window's minimum height 830px, taller than the 728px a common 1366x768 laptop has free, so the window grew off the bottom of the screen. The forms now sit in a `FittedScrollArea` (`ui/fitted_scroll_area.py`) that asks for exactly its contents' height and scrolls only when there is not room; the vector list keeps at least 300px, about two cards; and the window opens maximized when its default size does not fit.

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
*Filled in as tests are added (G1–G5).*

Tests live in `tests/`, mirroring the layer they cover, and run with `uv run pytest`.

- `tests/test_paths.py`, `tests/test_config.py`, `tests/test_model_asset.py` (G0) check that bundled files are found both from source and from inside the packaged `.exe`, that every tunable value is present, and that the MediaPipe model really loads.
- `tests/state/` (G1.1) covers the vector rules: that names are handed out lowest-first and reused after a deletion, that the ten colors are all different and none of them reads as an axis color, that the eleventh vector is refused, that every new vector stores its tail at the origin, and that each action reports exactly one change.

- `tests/render/` (G1.2) covers the scene's sizing rules: the 1-2-5 sequence, that a value exactly on the boundary still fits, that the world never shrinks below 10, and that the largest component decides the size.

- `tests/tracking/` (G4.1) runs the tracker thread against a **fake camera** that produces black pictures, with the real MediaPipe recognizer: pictures arrive and stopping releases the camera, a missing camera is reported, and a camera that stops sending is reported and released. It also checks the conversion from MediaPipe's result to plain hand data using fake results, and that timestamps always increase. `tests/ui/test_camera_preview.py` checks the plain-word gesture names against every label in the bundled model, and reads the drawn picture back pixel by pixel to confirm the image and a hand point land where they should. `tests/ui/test_fitted_scroll_area.py` checks that the forms can never again set the window's minimum height, and that folding a box frees its space — a test confirmed to fail when the part that makes folding work is removed.

The state tests need no window and no camera, which is the point of keeping Qt out of that layer. The scene tests cover its arithmetic only — whether a grid reads clearly is a question no test can answer, so that part is checked by eye.

### Likely questions
- **How do you know the math is right?** Every formula is tested against hand-calculated examples, and identities like cos²α + cos²β + cos²γ = 1 are checked.

---

## 5. Packaging and distribution

### In plain words
Students download one setup file and run it. It puts Vectra3D in their Start menu, without asking for an administrator password. They don't need to install Python or anything else, and it works without internet. A zip of the same app is kept as a fallback for computers that block installers.

### Technically
- **PyInstaller** bundles Python, the libraries, and the MediaPipe model into a one-folder build, shared as a zip. One-folder builds start faster and trigger fewer antivirus false alarms than single-file builds.
- The model file is located at runtime through a helper that checks PyInstaller's bundle folder, since PyInstaller doesn't include MediaPipe's model files automatically.
- **Inno Setup** turns that folder into a per-user installer with Start menu and desktop shortcuts and an uninstaller.
- A small loading window appears about two seconds after launch, because loading the 3D engine and hand tracking takes far longer and nothing else is on screen meanwhile.
- The final build is tested on a Windows machine without Python, with the internet disconnected.

### How it's implemented
Packaging was set up and proven in step G0.5, before any feature existed, so that packaging problems would surface while the app was still small enough to debug easily. The final build was made in step G6.1; the loading window and the installer were added in G6.1b, after testing on a second laptop.

The build is described by `packaging/vectra3d.spec`, run and zipped with:

```
uv run pyinstaller packaging/vectra3d.spec --noconfirm --clean
uv run python -m zipfile -c dist/Vectra3D-0.1.0-windows.zip dist/Vectra3D
```

The result is `dist/Vectra3D/`, containing `Vectra3D.exe` alongside its
libraries and data in `_internal/`: 1,031 files and 681 MB at G6.1 (972 files
and 0.66 GB at G0.5). The zip students receive is 247 MB and unpacks to a
single `Vectra3D` folder. The zip is made with Python's own `zipfile` module,
so building the shareable file needs no extra tool.

Three parts of that file are doing real work:

- **`collect_all("mediapipe")`.** PyInstaller works out what to include by
  following `import` statements, which finds Python code but not data. MediaPipe
  ships machine-learning models and graph definitions (`.tflite`, `.binarypb`)
  that no import mentions, so without this they are silently left out and the
  app fails only when hand tracking first runs. `collect_all` returns MediaPipe's
  data files, its compiled libraries, and its submodules, and all three are
  passed to the build.
- **`collect_all("qdarktheme")`.** The theme draws checkbox ticks and dropdown
  arrows from `.svg` files that its stylesheet names by path, which PyInstaller
  cannot see either. Without them only the packaged app would lose those marks.
  Checked in the packaged app at G6.1.
- **The model's destination path.** The gesture recognizer model is added as
  `("../assets/models/gesture_recognizer.task", "assets/models")`, so inside the
  packaged app it sits at the same relative path it has in the project. That is
  what allows `paths.resource_path()` to work without knowing which mode it is
  in: it swaps the project folder for PyInstaller's unpack folder and everything
  below that point is identical. The app icon, `assets/icons/vectra3d.ico`, is
  bundled the same way.

**The icon** is set twice, because Windows asks for it in two places. `icon=` on
the spec's `EXE` puts it on the `.exe` file itself, which Explorer shows. The
running app then sets it on its window with `QApplication.setWindowIcon`, loaded
through `resource_path()`, which is what the title bar and taskbar show. The
`.ico` holds seven sizes from 16 to 256 pixels, made from a transparent PNG
(`assets/icons/vectra3d.png`, kept as the source) using Qt alone, so Windows
picks a sharp image at every size rather than shrinking one large one.

**No terminal window.** The build is "windowed" (`console=False`), so students
see only the app. G0.5 kept a terminal open behind it while packaging was being
proven, so that a startup failure would print something. Two things replace it:

- A crash at startup still shows its error, in a dialog, because PyInstaller's
  windowed traceback is deliberately left on.
- A windowed program has no terminal to print to, which would have silenced
  the `--check-model` option below. Its output still arrives when it is piped,
  and piping also makes PowerShell wait for the program to finish:

  ```
  .\Vectra3D.exe --check-model | Out-String
  ```

**How the packaged app is checked.** `app.py` has a `--check-model` option:
it resolves the model path, builds a real MediaPipe gesture recognizer from it,
prints what happened, and exits with 0 on success or 1 on failure. At G0.5,
when the app had no camera code, it reported the path as
`dist/vectra3d/_internal/assets/models/gesture_recognizer.task` —
PyInstaller's own unpack folder, confirming the packaged path was being used
rather than the project folder. At G6.1 the zip was unpacked into an unrelated
folder and the check run from there, proving the shared file works on its own
and not only the build folder. The same option is used again in G6.2 to verify
the app on a computer with no Python and no internet connection.

The bundled model was also compared against the original by checksum, since a
file that is copied but truncated would pass a simple "is it there?" check.

**The first launch is slower.** PyVista brings in matplotlib, which builds a
font cache in the user's own folder the first time it runs on a computer. It
happens once per computer, and has nothing to do with the camera: no picture is
ever saved.

**The loading window** (G6.1b). On the second laptop the app looked dead
for its first half-minute: importing the libraries takes about 25 seconds on
the development laptop (`python -X importtime`: hand tracking - MediaPipe and
OpenCV - about 11 s, the 3D engine about 11 s), and the window could not
appear before all of them had loaded. `app.py` now imports only Qt and light
modules at the top, shows `LoadingSplash` (`ui/splash.py`, a `QSplashScreen`
drawn on a pixmap: icon, name, and a status line), and only then imports the
slow modules one stage at a time, in `LOADING_STAGES`, saying which is loading.
The splash closes when the main window is shown. Measured from the installed
app, warm: splash at 2.2 s, main window at 6.3 s. A test starts a fresh Python
and checks that importing `vectra3d.app` loads none of PyVista, VTK, MediaPipe
or OpenCV, which is the property everything else depends on. PyInstaller's own
splash screen was considered and not used: it is marked experimental, its docs
warn of problems in one-folder builds, and it would bundle Tcl/Tk, a second GUI
toolkit.

**The installer** (G6.1b). `packaging/vectra3d.iss` is an Inno Setup script,
compiled on the development machine only (Inno Setup is never shipped):

```
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" packaging\vectra3d.iss
```

It packs the whole `dist/Vectra3D` folder into `dist/Vectra3D-0.1.0-setup.exe`,
155 MB against 236 MB for the zip. `PrivilegesRequired=lowest` makes it a
per-user install with no administrator prompt - students on lab or university
laptops usually cannot approve one - so the default folder is the student's own
`%LOCALAPPDATA%\Programs\Vectra3D`, which they can change. It adds Start menu
entries for the app and the note, an optional desktop shortcut, an uninstaller
under Settings > Apps, and offers to launch the app at the end. Checked on the
development laptop (install, launch, clean close, uninstall leaving nothing
behind) and on the second laptop. Its fixed `AppId` must never change: Windows
uses it to recognise an upgrade and find the uninstaller.

**Read me first.** `packaging/Read me first.txt` goes beside `Vectra3D.exe`,
copied there by the spec after the build (PyInstaller 6 puts `datas` in
`_internal`). It tells students what would otherwise look like faults: the
SmartScreen warning on the unsigned installer ("More info", then "Run anyway"),
that starting takes a while, allowing the camera, and that everything works
from the panels without one. Tests check its wording, that the build still
copies it, and that the installer's version matches `pyproject.toml`.

**Verifying a build.** `packaging/verification-checklist.md` is the guided
session for every build given out: install on a laptop that has never had
Python, internet off, then recheck every G1-G5 criterion, once with the camera
and once with it disabled in Device Manager.

### Likely questions
- **Windows says "Windows protected your PC". Is the app unsafe?** No. The installer is not code-signed, so Windows does not recognise it yet. Click "More info", then "Run anyway".
- **Why a loading window instead of a faster start?** Most of the wait is loading the 3D engine and the hand-tracking model, which the app needs before it can show anything. The loading window makes the wait visible; it does not make it shorter.
- **Why is the download fairly large?** It contains a complete Python runtime, the 3D graphics library, and the machine-learning model.
- **Does it run on Mac?** Not in this version; it was built and tested for Windows only.
- **Why does the app take longer to open the very first time?** A plotting library that the 3D view depends on prepares its list of fonts once per computer. Later launches skip it.
- **Can I move `Vectra3D.exe` onto the desktop on its own?** No. It needs the `_internal` folder next to it. The installer puts a shortcut on the desktop if you tick the box; with the zip, keep the whole `Vectra3D` folder together and make a shortcut.
