# Vectra3D — Progress Tracker

Updated after every approved step. Read this at the start of every session to see where things stand.

---

## Current status
- **Current group:** G2 — Vector math and display. G2.1 and G2.2 complete and committed
- **Next step:** UI and rendering pass (raised by the user after G2.2: dated look, awkward view rotation, jagged lines, first-vector delay), then G2.3 — F-11 info panel (full)
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
| G1.2 | F-01 3D scene: `render/scene.py`, toolbar, scene scaling | 2026-09-20 | `G1.2: 3D scene with axes, grid and scene scaling` | All three F-01 criteria pass. Scene runs at ~50 fps after two measured rendering fixes (see `library-docs.md`). The rescale needed `/recover`: the planned "redraw geometry, glide the camera after it" is wrong for an extent-proportional scene and was replaced by a synchronized change. 16 new tests; suite now 67 passing. |
| G1.3 | F-04 create by typing: `core/spherical.py`, `render/vector_actor.py`, `ui/action_panel.py`, splitter layout | 2026-09-21 | `G1.3: create a vector by typing` | All four F-04 criteria pass, the limit message verified through the real panel offscreen. Vectors are drawn in this step, since F-04 cannot be judged without seeing the arrow. Palette and arrow proportions took three rounds of visual feedback. 36 new tests; suite now 103 passing. |
| G1.4 | F-11 info panel (basic): `ui/info_panel.py`, `core/formatting.py` | 2026-09-21 | `G1.4: info panel listing every vector` | One card per vector rather than a table, because F-11 full needs about twelve values per vector in a 300px column. `core/formatting.py` built here rather than at G2.3, since showing components means the section 2.5 display rules apply now. 21 new tests; suite now 124 passing. |
| G1.5 | F-10 delete and clear: `ui/dialogs.py`, delete buttons on cards | 2026-09-21 | `G1.5: delete a vector and clear the scene` | Delete is a button per card, so it acts on the vector being looked at and works before click-to-activate (G2.2). The Clear all prompt states the locked rule now, unconditionally, and defaults to Cancel. 8 new tests; suite now 132 passing. |
| G1 review | `/review` over the whole group, five findings fixed | 2026-09-21 | `G1 review: refuse values that are not numbers, and fix the letter offset` | One critical: `float()` accepts "nan", "inf" and overflowing literals like "1e400", and a nan made the extent search walk the 1-2-5 sequence forever, freezing the window with no error. Refused in the panel now, with the scene sizing raising rather than hanging as a backstop. Also: the letter offset assumed a tail at the origin; the window is now the only thing that listens to the store; two stale comments. 14 new tests; suite now 146 passing. |
| G2.1 | F-12 direction angles and unit vector: `core/vector_math.py` | 2026-09-21 | `G2.1: direction angles and unit vector` | Pure maths, no visible surface until G2.3. Magnitude built here too, since the angles divide by it. 42 new tests; suite now 188 passing. |
| G2.2 | F-05a active vector and selection: click-to-activate, multi-select in `state/store.py` | 2026-09-21 | `G2.2: active vector and multi-select` | Ticks live in the store, not the panel, because the cards are rebuilt on every change. Pruned in `store.remove`/`clear`, so a reused letter cannot inherit a tick. No Qt tests: the panel has no logic of its own, and no existing test opens a window. 18 new tests; suite now 206 passing. |


## Groups

| Group | Name | Status |
|---|---|---|
| G0 | Project setup | Complete — `/review` run, findings fixed |
| G1 | Foundation | Complete — `/review` run, findings fixed |
| G2 | Vector math and display | In progress — G2.1, G2.2 done |
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
| 2026-09-21 | Values that are not finite are refused in `parse_number`, and `extent_for` raises on them rather than searching | Found by `/review`. `float()` accepts "nan", "inf", "-inf" and overflow such as "1e400". A nan freezes the app outright, because every comparison against it is false and the extent search never terminates; an inf returns an infinite extent that then reaches VTK. Stopping them at the one place typed numbers enter satisfies F-04's rule about invalid input, and the check in `extent_for` makes any other route fail loudly instead of hanging. |
| 2026-09-21 | The window is the only thing that subscribes to the store; panels expose a `refresh()` it calls | Found by `/review`: the action panel subscribed for itself while the info panel was driven by the window, leaving two patterns for one job just as G2 adds more panel pieces. One listener also means one order of events. |
| 2026-09-21 | Delete is a button on each card, not a dropdown in the action panel | It acts on the vector the student is looking at, with no selection step, and it works before clicking a vector to make it active arrives in G2.2. The cost is that the info panel is no longer purely a display, which is why it now takes the store. |
| 2026-09-21 | Deleting one vector asks for no confirmation; only Clear all does | F-10 requires a prompt for Clear all alone. One vector is quick to retype, and undo arrives at G2.8. |
| 2026-09-21 | The Clear all prompt states the locked-vector rule now, before locking exists | F-10 requires the prompt to say it, and the wording will still be right when locking lands at G2.5. The alternative was leaving the criterion unmet for four steps. |
| 2026-09-21 | The info panel shows one card per vector rather than a table row | The panel is a 300px column, and by G2.3 each vector has about twelve values: components, magnitude, three direction angles, a unit vector and a lock state. A table would have to scroll sideways to reach them; a card absorbs them. |
| 2026-09-21 | `core/formatting.py` was built at G1.4, ahead of its G2.3 slot in `build-plan.md` | Showing components means `interaction-spec.md` section 2.5 applies now: two decimals and never "-0.00". Writing `f"{v:.2f}"` inline would have duplicated the rule later and shipped the "-0.00" bug in the meantime. G2.3 extends the module for angles rather than starting it. |
| 2026-09-21 | The info panel's card list is rebuilt from scratch on every change | At most ten cards, so working out what moved costs more than rebuilding, and a rebuilt list cannot drift out of step with the store. |
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
| 2026-09-21 | `core/vector_math.py` uses `math.hypot`, `math.acos` and `math.degrees` rather than NumPy | `architecture.md` section 1 gives NumPy all the vector maths, and this step departs from it deliberately. These are three scalars, not an array. `np.linalg.norm` computes `x.dot(x)` and takes a root, so it overflows to infinity for components above roughly 1e154 and underflows to zero below roughly 1e-200, both from finite input the app accepts; `math.hypot` does neither and is correctly rounded, so `hypot(3, 4, 0)` is exactly 5.0 and the hand-calculated tests assert equality rather than approximation. The angles follow it into `math` rather than mixing the two libraries for the same three numbers. NumPy remains the rule wherever the data is genuinely array-shaped, as in `render/scene.py`. |
| 2026-09-21 | The zero vector returns `None` from `direction_angles` and `unit_vector`, not `nan` | `interaction-spec.md` section 2.4 calls the angles and unit vector undefined for the zero vector, and the type `tuple[...] \| None` makes the caller handle that before it can display anything. A `nan` is the other natural answer and was rejected: it looks like a number to everything downstream and surfaces far from its origin, which is exactly the G1 review bug where a typed "nan" reached `extent_for` and hung the window. Raising was rejected too, because the zero vector is an expected state that F-16 produces from `A − B`. |
| 2026-09-21 | The ratio passed to `acos` is clamped into [-1, 1] | A vector on an axis has a true cosine of exactly ±1, the edge of the domain, and floating-point division is not guaranteed to land exactly on it. `math.acos` raises `ValueError` one step outside rather than returning `nan` as `np.arccos` does, so the failure would be a crash on the most ordinary vector a student can type. The clamp cannot mask a real error, since a component over its own magnitude can never legitimately exceed 1. Insurance rather than an observed bug: 500,000 near-axis samples did not produce a ratio above 1. |
| 2026-09-21 | Multi-select lives in `VectorStore`, changed through `toggle_selected` / `clear_selection` | The info panel rebuilds every card on every change (a G1.4 decision), so a tick held in a checkbox would be wiped by any unrelated edit. The store also keeps `architecture.md` section 2's rule that state has one home, and saves G3.2's Resultant button from reaching across into the info panel to find out what is ticked - the panel-to-panel wiring the G1 review removed. |
| 2026-09-21 | Ticks are pruned in `store.remove` and `store.clear`, not in the actions | Letters are reused, so a stale name is not merely untidy: the next vector to take that letter would appear ticked, silently and wrongly. Pruning at the one place a vector actually leaves the store means no future route can reintroduce it. |
| 2026-09-21 | Ticking and activating are fully independent, and ticks are outside undo | F-05a says multi-select is "separately from the active vector", which lets a student tick A and B for a resultant while C stays active to be steered - the case G5 needs. F-19 limits undo to changes to the vectors and excludes display toggles; a tick is the latter. Recorded so G2.8 does not quietly reverse it. |
| 2026-09-21 | G2.2 added no Qt widget tests, against its own approved plan | No existing test opens a `QApplication`: the convention is to lift logic into plain functions and test those, which is why `parse_number` and `card_values` are module level. The panel holds no state and no rules - each card binds a name into a callback - so a Qt-dependent test file would have been a second testing pattern for one job. The widget layer was driven offscreen with a throwaway script instead, confirming all seven behaviours. |


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
| 2026-09-21 | Operations in G3 can produce infinity from finite input: scalar multiplication of a large vector by a large k overflows. Typed input is now guarded, but `core/operations.py` is a second route to the same problem, and `extent_for` will raise rather than hang. Decide at G3.5 what the panel should say. | Open — handle at G3.5 |
| 2026-09-21 | The Clear all prompt says "It cannot be undone", which stops being true when undo arrives at G2.8. Revise the sentence in that step; `tests/ui/test_dialogs.py` asserts it, so the test will not let it be forgotten silently. | Open — revise at G2.8 |
| 2026-09-20 | The scene renders at ~50 fps at 1200x800 on Intel HD Graphics 620, against 60 fps for the single sphere in G0.5. Measured again at G1.3: ten vectors cost almost nothing (47.7 fps empty against 47.2 with all ten), so the cost is the scene itself, not what is drawn in it. Components and projections still have to go on top, and MediaPipe competes for the same chip at G4, where F-02 requires tracking not to slow the view. | Open — monitor at G2.6 and G4 |
| 2026-09-20 | `git push` to the remote fails with HTTP 408 / "Stream error in the HTTP/2 framing layer". Diagnosed as git's HTTP/2 transport on this network; the fix is `git config http.version HTTP/1.1`, not yet applied. Commits are intact locally. | Open — pushing deferred by the user |
