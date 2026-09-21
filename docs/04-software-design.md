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

**Picking vectors (G2.2).** The store remembers two different marks, and keeping them apart matters. The **active** vector is the single one that edits and hand gestures act on; it is tinted in the panel and haloed in the 3D view. The **ticked** vectors are a separate set, possibly empty, marking which ones an operation such as the resultant should use. Clicking a card's body sets the active one; clicking its tick box changes the other. Neither affects the other, so a student can tick A and B to add them while keeping C active to steer by hand.

The ticks are kept in the store rather than in the checkboxes, which looks roundabout until you notice that the card list is rebuilt from scratch every time anything changes. A tick living in a checkbox would vanish the moment an unrelated vector was created. They are also cleared the instant a vector leaves the store, because letters are reused: without that, deleting a ticked B and creating a new one would hand the newcomer a tick it never earned.

**Editing a vector (G2.4).** Below **New vector** sits a second form, **Edit vector A**, which changes the active vector rather than making another one. Two separate boxes rather than one form with a mode: the same filled-in fields meaning two different things is how a student ends up creating an eleventh vector when they meant to change one.

Both boxes are the same widget, `VectorForm`, so the toggle between components and magnitude + angles, and the rules for reading the fields, exist once. The edit fields are filled from the active vector at two decimals, matching the card beside them, and pressing **Apply** — or Enter in any field — replaces that vector's components. It keeps its letter, its colour, its tail and its lock state; only what it points at changes.

The fields are refilled only when the vector they are showing actually changes, never on every store event. This matters more than it sounds: any change at all notifies every listener, so refilling unconditionally would wipe a half-typed number the moment an unrelated card was ticked. From G5 the same rule keeps a vector steered by hand from leaving stale numbers in the form that **Apply** would quietly put back.

A locked vector is refused in two places — the form is greyed out, and `actions.edit_vector` refuses it regardless. The second is the one that counts: in G5 the gesture engine reaches the same function, and a rule kept only in the widget would have to be written again there.

**Room for the vectors (G2.4 UI fix).** Two stacked forms took 498px of an 800px window, leaving room for two of the ten cards. Three fixes: each form's three fields share one row instead of three, the error line is hidden until there is an error, and either box can be folded away by clicking its title. Open, the list now gets three cards; fold one form and it gets four, both and it gets six.

The panels used to share a splitter, which had to go for the folding to do anything. A splitter hands out the sizes it was last given and does not ask again when a child shrinks — so folding a form freed nothing, the box just shrank and left the gap behind as padding. A plain layout re-reads what each side needs, which gives the action panel exactly the height of its forms and the vector list everything that remains.

`state/actions.py` holds the changes themselves — creating, editing, deleting, and clearing vectors, choosing the active one, and ticking and unticking. The store stores; the actions decide what is allowed. Each action makes all of its changes and then notifies listeners exactly once, so nothing ever redraws a half-finished change. Creating an eleventh vector is refused: the action returns nothing and the panel shows the limit message.

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
*Filled in as tests are added (G1–G5).*

Tests live in `tests/`, mirroring the layer they cover, and run with `uv run pytest`.

- `tests/test_paths.py`, `tests/test_config.py`, `tests/test_model_asset.py` (G0) check that bundled files are found both from source and from inside the packaged `.exe`, that every tunable value is present, and that the MediaPipe model really loads.
- `tests/state/` (G1.1) covers the vector rules: that names are handed out lowest-first and reused after a deletion, that the ten colors are all different and none of them reads as an axis color, that the eleventh vector is refused, that every new vector stores its tail at the origin, and that each action reports exactly one change.

- `tests/render/` (G1.2) covers the scene's sizing rules: the 1-2-5 sequence, that a value exactly on the boundary still fits, that the world never shrinks below 10, and that the largest component decides the size.

The state tests need no window and no camera, which is the point of keeping Qt out of that layer. The scene tests cover its arithmetic only — whether a grid reads clearly is a question no test can answer, so that part is checked by eye.

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
*Packaging was set up and proven in step G0.5, before any feature existed, so that packaging problems would surface while the app was still small enough to debug easily. The G6.1 notes will be added when the final build is made.*

The build is described by `packaging/vectra3d.spec` and run with:

```
uv run pyinstaller packaging/vectra3d.spec --noconfirm
```

The result is `dist/vectra3d/`, containing `vectra3d.exe` alongside its
libraries and data. At the G0.5 stage it was 972 files and 0.66 GB, which will
grow as the app gains features.

Two parts of that file are doing real work:

- **`collect_all("mediapipe")`.** PyInstaller works out what to include by
  following `import` statements, which finds Python code but not data. MediaPipe
  ships machine-learning models and graph definitions (`.tflite`, `.binarypb`)
  that no import mentions, so without this they are silently left out and the
  app fails only when hand tracking first runs. `collect_all` returns MediaPipe's
  data files, its compiled libraries, and its submodules, and all three are
  passed to the build.
- **The model's destination path.** The gesture recognizer model is added as
  `("../assets/models/gesture_recognizer.task", "assets/models")`, so inside the
  packaged app it sits at the same relative path it has in the project. That is
  what allows `paths.resource_path()` to work without knowing which mode it is
  in: it swaps the project folder for PyInstaller's unpack folder and everything
  below that point is identical.

**How the packaged app was checked.** At this stage the app had no camera code,
so nothing in it loaded the model yet. Rather than adding code the app did not
need, `app.py` gained a `--check-model` option: running
`vectra3d.exe --check-model` resolves the model path, builds a real MediaPipe
gesture recognizer from it, prints what happened, and exits. It reported the
path as `dist/vectra3d/_internal/assets/models/gesture_recognizer.task` —
PyInstaller's own unpack folder, confirming the packaged path was being used
rather than the project folder — and created the recognizer successfully. The
same option is used again in G6.2 to verify the app on a computer with no
Python and no internet connection.

The bundled model was also compared against the original by checksum, since a
file that is copied but truncated would pass a simple "is it there?" check.

**One setting is temporary.** `console=True` keeps a terminal window open behind
the app, so that a failure at startup prints an error instead of the window
silently never appearing. G6.1 turns this off for the version students receive.

### Likely questions
- **Why is the download fairly large?** It contains a complete Python runtime, the 3D graphics library, and the machine-learning model.
- **Does it run on Mac?** Not in this version; it was built and tested for Windows only.
