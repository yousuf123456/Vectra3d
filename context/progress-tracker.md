# Vectra3D — Progress Tracker

Updated after every approved step. Read this at the start of every session to see where things stand.

---

## Current status
- **Current group:** G1 — Foundation, in progress
- **Next step:** G1.4 — F-11 info panel, basic (name, color swatch, components)
- **Blocked on:** nothing

## Completed steps

| Step | Description | Date | Commit | Notes |
|---|---|---|---|---|
| G0.1 | Initialize Git and uv project | 2026-09-20 | `G0.1: initialize git and uv project` | Python 3.12.14. Own repo rooted at the project folder, nested inside the Desktop-level repo; remote `github.com/yousuf123456/Vectra3d` (public). `uv sync` succeeds, 55 packages installed. |
| G0.2 | `paths.py` (`resource_path()`) and `config.py` (all section 9 tunables + section 8 defaults) | 2026-09-20 | `G0.2: add resource_path helper and config values` | Added a hatchling build system so `src/vectra3d` installs editable and is importable. 8 pytest tests pass, including a monkeypatched `sys._MEIPASS` test of the PyInstaller branch. |
| G0.3 | Bundle the MediaPipe gesture recognizer model | 2026-09-20 | `G0.3: bundle gesture recognizer model` | float16 bundle, 8,373,440 bytes, SHA256 recorded in `library-docs.md`. Test builds a real `GestureRecognizer` in VIDEO mode, not just a file-exists check. Suite now ~9 s. |
| G0.4 | Window and 3D view smoke test | 2026-09-20 | `G0.4: window with embedded 3D view` | Opens, rotates, closes cleanly (exit 0). PySide6 6.11.2 works; the section 2 fallback pin is not needed. Anti-aliasing changed from 8x MSAA to FXAA after measuring, roughly doubling the frame rate. User's verdict on rotation: "not super smooth but acceptable". |
| G0.5 | Packaging smoke test | 2026-09-20 | `G0.5: package as a one-folder exe` | One-folder build, 972 files / 0.66 GB. `vectra3d.exe --check-model` loads the model from `_internal`, proving the `sys._MEIPASS` branch on a real build. Anti-aliasing raised to 2x MSAA + FXAA + line smoothing after the axes looked jagged; measured as free. |
| G1.1 | Global vector rules: `state/models.py`, `naming.py`, `store.py`, `actions.py` | 2026-09-20 | `G1.1: global vector rules` | Frozen `Vector` keyed by letter; color derived from the letter; plain-callback change events, so `state` needs no Qt. 39 new tests; suite now 51 passing. No UI. |
| G1.3 | F-04 create by typing: `core/spherical.py`, `render/vector_actor.py`, `ui/action_panel.py`, splitter layout | 2026-09-21 | `G1.3: create a vector by typing` | All four F-04 criteria pass, the limit message verified through the real panel offscreen. Vectors are drawn in this step, since F-04 cannot be judged without seeing the arrow. Palette and arrow proportions took three rounds of visual feedback. 36 new tests; suite now 103 passing. |
| G1.2 | F-01 3D scene: `render/scene.py`, toolbar, scene scaling | 2026-09-20 | `G1.2: 3D scene with axes, grid and scene scaling` | All three F-01 criteria pass. Scene runs at ~50 fps after two measured rendering fixes (see `library-docs.md`). The rescale needed `/recover`: the planned "redraw geometry, glide the camera after it" is wrong for an extent-proportional scene and was replaced by a synchronized change. 16 new tests; suite now 67 passing. |

## Groups

| Group | Name | Status |
|---|---|---|
| G0 | Project setup | Complete — `/review` run, findings fixed |
| G1 | Foundation | In progress — G1.1 done |
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
| 2026-09-20 | Added a hatchling `[build-system]` in G0.2 rather than a pytest `pythonpath` setting | An editable install fixes imports once for tests, `python -m vectra3d` (G0.4), and PyInstaller (G0.5), instead of needing a separate path workaround in each. |
| 2026-09-20 | `config.py` also holds the section 8 user-setting defaults, in a separate block | `code-standards.md` section 3 bans magic numbers, and the sensitivity default and range are exactly that. The live values still belong to `Settings` in `state/`. |
| 2026-09-20 | `test_config.py` asserts relationships between tunables, not their exact literals | The spec allows re-tuning after real hand testing. Tests repeating each literal would have to be edited on every legitimate change, which is the habit `code-standards.md` section 4 forbids. |
| 2026-09-20 | The 3D view uses `multi_samples=2` + FXAA + line smoothing, rather than PyVista's default 8x MSAA | Measured on the target hardware (Intel HD Graphics 620) against a scene of thin lines: 8x MSAA 37 fps, this combination 60 fps. An earlier attempt at `multi_samples=0` + FXAA hit the same 60 fps but left the axes visibly jagged, so 2x was added back at no measurable cost. F-02 requires hand tracking not to slow the 3D view, so the headroom matters. |
| 2026-09-20 | `app.py` has a `--check-model` option | The app had no camera code when packaging was first proven, so nothing loaded the model. This verifies the bundled model from the .exe without adding code the app does not otherwise need, and G6.2 reuses it on a machine with no Python and no internet. |
| 2026-09-21 | The ten vector colors were rebuilt twice, ending with a maximum-contrast set rather than hues chosen by hand | Excluding red, green and blue leaves a narrow band, and the first palette put two olives and two teals in it. The second separated same-family pairs (orange/brown, teal/cyan) by lightness and the user still found them hard to tell apart. The third takes colors from a set designed for mutual contrast and keeps only those clear of the axis colors, so no two share a family. Judged on screen with all ten drawn at once. |
| 2026-09-21 | The active vector is shown with a translucent halo, not extra thickness | `interaction-spec.md` section 10 allows "thicker, with a glow or outline". Thickness was built first and the user asked for something else. It was also the weaker choice: thickness would mean two things at once from G2.6, when component arrows arrive. |
| 2026-09-21 | Arrow proportions are fractions of each vector's own length, not of the scene extent | A vector then looks the same shape whether it is 3 units or 300, and a short vector is a small arrow rather than a stubby barrel in a large world. Final values after three rounds of visual feedback: shaft 0.007, tip radius 0.018, tip length 0.060 - much slimmer than PyVista's defaults, which look like pipes beside one-pixel axis lines. |
| 2026-09-21 | Typed input is checked when Create is pressed, not keystroke by keystroke | F-04 requires invalid input to show an error, which needs a message rather than a refused keystroke: someone typing `3,5` is told to use a dot. Qt's documentation site returned only its navigation shell when `QDoubleValidator`'s locale behaviour was checked, and `library-docs.md` forbids working from memory, so Python's own `float()` was used, which has one unambiguous rule. |
| 2026-09-21 | The parsing rules live in module-level functions in `ui/action_panel.py`, apart from the widgets | They are what F-04's criteria are actually about, and this way they are tested without opening a window. |
| 2026-09-20 | The scene rescales geometry and camera in the same frame, with no animation | Everything in the scene is a fraction of the extent, including the camera distance, so they are one thing. The approved plan moved them separately and the result was visibly wrong: the world was ten times too big for 300 ms, the origin dot filled the view and the grid flew off screen. Changed together the grid lines land in nearly the same pixels and only the axis numbers change, which is calmer than any animation would have been. Diagnosed with `/recover` and approved by the user. |
| 2026-09-20 | `SCENE_RESCALE_MS` stays in `config.py` although nothing now uses it | It is an `interaction-spec.md` section 9 value. Deleting a spec value to match an implementation is the habit `code-standards.md` forbids. It returns if the animated rescale is ever picked up; otherwise section 9 and `config.py` need a deliberate joint edit. **Open decision.** |
| 2026-09-20 | Axis numbers use `pv.Label` billboards rather than `add_point_labels` | `add_point_labels` more than halved the frame rate on its overlap-avoidance pass. The numbers are spaced far enough apart not to overlap, so nothing is lost. Measured; see `library-docs.md`. |
| 2026-09-20 | Scene layout constants (grid divisions, camera direction, arrow sizes) live in `render/scene.py`, not `config.py` | `config.py` holds the values `interaction-spec.md` section 9 marks tunable after hand testing, where every change must be recorded. Grid spacing is layout, not feel, and does not need that ceremony. |
| 2026-09-20 | `state` reports changes with plain Python callbacks (`store.subscribe`), not Qt signals | `code-standards.md` only bans Qt in `core` and `gestures`, so Qt here would have been legal, but every state test would then need a `QApplication`. Callbacks keep the layer testable with pytest alone; `ui` wraps them in a Qt signal where it needs one. |
| 2026-09-20 | `Vector` is a frozen dataclass storing tuples, keyed in the store by its letter | Immutability makes G2.8's snapshot undo a dictionary copy instead of a deep copy, and makes it impossible to change a vector outside `actions.py`. NumPy arrives in G2.1 with the math that needs it; G1.1 only stores values. |
| 2026-09-20 | Vector color is derived from the letter, not stored on the vector | Letters and colors are both "lowest free", so deriving one from the other makes them a single piece of bookkeeping. A reused letter also returns in its familiar color. |
| 2026-09-20 | `create_vector` accepts a zero vector; only typed input rejects it | F-04 rejects a typed zero vector, but F-16 lets `A − B` be zero and still be saved as a vector. The rule belongs to the input form, not to the store. |
| 2026-09-20 | Deleting the active vector activates the first remaining vector by letter | `features.md` does not specify what happens next. First-by-letter is predictable and matches the info panel's order. Approved by the user at G1.1. |
| 2026-09-20 | `locked` was not added to `Vector` in G1.1 | `code-standards.md` section 1 says build only what the step needs. F-09a (G2.5) adds the field and the "locked vectors cannot be deleted" guard together, where both can be tested. |
| 2026-09-20 | The model-loading test calls `app.check_model()` instead of loading the model itself | `/review` found the same MediaPipe setup written twice, which would let the test drift from what the app actually does once G4 changes the options. The test now exercises the shipped code path. |
| 2026-09-20 | `main()` takes an optional `argv` and rejects unrecognised arguments with exit code 2 | `/review` found that a mistyped option opened the window instead of reporting an error - the wrong feedback when verifying a packaged build, which is exactly what G6.2 uses `--check-model` for. The parameter also makes the behaviour testable without opening a window. |

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
| 2026-09-20 | `app.py`'s `check_model()` constructs a MediaPipe `GestureRecognizer` directly, but `architecture.md` section 2 puts MediaPipe in the `tracking` layer. Nothing is inverted (`app` sits above `tracking`), and the duplication was removed by having the tests call `check_model()` rather than repeat the loading code. **Decide in G4**, when `tracking/tracker_thread.py` exists, whether `check_model()` should delegate to it. | Open — decide at G4 |
| 2026-09-20 | 3D view performance is adequate but not generous on Intel HD Graphics 620: ~56 fps with one sphere, and the user describes rotation as "not super smooth but acceptable". Worth re-checking when the camera thread is added, because F-02 requires hand tracking not to slow the 3D view. | Open — monitor at G4 |
| 2026-09-20 | ~~The ten vector colors have not been seen against anything.~~ Checked at G1.3 with all ten drawn at once; the palette was rebuilt twice and approved. | Closed — 2026-09-21 |
| 2026-09-20 | The scene renders at ~50 fps at 1200x800 on Intel HD Graphics 620, against 60 fps for the single sphere in G0.5. Measured again at G1.3: ten vectors cost almost nothing (47.7 fps empty against 47.2 with all ten), so the cost is the scene itself, not what is drawn in it. Components and projections still have to go on top, and MediaPipe competes for the same chip at G4, where F-02 requires tracking not to slow the view. | Open — monitor at G2.6 and G4 |
| 2026-09-20 | `git push` to the remote fails with HTTP 408 / "Stream error in the HTTP/2 framing layer". Diagnosed as git's HTTP/2 transport on this network; the fix is `git config http.version HTTP/1.1`, not yet applied. Commits are intact locally. | Open — pushing deferred by the user |
