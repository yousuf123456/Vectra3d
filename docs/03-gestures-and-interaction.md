# 03 — Gestures and Interaction

How hand shapes and movements become changes to vectors.

---

## 1. Design principles

### In plain words
Hands are used for things you'd naturally do by feel: stretching and aiming an arrow. Anything that needs precision, like picking a specific vector or typing an exact value, is done in the panel. Every hand action also has a button, so the app never depends on the camera.

### Technically
- **Pinch is the clutch:** nothing moves unless a pinch is held. Releasing freezes everything. This prevents drift when a hand is merely visible.
- **Continuous control by hand, discrete control by panel.** Selecting one arrow in 3D by pointing is unreliable with a single webcam, so selection is done by clicking or by cycling.
- **Every gesture has a panel equivalent,** so the app stays usable in poor lighting or without a webcam.

### How it's implemented
Built in G5.2, in `gestures/state_machine.py`.

- The clutch is made strict: a gesture starts only when a pinch **begins**. A pinch that is still held when a gesture ends - for example the second hand after a two-hand create - starts nothing until that hand lets go and pinches again. Without this rule, finishing a create while still holding one pinch would immediately start steering the new vector.
- When the pinch ends, the gesture ends and is confirmed at once (section 2).
- The state machine outputs intents, not changes, and `ui/gesture_controller.py` turns them into the same actions the panel uses (from G5.3).

### Likely questions
- **Which way should I hold my hands?** Palms toward the camera, fingers pointing up. Measured at G5.2: held like that, both hands were tracked reliably; with the hands pointing at the camera or overlapping, the tracker usually saw only one of them, and a two-hand pinch could only become steering.
- **Why not control everything with hands?** Some actions are simply faster and more accurate with a click. The aim is learning vectors, not fighting the interface.

---

## 2. The gesture state machine

### In plain words
The app is always in exactly one "mode": idle, creating, resizing, steering, or holding a gesture. What your hands do next decides which mode comes next. This stops two gestures from fighting over the same vector.

### Technically
A finite state machine with states IDLE, CREATING, RESIZING, STEERING, and HOLDING.
- A two-hand pinch (second hand pinching within 0.5 s of the first) beats a one-hand pinch. (The spec started at 0.3 s; it was lengthened after real testing showed people pinch their two hands up to half a second apart.)
- Hold gestures are recognized only in IDLE.
- Letting go of a pinch confirms the gesture at once.
- Only steering can be cancelled: an open palm from the free hand restores the vector exactly. A create or resize is taken back with Undo instead (see "Why a create cannot be cancelled" below).
- Losing a hand for more than 0.3 s counts as a normal release.
- The state machine outputs **intents** ("begin create," "update," "commit," "cancel") rather than changing vectors itself; the app turns intents into the same actions the panel uses.

### How it's implemented
Built in G5.2, in `gestures/state_machine.py` and `gestures/intents.py`.

- `GestureStateMachine.update(hands, now_ms)` is called once per camera frame with the hands measured by `hand_metrics` (see `02-hand-tracking.md`). It returns the current state, any intents, and the progress of a hold gesture. It knows nothing about vectors; until G5.3 the window only shows its state under the camera picture.
- Besides the spec's five states it has one short phase. **Waiting**: one hand has pinched, and for up to 0.5 s it is not known whether a second hand will join, so nothing begins yet. The steering anchor is still where the pinch began, so no movement is lost.
- **Why a create cannot be cancelled.** In a two-hand gesture both hands are pinching, so an open palm can only come from a hand that has just let go. G5.2 made the release wait 0.3 s so such a palm could cancel it. Real testing at G5.3 showed the flaw: a hand letting go of a pinch opens naturally, and the tracker reads that as an open palm, so ordinary releases were being cancelled. No threshold can tell the two apart, since they are the same hand shape at the same moment. The wait was removed; a create is taken back with Undo, which removes it in one step.
- **Why only the free hand can cancel steering.** Found with real hands: a pinch with the other three fingers stretched out is often classified as an open palm (three false cancels in 30 seconds at G5.2), and the steering hand opening as it lets go is too (G5.3). So only the other hand, and only while it is not pinching, is listened to.
- Intents carry the hands' geometry - which gesture, which hands, the start and current pinch points, the hand scale - and nothing about vectors. Turning them into magnitudes and directions is the job of each gesture's own step.
- Hold gestures (thumbs up, pointing up, victory) must be recognised at a confidence of at least 0.6 for 0.5 s, fire once, and cannot fire again from the same hand until it shows a different shape.
- Losing a hand: the hand metrics keep a missing hand's memory for 0.3 s, so one that reappears in time carries on with its pinch intact. The state machine pauses the gesture while the hand is missing and commits it once the hand has been gone for longer. A slow frame is not a missing hand: only a hand actually absent from a frame can expire.
- All timings are compared in whole milliseconds from the frames' own timestamps, never the wall clock, which is what lets the tests play any sequence of hand frames at any pace. The two-hand window, the hand-lost timeout and the hold duration all come from `config.py`.

### Likely questions
- **Why does steering take half a second to start?** Because until then the app cannot know whether a second hand is about to pinch and turn it into a create or resize.
- **How do I take back a vector I just made by hand?** Press Undo (Ctrl+Z). The whole gesture is one step. An open palm does not cancel a create, because letting go of a pinch already looks like an open palm to the tracker.
- **What's a state machine?** A model where a system is always in one of a fixed set of states and moves between them according to clear rules. Traffic lights are a classic example.
- **How was it tested without hands?** By feeding it recorded sequences of fake hand data and checking its output.

---

## 3. Creating a vector

### In plain words
Pinch with both hands close together, then pull them apart. A new arrow grows from zero, pointing along the line between your hands. The hand you pull with becomes the arrow's tip.

### Technically
- CREATING starts when both pinch points begin less than 1.0 hs apart.
- **Magnitude** = (current hand distance − starting distance) ÷ full stretch × sensitivity, with full stretch = 8 hs and sensitivity defaulting to 25 units (adjustable from 5 to 50).
- **Direction:** the 2D line between the pinch points, converted into 3D using the camera's current right and up directions (see section 5). The new vector is therefore parallel to the screen.
- **Head and tail:** the head is at the hand that moved more since the pinch started; if both moved about equally (within 10%), the right-hand side of the screen is the head.
- Releasing either pinch confirms it. Below a magnitude of 0.1, nothing is created.

### How it's implemented
Built in G5.3.

- **The maths** is in `gestures/hand_to_vector.py`, as plain functions tested with hand-calculated values:
  - `stretch_magnitude` applies the formula above. Each distance is divided by the hand scale *of its own moment*, so leaning in mid-gesture does not by itself stretch the vector. Bringing the hands closer than they started gives zero, not a vector pointing backwards.
  - `head_index` picks the pulling hand, with the 10% margin and the right-of-screen fallback. It is re-run every frame, so the head settles as soon as one hand clearly leads.
  - `screen_axes` works out which way "right" and "up" on the screen point in the 3D world. It cannot simply use the camera's `up` setting: PyVista keeps whatever that was set to (z, here), which is tilted away from the screen whenever the view looks down at the scene, and every vector would have tipped towards or away from the student. So right is worked out as *view direction × up*, and the screen's up as *right × view direction*. It is read from the camera on every frame.
  - `create_components` puts these together: the line from the tail hand to the head hand, with the picture's y flipped because it grows downward, carried into 3D along those two directions.
- **The vector is real from the first frame.** `ui/gesture_controller.py` turns the state machine's intents into actions. When a create begins it calls `actions.create_vector` with a zero vector, so the new vector already has its letter and colour, is active, and has a card in the info panel; every frame after that calls `actions.edit_vector`. On release, a vector shorter than 0.1 is discarded.
- **One gesture, one undo step.** A gesture changes the vector 30 times a second, which would fill the 20-step history in under a second. So `actions.begin_gesture` remembers the scene as it was, the actions skip recording while a gesture runs, and `actions.commit_gesture` records that remembered scene once - only if something changed. A too-short create is put back by `actions.cancel_gesture` and records nothing. Undo and Redo are greyed out while a gesture runs.
- **The scene does not rescale while you pull.** The window skips resizing the world while a gesture is in progress, and does it once, on release.
- **The live magnitude** replaces the vector's letter while it is being created, as "|A| = 12.50", and the letter comes back on release.
- **Keeping up with the hands.** Redrawing the whole scene and panel on every camera frame measured about 300 ms per frame against a frame of 33, so the arrow fell ever further behind. While a hand moves a vector, the window now redraws only that vector's arrow and label, and changes only the numbers on its card (`InfoPanel.update_vector`), instead of rebuilding everything. Frames that arrive during a redraw share the next one, which shows the newest position, so no backlog can build up. Measured at about 48 ms per redraw with ten vectors on screen: the arrow updates about 20 times a second, and never lags behind.
- If ten vectors already exist, nothing is drawn and the camera strip shows the same message the panel uses.

### Likely questions
- **Why does it always start flat against the screen?** A single webcam can't measure depth reliably, so depth is added by steering afterwards.
- **Why a sensitivity setting?** Small sensitivity gives fine control over small vectors; large sensitivity reaches big vectors quickly.

---

## 4. Resizing a vector

### In plain words
Pinch with both hands already apart, then move them closer or farther. The active arrow gets shorter or longer but keeps pointing the same way.

### Technically
- RESIZING starts when both pinch points begin 1.0 hs or more apart.
- New magnitude = starting magnitude + (current distance − starting distance) ÷ full stretch × sensitivity, never below 0.1.
- This is **additive**, at the same rate as creating. A ratio-based approach (doubling the gap doubles the length) was rejected: it barely responds on small vectors.

### How it's implemented
Built in G5.4, on top of what G5.3 built for creating.

- **The maths** is `resize_components` in `gestures/hand_to_vector.py`. The stretch is the same one creating uses, but it is allowed to be negative here, which is how closing the hands shortens the vector. The direction is taken from the vector as it was when the resize began and never recalculated, so however the hands wander the arrow cannot turn - only the distance between them counts. The length is held at 0.1 or more every frame.
- **It acts on the active vector,** through `ui/gesture_controller.py` and the same gesture session as creating: the scene is remembered when the resize begins, each frame calls `actions.edit_vector`, and letting go records one undo step. A resize that changed nothing records nothing. Unlike a create, a resize is never thrown away on release, since it cannot have become too short.
- **It is refused, with the reason under the camera picture,** when there is nothing sensible to resize: "Vector A is locked.", "Create a vector first.", or "Vector A has no direction to resize." for a zero vector - which can exist, because `A - A` can be saved as a vector. A refusal changes nothing and records nothing.
- **A result follows it live.** If the resized vector is part of a result (say A in `A + B`), the result arrow is redrawn at its new value each frame, and the result card's numbers change in place. The short glide a result makes after a panel edit is skipped mid-gesture: restarted 30 times a second it would only ever trail behind the hand.
- **Speed.** About 53 ms per update with ten vectors and a result showing - the same as creating. With the resized vector's components and shadows switched on it is about 114 ms, because those overlays rebuild all their geometry every frame; making that faster belongs with G5.8, where components following a hand-moved vector is a criterion of its own.

### Likely questions
- **How does it know whether I want to create or resize?** By how far apart your hands are when you pinch: together means create, apart means resize.
- **Why doesn't the arrow turn when I move my hands up or down?** Resizing only ever changes length. Turning the arrow is steering, a separate one-hand gesture.
- **Can I make a vector point the other way by closing my hands all the way?** No. The length stops at 0.1; reversing a vector would be steering it round, not resizing it.

---

## 5. Steering: the joystick

### In plain words
Pinch with one hand and hold. The spot where you pinched becomes the center of an invisible joystick, drawn as a yellow ring on the camera picture. Move your hand out of the ring and the arrow turns, like spinning a globe by the side nearest you: nudge right and the near side of the arrow moves right; nudge up and it tilts up. The farther you move from the center, the faster it turns. Small shakes inside the ring are ignored. Open your other hand flat to cancel and put the arrow back.

### Technically
- **Rate control, not position control:** hand offset from the anchor sets angular *speed*, not the angle itself. This hides jitter and avoids tiring, large arm movements.
- Offset d (in hs) → speed ω = ω_max × clamp((d − d₀) / (d_max − d₀), 0, 1), with dead zone d₀ = 0.3 hs, d_max = 1.5 hs, ω_max = 90°/s.
- **Screen-relative:** the rotation axes come from the 3D camera's current orientation. Horizontal offset rotates around the camera's *up* direction; vertical offset rotates around its *right* direction. So "right" means the same on screen from any viewpoint, even when viewing the scene from behind.
- **Globe-style:** the side of the arrow nearest you follows your hand. An arrow pointing at you swings right when you move right; one pointing into the screen swings left; one lying flat on the screen and pointing right tips *into* the screen. That last case is the point of steering: a created vector lies flat on the screen, and this is how it gets depth.
- Each frame rotates the vector by angle Δ = ω·Δt around unit axis **u** using **Rodrigues' rotation formula**:
  **v**′ = **v** cos Δ + (**u** × **v**) sin Δ + **u**(**u** · **v**)(1 − cos Δ)
- Rotations preserve length, so magnitude never changes while steering.

### How it's implemented
Built in G5.5.

- **The maths** is in `gestures/hand_to_vector.py`. `deflection` measures the hand's offset from the anchor in the hand scale *at the anchor*, so the joystick keeps one size for the whole gesture; picture y is flipped so up is positive. `steer_speed` is the formula above. `steer_components` turns the vector about `across * up - upward * right` - one axis for a diagonal push, not two turns one after the other - by Rodrigues' formula, then scales the result back to the length the vector had when steering began. Rotations keep length in exact arithmetic but not in floating point; rescaling to the stored length means thousands of frames cannot make the arrow creep longer or shorter.
- **Timed by the camera frames.** Each turn is the speed times the time since the last steering frame, from the frames' own timestamps. So the arrow turns at the same rate whatever the frame rate: when the redraw slows the updates down, each step is just bigger.
- **It acts on the active vector,** through `ui/gesture_controller.py` and the same gesture session as creating and resizing: one undo step per steer, refused with a reason for a locked vector, no vector, or the zero vector (which has no direction to turn). A hand held inside the dead zone changes nothing at all - not even a redraw.
- **Cancelling** is the one hand-driven cancel in the app. An open palm from the *free* hand calls `actions.cancel_gesture`, which puts the whole scene back as it was when steering began and records nothing. Only the free hand counts: the steering hand itself reads as an open palm the moment it lets go.
- **The joystick in the camera picture** is drawn by `ui/camera_preview.py` over the hand: the anchor dot, the dead-zone ring (0.3 hs at the anchor's hand scale) and a line to the current pinch point, in yellow so it is not mistaken for the hand's own lines.
- **Speed.** About 65 ms per update with ten vectors and a result showing, so about 15 updates a second; the camera itself kept 21 frames a second while steering, against 32 when idle, and frames never backed up. With the vector's components and shadows on it is about 130 ms, which belongs with G5.8.

### Likely questions
- **Why a joystick instead of pointing where I want?** Pointing needs accurate depth, which one webcam can't give. The joystick only needs left/right/up/down.
- **Why does it rotate relative to the screen?** If rotation followed fixed world axes, moving your hand right could move the arrow left on screen when the view is rotated, which feels broken.
- **Why does the arrow sometimes swing the opposite way to my hand?** It turns like a globe you spin by its near side. If the arrow points into the screen, its head is on the far side, which moves the other way. Moving right always turns it the same way - it is only the head's position that decides which way the head itself goes.
- **Why does moving my hand right sometimes push the arrow into the screen?** That is how depth is added. An arrow lying flat on the screen can only leave it by tipping into or out of it.

---

## 5a. Seeing the angles

### In plain words
The highlighted arrow always shows two angles as curved lines drawn from the axes: θ, measured down from the z axis, and φ, measured round the floor from the x axis to the arrow's shadow. Each curve carries its letter, and both values sit in one small line beside the arrow's head, changing as you move it.

### How it's implemented
Built in G5.5, in `AngleArcs` in `render/overlays.py`.

- `theta_arc` is a circular arc from +z to the vector, in the plane that holds both; `phi_arc` is a circular arc in the XY plane from +x turning counterclockwise, the way section 2.3 of the spec measures φ, so 270° goes three quarters of the way round. A dashed grey guide runs from the origin to the vector's floor shadow and up to its head, so it is visible what φ is measured to. Along the z axis φ is undefined, so no φ arc or value is drawn.
- The values come from `core/spherical.py`, the same numbers the panel uses, formatted to two decimals.
- **Always on, for the active vector only.** First built for steering only, as the spec then said; the user asked at G5.5 for the angles to show whenever a vector is active. One vector at a time, like components and shadows. They are hidden while the head-to-tail animation plays, because the arrows are drawn away from their real positions then.
- **Readability fixes, all from looking at the picture.** VTK's built-in font has no Greek letters, so "θ 45.00°" came out as " 45.00°"; the labels use Windows' own Arial, which has them. The values were first drawn in the vector's own colour, which the user found hard to read, so they are dark text on a white box outlined in the vector's colour, which reads on every one of the ten colours, including yellow.
- **Quieter since G5.6.** At first each arc had its own boxed value, 16 pt bold, and the arcs were 3.5 px and solid. Boxes of a fixed screen size do not shrink with the vector, so on a short vector the two boxes covered the arrow completely, and on any vector the arcs outweighed it - the user's report. Now the arcs are 2 px and half transparent, each carries only its letter (θ or φ, no box) just outside its middle (`arc_tag_position`), and both values are one 12 pt line, `angle_text`, hung under the vector's letter beside its head, where it cannot sit on the arrow however short it is.

### Likely questions
- **Why θ and φ rather than α, β, γ?** θ and φ are the two numbers the "magnitude + angles" input uses, so the arcs show exactly what a student would type to make this arrow. α, β and γ are on the card.

---

## 6. Snapping

### In plain words
While steering, the arrow gently "clicks" onto an axis or a flat plane when it gets close, making it easy to point exactly along x or lie exactly flat.

### Technically
- Angle to an axis **a**: arccos(|**v** · **a**| / |**v**|). Angle to a plane with normal **n**: arcsin(|**v** · **n**| / |**v**|).
- Snaps in below 5°, releases above 8°: hysteresis again, so it doesn't flicker at the boundary.
- Axis snaps take priority over plane snaps. Snapping can be turned off in settings.
- **Snap lock:** while snapped, steering turns the arrow *within* the plane it lies in (on an axis, within one of the two planes that contain it) instead of about the screen's axes. Added at G5.6 after real testing; see below.

### How it's implemented
Built in G5.6.

- **The rules** are pure functions in `gestures/hand_to_vector.py`. A `SnapTarget` is an axis (with a sign, so +x and -x are different targets) or a plane (named by its normal). `angle_from` measures the two angles above; `snap_target` decides each frame: an axis within 5° always wins, even over a plane the arrow is held in; otherwise the current target holds until 8°; otherwise the nearest plane within 5°; otherwise nothing. Only one axis can be within 5° of any direction, and it is the one along the largest component; the nearest plane is square to the smallest. `snapped_components` puts the arrow exactly on the target at its full length - on an axis the other two components are exactly zero, in a plane the part sticking out is dropped and the rest scaled back up.
- **Two directions, not one.** The joystick turns a hidden *steered* direction, kept in `ui/gesture_controller.py`, and the store is given that direction snapped. Turning the snapped arrow itself would not work: each frame it would move a couple of degrees off the axis, snap straight back, and never get 8° away. When a snap takes hold, the steered direction is reset onto it once, so drift absorbed on the way in does not carry into the next move - but only on arriving; reset every frame, the arrow could never leave.
- **The snap lock**, `turn_axes`. The default view looks down at the floor from above, so the screen's up is tilted from z, and a purely sideways push turned the arrow about that tilted axis and dropped it out of the XY plane after about 24° - found by the user with real hands. While snapped, each plane the arrow lies in replaces the screen axis nearest to its normal: for the floor seen from above, sideways now spins the arrow round inside it, while up/down still tilts it out, which is how it leaves. For the YZ plane seen edge-on from the front it is the other way round. On an axis, which lies in two planes, sideways takes the plane whose normal is closer to the screen's up and up/down takes the other. The normals are signed to point the way the screen axis they replace does, so the globe-style sense of steering is unchanged.
- **Where it starts.** An arrow that already lies exactly on an axis or plane when the pinch begins counts as snapped from the start (`exact_target`): it needs the full 8° to leave, and does not flash, since nothing arrived.
- **The cue.** When a snap moves the arrow onto something new, its halo flashes brighter for 0.3 s (`SNAP_FLASH_OPACITY`, `SNAP_FLASH_MS` in `render/vector_actor.py`, timed by one `QTimer` in the window so a second snap restarts it). The halo rather than the axis, because a plane has no single line to flash. Leaving an axis along one of its planes is not a new arrival and does not flash. While snapped, the camera strip says "Steering, snapped to +x axis" or "... XY plane"; it keeps the word "Steering", whose place it takes.
- Snapping can be switched off from the Gesture settings box (section 6a). Switched off in the middle of a snap, the arrow goes to where the hand has steered it on the next frame.

### Likely questions
- **Can I avoid snapping for an angle like 3° off the axis?** Turn snapping off in settings, or type the exact value in the panel.
- **Why does the arrow sometimes jump a few degrees when it lets go of an axis?** While held, your hand keeps turning the hidden direction; at 8° the arrow lets go and jumps to where your hand has been steering it. That gap is what stops it flickering on and off at the edge.
- **Why does moving my hand sideways keep the arrow on the floor, but up and down lifts it off?** That is the snap lock. Once the arrow is in a plane, one hand direction slides it round inside the plane and the other tilts it out, so you can sweep round the floor without it drifting off. A hand that also drifts up a little will still, slowly, tilt it out.

---

## 6a. Gesture settings

### In plain words
A small **Gesture settings** box in the action panel has two controls: a tick box that turns snapping on or off, and a slider for how long a vector one full stretch of your hands makes. Lower is finer control over short vectors; higher reaches long ones quickly.

### Technically
- Snapping: on by default.
- Magnitude sensitivity: the units one full stretch (8 hs) adds when creating or resizing. Default 25, from 5 to 50 in steps of 5.
- Both start at their defaults every time the app opens.

### How it's implemented
Built in G5.7.

- **In the state layer**, as every other piece of data is. `Settings` in `state/models.py` is a frozen dataclass holding the two values, created from `config.py`. The store holds one; `actions.set_snapping` and `actions.set_sensitivity` change it. The sensitivity action refuses anything off the 5-50 grid, because every change goes through the actions whether or not the panel could produce it.
- **Not part of the scene.** Changing a setting records no undo step (F-19 is about the vectors), and clearing the scene or undoing leaves the settings alone. It also does not notify the store's listener: nothing drawn depends on a setting, and the full redraw a notification causes costs about 300 ms - once for every step of a dragged slider.
- **Read live.** `ui/gesture_controller.py` reads `store.settings` on every frame, so a change applies from the next frame: creating and resizing use the sensitivity; steering skips the snap rules, the snap lock and the flash when snapping is off.
- **The panel box** in `ui/action_panel.py` is a `CollapsibleBox` that starts folded - the one box that does, because settings are rarely changed and the vector list needs the room. The slider counts steps of 5 (1 to 10), so it can only ever produce a value the spec allows, and the readout beside it says "25 units per full stretch".
- **Never saved.** On a shared lab or lecture laptop, the next student should not inherit someone else's setting.

### Likely questions
- **Why does my setting reset when I reopen the app?** On purpose: many students share one laptop in a lab, and an odd setting left behind by someone else would look like a bug.
- **Why is the box folded?** It is rarely needed, and the vector list below it needs the height. Click its title to open it.

---

## 7. Hold gestures

### In plain words
Three hand signs trigger actions if you hold them for half a second: pointing up selects the next vector, thumbs up locks or unlocks it, and a peace sign shows or hides its components. A ring fills up in the camera view while you hold, so you can see it coming.

### Technically
- Recognized with MediaPipe's built-in gesture classifier: `Pointing_Up`, `Thumb_Up`, `Victory`.
- Must be recognized continuously for 0.5 s with confidence of at least 0.6, triggers once, and re-arms only after the hand changes shape.
- There is deliberately no delete gesture: a misread gesture should never destroy work.

### How it's implemented
Built in G5.8. The timing - 0.5 s at 0.6 confidence, firing once, re-arming on a change of shape - was built into the state machine at G5.2; this step connected it to the vectors.

- **What each shape does** is decided in `ui/gesture_controller.py`, which turns the machine's `HoldTriggered` intent into an action on the active vector, the same actions the panel uses. `Pointing_Up` calls `actions.activate_next`: the next vector by letter after the active one, wrapping round from the last to the first, skipping locked ones. If the active vector is the only unlocked one it stays; if all are locked, nothing changes and the camera strip says "All vectors are locked." `Thumb_Up` calls `toggle_locked`, and `Victory` calls `toggle_components`.
- **Locked vectors.** "A locked vector ignores all gestures" is read as the gestures that would change it - resizing and steering, both refused since G5.4 and G5.5 - and being skipped when cycling. `Thumb_Up` still works on a locked vector, because it is how one is unlocked, and `Victory` still shows its components, because that changes nothing about it and the panel allows the same.
- **Undo.** Locking by hand is one undo step, like the panel's Lock button. Moving the highlight and showing components are not, the same as clicking a card or a toggle.
- **With no vectors** any of the three says "Create a vector first." and does nothing.
- **The progress ring** is drawn by `ui/camera_preview.py` around the hand making the shape: the machine's `HoldStatus` says which hand, `hold_ring` centres the ring on the middle of that hand's 21 points and sizes it from its hand scale (1.4 hs), and it fills clockwise from twelve o'clock over a faint full circle. Yellow, like the steering joystick.
- **Components follow the hand.** While a hand moves a vector showing its components or shadows, both are redrawn each frame without rendering themselves, and the window renders once. Measured on screen with ten vectors and both on, while steering: 85 ms per update before, 77 ms after. The rest is rebuilding the geometry each frame, spread evenly across components, shadows, angle arcs and the arrow.

### Likely questions
- **Why the half-second wait?** It stops hand shapes you pass through by accident from triggering actions.
- **Why can thumbs up unlock a vector if locked vectors ignore gestures?** Otherwise a vector locked by hand could only be unlocked from the panel. Thumbs up is a lock *switch*; the gestures a locked vector ignores are the ones that would change it.
- **I held the sign and nothing happened again.** It fires once per hold. Change your hand to any other shape for a moment, then show the sign again.

---

## 8. Undo

### In plain words
Any change can be undone, including an entire hand movement. One full gesture, from pinch to release, is one undo step.

### Technically
- **Snapshot-based:** before each change, a copy of all vectors (at most 10, so it's tiny) is stored; undo restores the previous copy. The last 20 steps are kept; a new change clears the redo history.
- Gestures record a snapshot only at the start, and commit one step on release. Cancelled gestures record nothing.

### How it's implemented
*The panel half was built in step G2.8; the gesture half comes in G5.9.*

`src/vectra3d/state/undo.py` holds a `History` of snapshots. A snapshot is the vectors plus which one was active — the active vector is in there because creating a vector makes it active, so undoing a create has to put the highlight back where it was rather than guess.

Each snapshot is a plain dictionary copy rather than a deep one. That is safe because a `Vector` is frozen and cannot be edited in place, so two snapshots sharing the same vector object can never come to disagree. It is also what makes taking a snapshot before *every* change cheap enough not to think about.

The snapshots are recorded in `state/actions.py`, the one place every change passes through — the same property that lets gestures reuse all of this in G5. An action records only once its change is certain to happen: creating an eleventh vector, or editing or deleting a locked one, is refused and records nothing, because a step recorded for a change that never happened would make undo appear to do nothing.

**Undo and Redo sit in the toolbar**, with Ctrl+Z and Ctrl+Y, and grey out when there is nothing to do. F-19 originally asked for them in the panel; the criterion was changed deliberately at G2.8, because panel height is what the vector list competes for and a toolbar is where people look for undo. While a text field has focus, Ctrl+Z is that field's own text undo and the vector history is left alone — the shortcut undoes whatever you are currently doing.

What undo deliberately does *not* cover: the camera, which vector is active, which are ticked for an operation, and the components and shadows toggles. Those are ways of looking at the scene rather than changes to it, so a vector restored by undo comes back unticked with its overlays off.

### Likely questions
- **Why snapshots instead of recording each action?** With at most 10 vectors, copying everything is simpler and less error-prone than a command system.
