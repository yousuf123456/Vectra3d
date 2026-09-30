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
- Two-hand pinch beats one-hand pinch. If a second hand pinches within **0.5 s** (tunable; started at 0.3) of the first, it is a two-hand gesture; otherwise the first hand starts STEERING once the window has passed, and a later second pinch is ignored until STEERING ends. The steering grab point is still the pinch point at the moment the first pinch began.
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

They are used to create a vector (6.2). Steering does not turn the vector about them: it changes the vector's own angles (6.4), and uses the screen's directions only for a vector grabbed on the z axis, to choose which way the head leaves it.

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

### 6.4 Steer the active vector (grab and drag)
1. One hand pinches, the other does not. This **grabs** the active vector. The pinch point at the moment the pinch began is the **grab point**.
2. While the pinch is held, the vector turns **by as much as the hand moves**: each frame, the pinch point's movement since the previous frame, in hs (in that frame's hand scale), turns it by **90° per hs** (tunable). Movement from the moment the pinch began counts, including the two-hand window (section 5). A still hand leaves the vector still; there is no dead zone and no speed. To turn further than one reach of the hand, let go and grab again.
3. Steering changes the vector's two angles, θ and φ (section 2.3) - the same two the 3D view draws as arcs on the active vector:
   - **Up and down change θ.** Hand up lowers θ, so the head rises towards **+z**; hand down raises it, so the head drops towards **−z**. This is the same whatever the view's rotation and wherever the vector points. The head turns round the **vertical circle** through it and the z axis, with **no stop**: keep moving up and it passes over the top (+z) and comes down the far side, keep moving down and it passes under the bottom (−z) - a full turn either way, for as long as the hand keeps moving. Moving back retraces the way it came. (Added 2026-09-30, found with real hands: θ used to stop at 0° and 180°, so a vector dragged up stopped at +z and only moved again once the hand came back down.)
   - **Left and right change φ**, turning the vector around the z axis like a turntable, and **always the same way**: moving right raises φ (anticlockwise seen from above), moving left lowers it - wherever the vector points, whatever the view, across grabs, and after going over the top. So the side of the turntable nearest the student follows the hand: a vector pointing towards the student moves right on screen as the hand moves right, and one pointing away moves left, like the far side of a turntable. (Changed 2026-09-30 at the user's request: the way was chosen at each grab, and again on crossing a pole, from where the vector pointed, so the same hand movement turned it different ways at different times.)
   - A diagonal movement changes both angles, each by its own part of the movement.
   - Near the z axis a change of φ moves the head only a little, as on a turntable.
   - **Grabbed on the z axis** - straight up or straight down, as a release there snaps it; a drag passes through without stopping - φ means nothing, so neither rule above can move the head. There, the head leaves the axis **the way the hand moves on screen**, by the same 90° per hs: from straight up, moving down tips it towards the viewer (down on screen) and moving right tips it right; from straight down, the same with up. The part of a movement that points further into the axis (up at straight up, down at straight down) does nothing. Once the vector has left the axis, the rules above take over. (Added 2026-09-27, found with real hands: pushing sideways at the z axis did nothing, and pushing away from it often tipped the head along the line of sight, so it seemed not to move.)
4. Magnitude never changes while steering.
5. Releasing the pinch leaves the vector where the hand put it - exactly on an axis or plane if it is within reach of one (6.5).

(Changed 2026-09-29 at the user's decision: grab and drag replaces the joystick. The joystick turned the vector at a speed set by how far the hand was held from its anchor, which with sticky snapping stuck at axes and could not turn smoothly through a full turn; the user found it janky. Changed 2026-09-27 before that, also at the user's decision, from the globe-style rule settled at G5.5, which turned the vector about the screen's axes so the same hand movement did opposite things depending on where the vector pointed.)

### 6.5 Snapping (on release)
Nothing snaps while the hand is moving the vector: it follows the hand freely. Snapping happens when the pinch is **released**, on the two angles of 6.4, each on its own:
- **θ snaps to 0°, 90° or 180°**, and **φ snaps to 0°, 90°, 180° or 270°**, if the angle is within **5°** (tunable) of one of them on release. The angle is then set exactly to that value.
- While the vector is within reach of a snap, the camera strip says **"Release to snap to"** the axis or plane, so the student knows before letting go.
- Between them this covers every axis and plane:

  | Snapped | The vector lies |
  |---|---|
  | θ at 0° or 180° | on the +z or −z axis (φ is then meaningless and does not snap) |
  | θ at 90° | in the XY plane |
  | φ at 0° or 180° | in the XZ plane |
  | φ at 90° or 270° | in the YZ plane |
  | θ at 90° and φ too | on the ±x or ±y axis |

  An axis is both angles snapped at once, so axes need no priority rule over planes. And since sideways movement changes only φ, a vector in the XY plane stays in it while the hand moves sideways; a little up-and-down wobble on the way is taken out again on release, as long as it stays within 5°.
- A release that moves the vector onto a snap shows the snap cue (section 10). One already exactly there - grabbed on an axis and let go without moving - changes nothing and shows no cue.
- The snap belongs to the gesture: it is part of the same undo step (section 5). A cancelled steer restores the vector and does not snap.
- Snapping is **on by default** and can be turned off in settings (section 8). With it off there is no hint, and a release leaves the vector exactly where the hand put it.

(Rewritten 2026-09-29 with grab and drag. The 2026-09-27 version snapped while steering, held a snapped angle until the steering pushed it 8° away, and carried rules for pushing on and reversing; with a vector that follows the hand, a snap mid-drag would stop the vector while the hand kept moving. It in turn replaced the snap lock added at G5.6.)

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
| Steering rate | 90° per hs | 6.4 |
| Snap angle | 5° | 6.5 |
| Hold duration | 0.5 s | 7 |
| Hold confidence | 0.6 | 7 |
| Live result transition | 150 ms | 10 |
| Scene rescale transition | 300 ms | 3 |
| Head-to-tail animation (slide / draw / pause / return) | 1.0 / 0.5 / **1.5** / 0.5 s | 10 |

---

## 10. Visual feedback and animation
- **Active vector:** highlighted (thicker, with a glow or outline) in the 3D view and in the info panel.
- **During CREATING / RESIZING:** the live magnitude is shown next to the vector's head.
- **During STEERING:** the camera preview shows the grab point and a line from it to the current pinch point. (Was the joystick's anchor and dead-zone ring, until grab and drag on 2026-09-29.)
- **Angles of the active vector:** the 3D view always shows the active vector's θ and φ as arcs from their axes - θ from +z to the vector, φ in the XY plane from +x round to the vector's shadow - each arc tagged with its own letter (θ, φ), and their values shown as one line beside the vector's head, under its letter, changing live while a hand moves it. The arcs are thin and half transparent so they never outweigh the vector. (Changed 2026-09-25, G5.5, at the user's request: first built for steering only, as this line used to say. Changed again at G5.6, at the user's request: the values were boxes at each arc, which covered a short vector entirely.)
- **Snap:** a brief visual cue (the vector's halo flashes) when a release moves the vector onto an axis or plane (section 6.5).
- **Live result updates:** when an input vector changes, the result moves to its new value with a short smooth transition (150 ms), not a jump.
- **Head-to-tail animation:** the selected vectors slide into a head-to-tail chain (1.0 s), the resultant is drawn from the origin to the final head (0.5 s), the chain pauses so students can see it (1.5 s), then the vectors slide back to the origin (0.5 s). The animation never changes any vector's actual values.

---

## 11. Manual test checklist for gestures (used in group G5)
Test each at a normal laptop distance, then leaning in, then sitting back.
- [x] Pinch is detected reliably with each hand, and does not flicker when held.
- [x] Hands together + pull apart creates a vector; it follows the line between the hands.
- [x] Hands apart + pinch resizes the active vector without changing its direction.
- [x] Steering: holding the pinching hand still keeps the vector still, and a small shake barely moves it. (Was "inside the dead zone"; rewritten 2026-09-29 for grab and drag, which has no dead zone.)
- [x] Steering: dragging the hand up always raises the head towards +z and dragging it down always lowers it, whatever the view and wherever the vector points - including pointing away from you, and after rotating the view to look from behind. Keeping on up carries it over the top and down the far side without stopping, all the way round; the same downwards. Dragging right always turns the vector the same way round the z axis (anticlockwise seen from above), wherever it points and after going over the top; by letting go and grabbing again it can be turned all the way round. At the z axis, dragging tips the head off it the way the hand moves. (Rewritten 2026-09-29 for grab and drag, section 6.4.)
- [x] Snapping: released within 5° of an axis or plane, the vector lands exactly on it - the strip says "Release to snap to ..." beforehand and the halo flashes; released further away, it stays where it was left; turning snapping off in settings stops both. (Rewritten 2026-09-29 for snapping on release, section 6.5.)
- [x] Each hold gesture triggers once after 0.5 s and not again until the hand changes shape.
- [x] Open palm with the free hand cancels steering and restores the vector exactly; releasing a create, resize or steer never cancels it.
- [x] Locked vectors ignore resize and steer, with the message shown.
- [x] One gesture = one undo step.
- [x] Changing the sensitivity setting changes how much a full stretch creates.

