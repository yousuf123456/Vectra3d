# Vectra3D — Features

This file lists every feature, its priority, how features are grouped for building and testing, and **acceptance criteria**: the checks that decide whether a feature is done.

- Exact gestures, thresholds, coordinate conventions, and number formatting live in `interaction-spec.md`. This file says *what* each feature does, not the gesture mechanics.
- Every action that can be done by gesture must also be possible from the action panel (see `project-overview.md`).

## Priority legend
- **MVP**: must be built and working before the app is shown to anyone.
- **Post-MVP**: planned only if the student trial is positive. Do NOT build these until instructed.

---

## Build and test rules
These rules apply to every feature and override convenience.

1. **Each feature is built as a separate, self-contained piece.** Its code lives in its own module or clearly separated functions, so it can be tested on its own and changed without breaking other features.
2. **Build by feature group, in order.** Related features are grouped (see the table below). A group is complete only when **every acceptance criterion of every feature in it passes**. Do not start the next group before that.
3. **Test each feature as soon as it is built,** before starting the next feature in the same group. Do not build several features and test them together at the end.
4. **Math is tested without the UI or camera.** All vector math (components, magnitude, angles, unit vector, resultant, subtraction, scaling) must have automated tests with hand-calculated expected values, runnable without opening the app or using a webcam.
5. **Panel first, gestures second.** Every feature that has both a panel and a gesture part is built and tested with the panel first. The gesture part is added later in its own group. This way every feature is proven correct before hand tracking is involved.
6. **No feature may depend on the camera to work.** The app must be fully usable with the webcam off (see F-02).
7. **Record results.** When a feature's criteria pass, mark them `[x]` in this file and note it in `progress-tracker.md`. If a criterion cannot be met, stop and report it instead of changing the criterion.

## Feature groups (build in this order)
The group order is finalized in `build-plan.md`, which adds the tasks for each group.

| Group | Name | Features | How it's tested |
|---|---|---|---|
| G1 | Foundation | F-01, F-04, F-10, F-11 (basic), global vector rules | Manual, with typed vectors. No camera. |
| G2 | Vector math and display | F-05a, F-08, F-09a, F-11 (full), F-12, F-13a, F-14, F-19 (panel) | Automated math tests + manual visual checks. No camera. |
| G3 | Operations | F-15, F-16, F-17, global result rules | Automated math tests + manual visual checks. No camera. |
| G4 | Hand tracking | F-02, F-21 | Manual: webcam, landmarks, and gesture names shown. Does not touch vectors yet. |
| G5 | Gesture control | F-03, F-05b, F-06, F-07, F-09b, F-13b, F-19 (gestures), F-20 | Manual, following the gesture checks in `interaction-spec.md`. |
| G6 | Packaging | F-18 | Run the `.exe` on a Windows machine without Python, offline. |

Features split into **a** (panel part) and **b** (gesture part) are built in different groups, per rule 5.

---

## Global rules for vectors
Built and tested in G1.
- All vectors are position vectors with their tail at the origin. The data model still stores a tail position for each vector (always `(0, 0, 0)` in the MVP) so free vectors can be added later.
- **Maximum 10 vectors** at once.
- **Names** are capital letters assigned automatically in textbook style: A, B, C, … J. A new vector always gets the **lowest free letter**, so deleted letters are reused (if B is deleted, the next new vector is B).
- **Colors** are assigned automatically, one distinct color per vector. No two existing vectors share a color. Vector colors must be clearly different from the reserved component colors (red, green, blue) and the reserved result color.
- The **active vector** is the one gestures and edits act on. It is visibly highlighted in the 3D view and in the info panel.

## Global rules for operation results
Built and tested in G3. Applies to resultant, subtraction, and scalar multiplication.
- A result is **temporary**: it is drawn in a reserved result color that no regular vector uses, and it is labeled with its expression (e.g. `A + B + C`, `A − B`, `2.5·A`).
- Only one temporary result is shown at a time. Running a new operation replaces it.
- A result **updates live** whenever any vector it was computed from changes (by panel or by hand). The change is shown with a subtle, short transition rather than a sudden jump; timing is defined in `interaction-spec.md`.
- If a vector used in the result is deleted, the result disappears.
- Every result has a **Save as vector** button. Saving turns it into a regular vector with the next free letter and color, and it counts toward the 10-vector limit. If the limit is reached, the button is disabled with a clear message.
- The info panel shows the result's components, magnitude, direction angles, and unit vector, same as a regular vector.

---

## MVP features

### F-01 3D scene
**Group:** G1 · **Depends on:** nothing
- [x] x, y, z axes are drawn and labeled, with a visible origin and a reference grid.
- [x] The view can be rotated, zoomed, and panned with the mouse or touchpad.
- [x] A **Reset view** button returns the camera to the default angle.

### F-02 Camera preview and hand feedback
**Group:** G4 · **Depends on:** F-01
- [ ] Shows the mirrored webcam feed with detected hand landmarks drawn on it.
- [ ] Shows the currently recognized gesture by name, or "No hand detected."
- [ ] Shows gesture feedback defined in `interaction-spec.md` (e.g. joystick center and dead zone while steering).
- [ ] If no webcam is found, the app still runs fully from the action panel and shows a clear message instead of crashing.
- [ ] Hand tracking does not freeze or noticeably slow the 3D view or the panels.

### F-03 Create a vector by gesture
**Group:** G5 · **Depends on:** F-02, F-04
- [ ] Performing the create gesture produces a new vector that appears live in the 3D view while the gesture is in progress.
- [ ] Releasing the gesture confirms the vector; it gets the next letter and color and becomes the active vector.
- [ ] If 10 vectors already exist, the gesture does nothing and a message explains the limit.

### F-04 Create a vector by typing
**Group:** G1 · **Depends on:** F-01
- [x] The action panel has an input form with a **toggle** between two modes: components `(x, y, z)` and magnitude + angles.
- [x] Invalid input (empty fields, non-numbers, zero vector) shows an error and creates nothing.
- [x] A valid entry creates a vector exactly matching the typed values, which becomes the active vector.
- [x] If 10 vectors already exist, creation is blocked with a message explaining the limit.

### F-05 Active vector and selection
**F-05a (panel) — Group:** G2 · **Depends on:** F-11
- [ ] Exactly one vector is active at a time (or none, if no vectors exist).
- [ ] The active vector can be changed by clicking it in the info panel.
- [ ] Separately from the active vector, the info panel has a checkbox per vector for **multi-select**, used by the resultant.

**F-05b (gesture) — Group:** G5 · **Depends on:** F-05a, F-02
- [ ] The cycle gesture moves the active vector to the next one, skipping locked vectors.

### F-06 Steer direction by hand
**Group:** G5 · **Depends on:** F-02, F-05a
- [ ] The steering gesture changes the active vector's direction while keeping its magnitude unchanged.
- [ ] Releasing the gesture freezes the vector exactly where it is.
- [ ] Snapping to axes and planes works as defined in `interaction-spec.md`.

### F-07 Resize by hand
**Group:** G5 · **Depends on:** F-02, F-05a
- [ ] The resize gesture changes the active vector's magnitude while keeping its direction unchanged.
- [ ] Releasing the gesture freezes the magnitude.

### F-08 Edit exact values
**Group:** G2 · **Depends on:** F-04, F-05a
- [ ] The action panel can edit the active vector using the same two-mode toggle as F-04.
- [ ] Changes apply immediately and update the 3D view and info panel.
- [ ] Locked vectors cannot be edited; the form is disabled for them.

### F-09 Lock / unlock
**F-09a (panel) — Group:** G2 · **Depends on:** F-05a
- [ ] A vector can be locked or unlocked from the panel.
- [ ] A locked vector ignores all edits, shows a lock indicator in the info panel, and cannot be deleted until unlocked.
- [ ] Locked vectors can still be selected for operations and have their components shown.

**F-09b (gesture) — Group:** G5 · **Depends on:** F-09a, F-02
- [ ] The lock gesture toggles the lock on the active vector.
- [ ] A locked vector ignores all gestures and is skipped when cycling.

### F-10 Delete and clear
**Group:** G1 · **Depends on:** F-04
- [x] Delete removes one vector. Panel only; there is no delete gesture.
- [x] **Clear all** removes every vector, after a confirmation prompt that states locked vectors will also be removed.

### F-11 Information panel
**Basic — Group:** G1 · **Depends on:** F-04
- [x] Lists every vector with: name, color swatch, and components `(x, y, z)`.

**Full — Group:** G2 · **Depends on:** F-11 basic, F-12
- [ ] Adds magnitude, direction angles `(α, β, γ)`, unit vector, and lock status for every vector.
- [ ] Also lists the current temporary result, if any (from G3 onward).
- [ ] Every value updates live whenever a vector changes (by panel now; by hand from G5 onward).

### F-12 Direction angles and unit vector
**Group:** G2 · **Depends on:** F-04
- [ ] α, β, γ (angles with the x, y, and z axes) and the unit vector are computed for every vector and result.
- [ ] Automated tests pass against hand-calculated examples, including vectors lying along each axis.

### F-13 Resolve into components
**F-13a (panel) — Group:** G2 · **Depends on:** F-01, F-05a
- [ ] Can be toggled per vector from the panel.
- [ ] When on, shows the x, y, and z component vectors as arrows along the axes, dashed projection lines, and an outline box showing how the components build the vector.
- [ ] Components always use fixed colors: **x = red, y = green, z = blue**, matching the axis colors.
- [ ] Component values are labeled in the 3D view.
- [ ] Components update whenever the vector changes.

**F-13b (gesture) — Group:** G5 · **Depends on:** F-13a, F-02
- [ ] The components gesture toggles components on the active vector.
- [ ] Components update live while the vector is moved by hand.

### F-14 Plane projections
**Group:** G2 · **Depends on:** F-01, F-05a
- [ ] Can be toggled per vector from the panel.
- [ ] When on, shows the vector's projection ("shadow") on the XY, YZ, and XZ planes.
- [ ] Projections update whenever the vector changes.

### F-15 Resultant
**Group:** G3 · **Depends on:** F-05a, F-11 full
- [ ] With 2 or more vectors checked in the info panel, a **Resultant** button computes their sum.
- [ ] Automated tests pass for sums of 2, 3, and 10 vectors, including vectors that cancel to zero.
- [ ] The result follows the global rules for operation results.
- [ ] A **Show how** button plays a head-to-tail animation: the selected vectors slide into a head-to-tail chain, the resultant is drawn from the origin to the final head, then the vectors return to the origin.
- [ ] The animation does not permanently move or change any vector.

### F-16 Subtraction
**Group:** G3 · **Depends on:** F-05a, F-11 full
- [ ] The panel has two dropdowns forming `[ A ] − [ B ]`, where the student picks each vector.
- [ ] Picking the same vector in both dropdowns is allowed and gives the zero vector with a note.
- [ ] Automated tests pass, including `A − B = −(B − A)`.
- [ ] The result follows the global rules for operation results.

### F-17 Scalar multiplication
**Group:** G3 · **Depends on:** F-05a, F-11 full
- [ ] The panel has a vector dropdown and a number field for the scalar `k`.
- [ ] Negative values are allowed and visibly reverse the direction; `k = 0` gives the zero vector with a note.
- [ ] Automated tests pass for positive, negative, fractional, and zero `k`.
- [ ] The result follows the global rules for operation results.

### F-18 Packaged Windows app
**Group:** G6 · **Depends on:** all MVP features
- [ ] The app builds into a Windows `.exe` that runs on a machine without Python installed.
- [ ] The hand-tracking model is bundled inside; the app works fully with the internet disconnected (tested by disconnecting it).
- [ ] Every acceptance criterion from G1–G5 still passes when run from the `.exe`.

### F-19 Undo / redo
**Undo (panel) — Group:** G2 · **Depends on:** F-04, F-08, F-09a, F-10
Keep this simple: store a snapshot of all vectors before each change. Do not build a complex command system.
- [ ] **Undo** and **Redo** buttons in the panel, plus `Ctrl+Z` and `Ctrl+Y`.
- [ ] Undo covers every change to vectors: create, edit, lock/unlock, delete, clear all, and saving a result as a vector.
- [ ] Undo does not cover camera view changes or toggling display options (components, projections).
- [ ] Keeps the last 20 steps. Making a new change after undoing clears the redo history.

**Undo for gestures — Group:** G5 · **Depends on:** F-19 panel, F-03, F-06, F-07
- [ ] One complete gesture (from grab to release) counts as **one** undo step, not one step per frame.

### F-20 Gesture settings
**Group:** G5 · **Depends on:** F-03, F-06, F-07
- [ ] The action panel has a **Snapping** on/off toggle (default on). Turning it off stops all snapping while steering.
- [ ] The action panel has a **Magnitude sensitivity** setting: how many units a full hand stretch equals, default 25, range 5 to 50 in steps of 5 (see `interaction-spec.md` section 8).
- [ ] Changing sensitivity immediately affects creating and resizing by hand.

### F-21 First-launch privacy notice
**Group:** G4 · **Depends on:** F-02
MediaPipe sends anonymous performance statistics to Google when online (see `architecture.md` section 6). Students must be told.
- [ ] On the first launch, a short plain-language notice appears before the camera starts, stating that: hand tracking runs entirely on the computer; camera images are never saved or sent anywhere; the hand-tracking library sends anonymous performance statistics to Google when the computer is online.
- [ ] The notice is shown once; the app remembers it has been shown using Qt's standard settings storage.
- [ ] The notice can be viewed again at any time from a **Privacy** item in the app's menu or help area.

---

## Post-MVP features (do NOT build until instructed)
Each will be added as its own group, built and tested the same way as the MVP groups.

### P-01 Dot product
Dot product of two vectors, with the angle between them shown as an arc in the 3D view.

### P-02 Cross product
Cross product of two vectors, drawn perpendicular to both, with a visual hint for the right-hand rule.

### P-03 Save / load scenes
Save the current vectors to a file and load them back, so teachers can prepare examples.

### P-04 Free vectors
Vectors whose tail can be placed away from the origin.

### P-05 Guided lab exercises
Tasks for students to complete, with the app checking their answers.

