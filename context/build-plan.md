# Vectra3D — Build Plan

The order in which Vectra3D is built, and the workflow for every step. Features are defined in `features.md`; this file says **when** and **how** to build them.

---

## 1. Workflow for every step
Every numbered step in section 4 follows this loop. **Do not skip or merge steps.**

1. **Read** the step's features in `features.md` and the related sections of `interaction-spec.md`, `architecture.md`, `code-standards.md`, and `library-docs.md`.
2. **Check the docs** for every library the step touches (rules in `library-docs.md`).
3. **Plan with `/architect`.** The plan states which files will be created or changed, which library features will be used, and which tests will be written. **Wait for the user's approval before writing any code.**
4. **Build** only what the approved plan covers.
5. **Test.** Run `uv run pytest`; all tests must pass. Then check each acceptance criterion of the step.
6. **Report and stop.** Tell the user what was built, which criteria pass, and exactly what to check by hand (what to click, type, or gesture, and what should happen). **Wait for the user's review.**
7. **After approval:** mark the criteria `[x]` in `features.md`, update `progress-tracker.md`, update the docs (below), and make a Git commit (section 2).

**Updating the docs.** The `docs/` folder explains the app for people (the developer, professors, students). After each approved step:
- Fill in every **How it's implemented** section that names this step: which modules and functions do the work, which library features are used, and any design choice made during the step. Write it clearly for a reader who knows basic Python.
- If the implementation differs from a concept section (a formula, a threshold, a behavior), correct that section and note why.
- Add any genuinely new **Likely questions** the step raises.
- Include the docs changes in the same commit as the code.
8. Move to the next step.

If a criterion cannot be met, or a spec seems wrong, **stop and report it**. Never weaken a criterion, skip a test, or change a tunable value to make something pass.

If the same problem persists after one corrective prompt, **stop and run `/recover`**.

## 2. Git
- Commit after **each approved step**, never before approval and never with failing tests.
- Commit message format: `<step id>: <short description>`, for example `G1.3: create vector by typing` or `G0.3: bundle gesture model`.
- Commit locally only. Pushing to a remote is the user's decision.

## 3. Sessions
- **One Claude Code session per group.** Start a fresh session for each new group.
- **Starting a session:** run `/remember restore`, then read `progress-tracker.md` to see where things stand, then this group's section below.
- **During a group:** if the session gets long before the group is finished, run `/remember save` and continue in a new session with `/remember restore`.
- **Ending a group:**
  1. Run the group checkpoint (listed under each group).
  2. Run `/review` on the group's work and fix anything it finds, following the normal step workflow.
  3. Update `progress-tracker.md` with the status and the next group, and commit.
  4. Run `/remember save`.
  5. Tell the user to start a new session.
- **Before the student trial:** run `/review` on the whole app after G6.

---

## 4. Groups and steps

### G0 — Project setup
**Goal:** an empty app that opens, runs its tests, and already packages correctly, before any feature exists.

| Step | Task | Done when |
|---|---|---|
| G0.1 | Initialize Git with a Python `.gitignore`. Initialize the uv project with Python 3.12 and add the libraries from `architecture.md` section 1. | `uv sync` succeeds; versions are locked in `uv.lock`. |
| G0.2 | Create `paths.py` (`resource_path()` helper) and `config.py` containing every tunable value from `interaction-spec.md` section 9. | Both import cleanly; a test confirms `resource_path()` resolves a file in the project folder. |
| G0.3 | Download the MediaPipe gesture recognizer model from the link in Google's **current official docs** into `assets/models/`. Record the source URL and date in `library-docs.md`. | A small test loads the model through `resource_path()` without errors. |
| G0.4 | **Smoke test:** a main window with an empty, mouse-rotatable 3D view (`architecture.md` section 7). | Window opens, rotates smoothly, closes cleanly. If it hangs, apply the PySide6 fallback in `library-docs.md`. |
| G0.5 | **Packaging smoke test:** build the empty app as a one-folder `.exe` including the model. | The `.exe` opens the window and loads the model. Catching packaging problems now avoids a painful surprise in G6. |

**Don't do yet:** any vectors, panels, or camera code.
**Checkpoint:** all five steps approved and committed.

---

### G1 — Foundation
**Goal:** create, see, list, and delete vectors by typing. No camera.

| Step | Features | Notes |
|---|---|---|
| G1.1 | Global vector rules | `state/models.py`, `naming.py`, `store.py`, `actions.py`. Tests: lowest free letter, distinct colors, 10-vector limit, tail stored at origin. No UI yet. |
| G1.2 | F-01 3D scene | Axes, grid, labels, x/y/z colors, reset view. Scene scaling (`interaction-spec.md` section 3) included here. |
| G1.3 | F-04 Create by typing | Both input modes with the toggle; spherical conversion tested in `core/spherical.py`. |
| G1.4 | F-11 Info panel (basic) | Name, color swatch, components. |
| G1.5 | F-10 Delete and clear | Including the clear-all confirmation. |

**Don't do yet:** selection, editing, locking, components, any operations.
**Checkpoint:** every G1 criterion passes; all tests pass; the user can type three vectors, see them, and delete one.

---

### G2 — Vector math and display
**Goal:** everything about a single vector: its numbers, its parts, and editing it. No camera.

| Step | Features | Notes |
|---|---|---|
| G2.1 | F-12 Direction angles and unit vector | Pure math in `core`, fully tested first, including the zero vector. |
| G2.2 | F-05a Active vector and selection | Click to activate; multi-select checkboxes. |
| G2.3 | F-11 Info panel (full) | Magnitude, α, β, γ, unit vector, lock status. |
| G2.4 | F-08 Edit exact values | |
| G2.5 | F-09a Lock / unlock (panel) | |
| G2.6 | F-13a Resolve into components (panel) | |
| G2.7 | F-14 Plane projections | |
| G2.8 | F-19 Undo / redo (panel) | Snapshot-based, kept simple. |

**Don't do yet:** operations between vectors, camera.
**Checkpoint:** every G2 criterion passes; all tests pass.

---

### G3 — Operations
**Goal:** combining vectors. No camera.

| Step | Features | Notes |
|---|---|---|
| G3.1 | Operation math | `core/operations.py`: resultant, subtraction, scalar multiplication, fully tested before any UI. |
| G3.2 | Global result rules + F-15 Resultant | Temporary result, reserved color, expression label, Save as vector, live updates with transition. |
| G3.3 | F-15 Head-to-tail animation | Separate step: the animation must never change real vector values. |
| G3.4 | F-16 Subtraction | |
| ~~G3.5~~ | ~~F-17 Scalar multiplication~~ | **Dropped 2026-09-23** at the user's decision; F-17 moved to post-MVP as P-06. |

**Don't do yet:** dot or cross product (post-MVP), camera.
**Checkpoint:** every G3 criterion passes; all tests pass. **At this point the entire app works without a camera.**

---

### G4 — Hand tracking
**Goal:** the app sees hands and names gestures, but hands do not affect vectors yet.

| Step | Features | Notes |
|---|---|---|
| G4.1 | F-02 Camera preview | Tracker thread, mirrored preview, landmarks drawn, gesture name shown, no-webcam fallback. The 3D view must stay smooth. |
| G4.2 | F-21 First-launch privacy notice | Shown before the camera starts; viewable again from a Privacy item. |

**Don't do yet:** anything that changes vectors from hand input.
**Checkpoint:** every G4 criterion passes; the user confirms all 3D and panel features still work normally with the camera running.

---

### G5 — Gesture control
**Goal:** connect hands to vectors, following `interaction-spec.md` exactly.

| Step | Features | Notes |
|---|---|---|
| G5.1 | Hand metrics | Hand scale, pinch detection with thresholds, smoothing. Tested with synthetic hand data. |
| G5.2 | Gesture state machine | All states, priority rules, cancel, hand-lost release. Tested with synthetic hand frame sequences; no vectors connected yet. |
| G5.3 | F-03 Create by gesture | Including head/tail choice and the 10-vector limit. |
| G5.4 | F-07 Resize by hand | |
| G5.5 | F-06 Steer by hand | Screen-relative joystick, without snapping. |
| G5.6 | Snapping (part of F-06) | Separate step: snap-in, snap-release, axis priority. |
| G5.7 | F-20 Gesture settings | Snapping toggle and magnitude sensitivity. |
| G5.8 | Hold gestures: F-05b, F-09b, F-13b | Next vector, lock, components, with the progress ring. |
| G5.9 | F-19 Undo for gestures | One gesture = one undo step. |

**Don't do yet:** any gesture not listed in `interaction-spec.md`.
**Checkpoint:** every G5 criterion passes, and the user completes the full manual checklist in `interaction-spec.md` section 11. Record any tuning changes in `progress-tracker.md`.

---

### G6 — Packaging
**Goal:** the finished app, ready for students.

| Step | Features | Notes |
|---|---|---|
| G6.1 | F-18 Build | One-folder `.exe` with the model bundled, zipped for sharing. |
| G6.2 | F-18 Verification | On a Windows machine **without Python**: run the `.exe` with the internet **disconnected**, and recheck every G1–G5 criterion. |

**Checkpoint:** the MVP is complete. Update `progress-tracker.md` and stop. **Post-MVP features are not started until the user asks**, after the student trial.

---

## 5. After the MVP
Post-MVP features (`features.md` P-01 to P-05) are each added later as a new group with its own steps, following the same workflow. They are not planned in detail until the user decides to continue.
