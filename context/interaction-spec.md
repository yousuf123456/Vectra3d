# Vectra3D — Interaction Spec

This file defines exactly how Vectra3D behaves: coordinate and math conventions, number display, scene scaling, and every hand gesture. When code and this file disagree, this file wins. If something here seems wrong or impossible, stop and report it rather than inventing a different behavior.

- *What* each feature does is in `features.md`. This file defines *how* it behaves.
- All numbers marked **(tunable)** are starting values collected in the table in section 9. They may only be changed after real testing, and every change must be recorded in `progress-tracker.md`.

---

## 1. Usage setup
- One person, sitting or standing at a laptop, using the built-in webcam or a desk webcam.
- Up to **2 hands** are tracked. Either hand can perform every gesture; there is no dominant hand.
- The camera preview is **mirrored**, like a selfie camera: moving the right hand to the right moves it right on screen.

---

## 2. Coordinate system and math conventions

### 2.1 Axes
- **Right-handed** coordinate system, **z points up**.
- Default view looks at the origin from a raised front-right position, so x, y, and z are all clearly visible.
- Axis colors: **x = red, y = green, z = blue.** The same colors are used for component vectors.

### 2.2 Vectors
- Every vector is a position vector with its tail at the origin (the data model still stores a tail, always `(0, 0, 0)` in the MVP).
- All math is done in full floating-point precision. Rounding happens **only** when values are displayed.

### 2.3 Spherical angles (for "magnitude + angles" input and display)
Physics convention:
- **r**: magnitude, must be greater than 0.
- **θ (theta)**: angle from the **+z axis**, from 0° to 180°.
- **φ (phi)**: angle in the **XY plane**, measured from the **+x axis toward +y** (counterclockwise when seen from above). Any typed value is normalized into 0° to 360°.

Conversion:
```
x = r · sin θ · cos φ
y = r · sin θ · sin φ
z = r · cos θ
```
Along the z axis (θ = 0° or 180°), φ is undefined; display it as `—` and treat typed φ as irrelevant.

### 2.4 Direction angles and unit vector
- α, β, γ are the angles between the vector and the +x, +y, +z axes:
  `α = arccos(x / |v|)`, `β = arccos(y / |v|)`, `γ = arccos(z / |v|)`
- Unit vector: `v / |v|`.
- For the **zero vector**, magnitude is 0 and all angles and the unit vector are undefined; display them as `—` with the note "zero vector has no direction."

### 2.5 Number display
- **Angles in degrees**, shown with the `°` symbol.
- **2 decimal places** for every displayed value.
- Never display `-0.00`; show `0.00`.

---

## 3. Scene scale
- The scene starts with axes and grid from **−10 to 10**.
- The scene extent follows this sequence: **10 → 20 → 50 → 100 → 200 → 500 → 1000**, and so on (1, 2, 5 pattern).
- **Growing:** if any vector or the current result has a component whose absolute value exceeds the current extent, the extent grows to the smallest step in the sequence that fits everything.
- **Shrinking:** if everything fits within a smaller step, the extent shrinks back to it, down to a minimum of 10.
- **When rescaling happens:** only after a gesture is released, a typed value is applied, a vector is deleted or cleared, or an undo/redo. **Never while a vector is being moved by hand.**
- Rescaling is a smooth camera and grid transition (tunable duration), not a jump.

---

## 4. Hand tracking basics

### 4.1 Hand scale (makes the app work at any distance)
- Hands look larger when closer to the camera. To compensate, every distance in this spec is measured in **hand-scale units (hs)**.
- **1 hs = distance from the wrist (landmark 0) to the base of the middle finger (landmark 9)** in the camera image, for that hand.
- For two-hand measurements, use the average hand scale of both hands.

### 4.2 Pinch
- The pinch point is the midpoint between the thumb tip (landmark 4) and index fingertip (landmark 8).
- **Pinch starts** when the thumb–index distance falls below **0.25 hs** (tunable).
- **Pinch ends** when it rises above **0.35 hs** (tunable).
- The gap between these two values prevents flickering between pinched and not pinched.

### 4.3 Smoothing
- Landmark positions are smoothed before use to remove shake. Use a One Euro filter (preferred, because it smooths strongly when the hand is still but reacts quickly when it moves) or, if that proves problematic, an exponential moving average. Parameters are tunable (section 9); the starting values are the filter authors' own defaults, and β starts at 0 as their tuning procedure prescribes.

### 4.4 Losing the hand
- If a hand involved in an active gesture is lost for more than **0.3 s** (tunable), the gesture ends as a normal **release**: the vector keeps its current state and one undo step is recorded. It is not treated as a cancel.

---

## 5. Gesture state machine
Only one gesture is active at a time.

| State | Entered when | Ends when |
|---|---|---|
| IDLE | Nothing is happening | — |
| CREATING | Both hands pinch, starting close together | Either pinch ends |
| RESIZING | Both hands pinch, starting apart | Either pinch ends |
| STEERING | One hand pinches, the other does not | The pinch ends, or cancel |
| HOLDING | A hold gesture (section 7) is recognized while IDLE | It triggers, or the hand shape changes |

**Priority rules**
- Two-hand pinch beats one-hand pinch. If a second hand pinches within **0.5 s** (tunable; started at 0.3) of the first, it is a two-hand gesture; otherwise the first hand starts STEERING once the window has passed, and a later second pinch is ignored until STEERING ends. The steering anchor is still the pinch point at the moment the first pinch began.
- A gesture starts only when a pinch **begins**. A pinch still held when a gesture ends, or a second pinch that was ignored, starts nothing until that hand lets go and pinches again.
- Hold gestures are only recognized in IDLE. They are ignored during any pinch gesture, and a pinch beginning during HOLDING abandons the hold.

**Release**
- Letting go of a pinch ends the gesture and commits it **at once**.

**Cancel (Open_Palm) — steering only**
- While STEERING, an open palm from the **free hand** cancels the gesture at once. The vector returns exactly to its state before the gesture started. No undo step is recorded.
- Only the free hand counts, and only while it is not pinching. The steering hand opens as it lets go, and a pinch with the other fingers stretched out is often classified as `Open_Palm`; both cancelled gestures at random in real testing (G5.2, G5.3).
- CREATING and RESIZING **cannot be cancelled**. Both hands are pinching, so a palm could only come from a hand that has just let go, and a hand letting go opens naturally and is read as `Open_Palm` - so a palm after a release says nothing about what the student meant. A create or resize is taken back with **Undo** instead, which removes the whole gesture in one step; a create released with almost no pull creates nothing (section 6.2).
- Open palm in IDLE does nothing.
- (Amended 2026-09-25, G5.3. The G5.2 version waited a 0.3 s release confirm window after every pinch gesture and let an open palm in it cancel; real testing showed ordinary releases being cancelled, because the releasing hand itself reads as an open palm. The confirm window was removed.)

**Undo**
- One complete gesture, from start to release, is recorded as **one** undo step. Cancelled gestures record nothing.

**Locked vectors**
- If the active vector is locked, RESIZING and STEERING do nothing and the preview shows "Vector A is locked." CREATING still works, because it makes a new vector.

---

## 6. Pinch gestures

### 6.1 Screen-relative directions
All hand directions are relative to the screen as the student currently sees it, whatever the 3D view's rotation:
- Hand moving right in the (mirrored) preview = the camera's **right** direction in the 3D world.
- Hand moving up in the preview = the camera's **up** direction in the 3D world.
- Note: image y grows downward, so it must be inverted.

These camera directions are read from the 3D view's camera at the moment they are needed.

### 6.2 Create a vector
1. Both hands pinch (within the two-hand window, section 5) with the pinch points closer than **1.0 hs** (tunable). This enters CREATING.
2. As the hands pull apart, a new vector is drawn live:
   - **Direction:** the line between the two pinch points, converted to 3D using screen-relative directions (6.1). The vector therefore starts parallel to the screen; the student steers it afterwards to add depth.
   - **Head and tail:** the head is at the hand that has moved more since the pinch started (the "pulling" hand); the hand that moved less is the tail end. This lets students pull in any direction with either hand. If both hands have moved equally (within 10%, tunable), the head is at the hand on the right of the screen. The head/tail choice is re-evaluated live during CREATING, so it settles as soon as one hand clearly leads.
   - **Magnitude:** `(current distance − starting distance) ÷ full stretch × sensitivity`, where **full stretch = 8 hs** (tunable) and **sensitivity** is the user setting in section 8 (default 25 units).
3. Releasing either pinch confirms the vector. It gets the next letter and color and becomes active. Scene rescaling then applies.
4. If the magnitude on release is below **0.1** (tunable), nothing is created.
5. If 10 vectors already exist, entering CREATING shows the limit message and nothing is drawn.

### 6.3 Resize the active vector
1. Both hands pinch with pinch points **1.0 hs or more** apart. This enters RESIZING on the active vector.
2. Direction stays fixed. Magnitude changes by the same rate as creation: `new magnitude = starting magnitude + (current distance − starting distance) ÷ full stretch × sensitivity`.
3. Magnitude never drops below **0.1** (tunable) while resizing.
4. Releasing either pinch confirms. Scene rescaling then applies.

### 6.4 Steer the active vector (joystick)
1. One hand pinches, the other does not. The pinch point at that moment becomes the **anchor**.
2. The offset from the anchor, in hs, is the joystick deflection.
3. Inside the **dead zone** of **0.3 hs** (tunable), nothing moves.
4. Beyond it, the vector rotates at a speed that grows with distance, up to a **maximum of 90° per second** (tunable) at **1.5 hs** (tunable) or more.
5. Rotation is screen-relative:
   - Horizontal deflection rotates the vector around the camera's **up** direction (the head swings left or right on screen).
   - Vertical deflection rotates the vector around the camera's **right** direction (the head tilts up or down on screen).
   - The sense is **globe-style**: the side of the vector nearest the viewer moves the way the hand moves. A vector lying flat on the screen therefore tips into or out of it, which is how steering adds depth (section 6.2). (Settled at G5.5, 2026-09-25.)
   - The speed rises in a straight line from 0 at the dead zone's edge to the maximum at the full-speed deflection, and is timed from the frames' own timestamps.
6. Magnitude never changes while steering.
7. Releasing the pinch freezes the vector.

### 6.5 Snapping (while steering)
- When the vector comes within **5°** (tunable) of an axis (±x, ±y, ±z) or within **5°** of lying in a coordinate plane (XY, YZ, XZ), it snaps exactly onto it.
- It stays snapped until the steering pushes it more than **8°** (tunable) away, so it doesn't flicker at the boundary.
- Axis snaps take priority over plane snaps.
- **Snap lock.** While snapped, steering turns the vector *within* the plane it lies in (or, on an axis, within one of the two planes containing it), whatever the view's rotation, instead of about the screen's axes. For a plane, the hand direction whose screen axis is closer to the plane's normal spins the vector inside it (sideways for the floor seen from above; up/down for the YZ plane seen edge-on from the front), and the other direction tilts it out until it releases. On an axis, the normal closer to the screen's up takes sideways and the other takes up/down. The globe-style sense of 6.4 is kept. (Added 2026-09-25, G5.6, at the user's decision: in the raised default view a purely sideways push turned the vector about a tilted axis and dropped it out of the XY plane.)
- On arriving at a snap, steering continues from the snapped direction, so the full release angle is needed to leave it. Leaving an axis along one of its planes does not count as a snap engaging (no flash).
- Snapping is **on by default** and can be turned off in settings (section 8).

---

## 7. Hold gestures
Recognized with MediaPipe's built-in gesture classifier.

| Gesture (MediaPipe label) | Action |
|---|---|
| `Pointing_Up` | Make the next vector active, skipping locked vectors. If all are locked, show a message. |
| `Thumb_Up` | Lock / unlock the active vector. |
| `Victory` | Show / hide components on the active vector. |

Rules:
- The gesture must be recognized continuously for **0.5 s** with confidence of at least **0.6** (tunable) before it triggers.
- It triggers **once**. To trigger again, the hand must first change to a different shape.
- A progress ring in the camera preview fills during the hold, so the student sees it coming.
- If no vector exists, hold gestures show a short message and do nothing.
- `Thumb_Down`, `Closed_Fist`, and `ILoveYou` are unused in the MVP.

---

## 8. User settings
Available in the action panel:
- **Snapping:** on / off. Default: on.
- **Magnitude sensitivity:** how many units a full hand stretch equals, for creating and resizing. Default: **25 units**. Range: **5 to 50** in steps of 5. Lower values give finer control over small vectors; higher values make large vectors quicker to reach.

---

## 9. Tunable values
Starting values. Change only after real testing, and record every change in `progress-tracker.md`.

| Value | Start | Section |
|---|---|---|
| Pinch start threshold | 0.25 hs | 4.2 |
| Pinch end threshold | 0.35 hs | 4.2 |
| Smoothing minimum cutoff | 1.0 Hz | 4.3 |
| Smoothing speed coefficient (β) | 0.0 | 4.3 |
| Smoothing derivative cutoff | 1.0 Hz | 4.3 |
| Hand-lost timeout | 0.3 s | 4.4 |
| Two-hand pinch window | **0.5 s** (was 0.3; see `progress-tracker.md`) | 5 |
| "Hands together" distance for create | 1.0 hs | 6.2 |
| Full stretch | 8 hs | 6.2 |
| Minimum magnitude | 0.1 | 6.2, 6.3 |
| Equal-movement margin for head choice | 10% | 6.2 |
| Steering dead zone | 0.3 hs | 6.4 |
| Steering max speed | 90°/s | 6.4 |
| Deflection for max speed | 1.5 hs | 6.4 |
| Snap-in angle | 5° | 6.5 |
| Snap-release angle | 8° | 6.5 |
| Hold duration | 0.5 s | 7 |
| Hold confidence | 0.6 | 7 |
| Live result transition | 150 ms | 10 |
| Scene rescale transition | 300 ms | 3 |
| Head-to-tail animation (slide / draw / pause / return) | 1.0 / 0.5 / **1.5** / 0.5 s | 10 |

---

## 10. Visual feedback and animation
- **Active vector:** highlighted (thicker, with a glow or outline) in the 3D view and in the info panel.
- **During CREATING / RESIZING:** the live magnitude is shown next to the vector's head.
- **During STEERING:** the camera preview shows the anchor point, the dead zone ring, and a line to the current pinch point.
- **Angles of the active vector:** the 3D view always shows the active vector's θ and φ as arcs from their axes - θ from +z to the vector, φ in the XY plane from +x round to the vector's shadow - each arc tagged with its own letter (θ, φ), and their values shown as one line beside the vector's head, under its letter, changing live while a hand moves it. The arcs are thin and half transparent so they never outweigh the vector. (Changed 2026-09-25, G5.5, at the user's request: first built for steering only, as this line used to say. Changed again at G5.6, at the user's request: the values were boxes at each arc, which covered a short vector entirely.)
- **Snap:** a brief visual cue (the vector or target axis flashes) when a snap engages.
- **Live result updates:** when an input vector changes, the result moves to its new value with a short smooth transition (150 ms), not a jump.
- **Head-to-tail animation:** the selected vectors slide into a head-to-tail chain (1.0 s), the resultant is drawn from the origin to the final head (0.5 s), the chain pauses so students can see it (1.5 s), then the vectors slide back to the origin (0.5 s). The animation never changes any vector's actual values.

---

## 11. Manual test checklist for gestures (used in group G5)
Test each at a normal laptop distance, then leaning in, then sitting back.
- [x] Pinch is detected reliably with each hand, and does not flicker when held.
- [x] Hands together + pull apart creates a vector; it follows the line between the hands.
- [x] Hands apart + pinch resizes the active vector without changing its direction.
- [x] Steering: small hand shake inside the dead zone does not move the vector.
- [x] Steering: moving right turns the vector the same way on screen whatever the view is turned to, even after rotating the 3D view to look from behind. (Globe-style, section 6.4: the side nearest you follows the hand, so a vector pointing at you swings right, one pointing into the screen swings left, and one lying flat pointing right tips into the screen. Reworded 2026-09-25, G5.5: "always moves the head right" cannot hold for every vector if steering is to add depth.)
- [x] Snapping engages near each axis and plane and releases cleanly; turning it off in settings works.
- [x] Each hold gesture triggers once after 0.5 s and not again until the hand changes shape.
- [x] Open palm with the free hand cancels steering and restores the vector exactly; releasing a create, resize or steer never cancels it.
- [x] Locked vectors ignore resize and steer, with the message shown.
- [x] One gesture = one undo step.
- [x] Changing the sensitivity setting changes how much a full stretch creates.

