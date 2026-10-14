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
- **When the camera itself stops.** A lost hand is noticed on the frames that follow, so if the whole camera stops - a USB webcam unplugged mid-pinch - no frame ever comes to notice it, and the gesture would never end: Undo would stay greyed out and nothing done afterwards would be recorded, until the app restarted. Found by the G5 review. `GestureStateMachine.camera_lost()` now ends a create, resize or steer as a normal release, exactly as a lost hand does (spec section 4.4), and forgets every hand; the window calls it when the tracker reports the camera lost.
- Intents carry the hands' geometry - which gesture, which hands, the start and current pinch points, the hand scale - and nothing about vectors. Turning them into magnitudes and directions is the job of each gesture's own step.
- Hold gestures (thumbs up, pointing up, victory) must be recognised at a confidence of at least 0.6 for 0.5 s, fire once, and cannot fire again from the same hand until it shows a different shape.
- Losing a hand: the hand metrics keep a missing hand's memory for 0.3 s, so one that reappears in time carries on with its pinch intact. The state machine pauses the gesture while the hand is missing and commits it once the hand has been gone for longer. A slow frame is not a missing hand: only a hand actually absent from a frame can expire.
- All timings are compared in whole milliseconds from the frames' own timestamps, never the wall clock, which is what lets the tests play any sequence of hand frames at any pace. The two-hand window, the hand-lost timeout and the hold duration all come from `config.py`.

### Likely questions
- **Why does steering take half a second to start?** Because until then the app cannot know whether a second hand is about to pinch and turn it into a create or resize.
- **How do I take back a vector I just made by hand?** Press Undo (Ctrl+Z). The whole gesture is one step. An open palm does not cancel a create, because letting go of a pinch already looks like an open palm to the tracker.
- **What's a state machine?** A model where a system is always in one of a fixed set of states and moves between them according to clear rules. Traffic lights are a classic example.
- **How was it tested without hands?** By feeding it recorded sequences of fake hand data and checking its output.
- **What if the camera disconnects while I am steering?** The arrow stays where you had steered it, as if you had let go, and one Undo takes the whole steer back.

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

## 5. Steering: grab and drag

### In plain words
Pinch with one hand to grab the highlighted arrow, then move your hand: the arrow turns by as much as your hand moves, and stops when your hand stops. Move up and the head rises towards the top (+z); keep going and it goes over the top and down the far side, all the way round. Move right and the arrow spins round the vertical axis like a turntable, always the same way. A yellow dot on the camera picture marks where you grabbed, with a line to your hand. To turn further than your arm reaches, let go and grab again. Open your other hand flat to cancel and put the arrow back.

### Technically
- **Position control:** each frame, the hand's movement since the last frame, in hand-scale units (hs), turns the arrow by 90° per hs. A still hand is a still arrow.
- **Up and down** turn the head round its **vertical circle** - the circle through the arrow and the z axis - with no stop. The app keeps the arrow as a *tilt* round that circle, from −180° to 180°, rather than as θ, because θ stops at 0° and 180° and a tilt does not: past a pole the tilt goes negative, which is θ = |tilt| on the far side, φ + 180°.
- **Left and right** change φ, always the same way: right raises φ, anticlockwise seen from above, so the side of the turntable nearest a student looking down at the floor follows the hand. It does not depend on where the arrow points or on the view.
- **Grabbed exactly on the z axis**, φ means nothing, so there is no vertical circle yet. The first movement tips the head off the axis the way the hand moves on screen, by Rodrigues' rotation formula about the axis square to the pole and that direction:
  **v**′ = **v** cos Δ + (**u** × **v**) sin Δ + **u**(**u** · **v**)(1 − cos Δ)
  The part of the movement pointing further into the axis is dropped.
- Magnitude never changes while steering.

### How it's implemented
Built in G5.5 as a joystick; rebuilt as grab and drag on 2026-09-29/30.

- **The maths** is in `gestures/hand_to_vector.py`. `hand_movement` measures how far the pinch point moved between two frames, in the newer frame's hand scale, with picture y flipped so up is positive. `Meridian` holds the arrow as a tilt round its vertical circle and the circle's φ; its `heading` gives θ and φ back. `drag_meridian` applies one frame's movement. `leave_pole` handles an arrow grabbed on the z axis. `heading_components` turns θ and φ into x, y, z, setting exactly to zero any component an axis-aligned angle makes zero - `cos 90°` is 6e-17 in floating point, not 0.
- **It acts on the active vector,** through `ui/gesture_controller.py` and the same gesture session as creating and resizing: one undo step per grab, refused with a reason for a locked vector, no vector, or the zero vector. The first update is measured from where the pinch began, so movement during the 0.5 s two-hand window counts. A still hand changes nothing - not even a redraw.
- **Cancelling** is the one hand-driven cancel in the app. An open palm from the *free* hand calls `actions.cancel_gesture`, which puts the scene back as it was when the grab began and records nothing. Only the free hand counts: the steering hand itself reads as an open palm the moment it lets go.
- **The grab mark** in the camera picture is drawn by `ui/camera_preview.py`: a dot at the grab point and a line to the current pinch point, in yellow (`theme.GESTURE_MARK`) so it is not mistaken for the hand's own lines.
- **Why it changed.** The joystick turned the arrow at a speed set by how far the hand was held from the anchor. With snapping that held on until 8°, it stuck at axes and could not turn smoothly through a full turn; the user found it janky. Then, with real hands: θ stopping at 0° made a dragged arrow stop at the top until the hand came back down, so the vertical circle replaced it; and choosing the sideways direction from where the arrow pointed made the same hand movement turn it different ways, so it was fixed.

### Likely questions
- **Why not point where I want the arrow to go?** Pointing needs accurate depth, which one webcam can't give. Grab and drag only needs left/right/up/down.
- **Why does the arrow sometimes move left on screen when I move right?** Right always spins it the same way round, like a turntable. A turntable's near side moves right when its far side moves left, so an arrow pointing away from you goes left.
- **How do I give a flat arrow depth?** Move up or down: that tilts it towards +z or −z. Moving sideways spins it round without leaving the floor.
- **Why does the arrow keep going over the top instead of stopping at +z?** So a steady hand movement is a steady turn, with no point where the hand has to reverse. Move back and it retraces the way it came.

---

## 5a. Seeing the angles

### In plain words
The highlighted arrow always shows its three direction angles as curved lines: α in red from the x axis, β in green from the y axis, γ in blue from the z axis, each ending on the arrow. Each curve carries its letter, and the three values sit in one small line beside the arrow's head - the same numbers as on its card - changing as you move it.

### How it's implemented
Built in G5.5 as θ and φ arcs; changed to α, β, γ on 2026-10-15 at the user's decision, because first-year students know direction angles and have not studied spherical coordinates. In `AngleArcs` in `render/overlays.py`.

- `direction_arc(components, axis, radius)` is one circular arc from a positive axis to the vector, in the plane holding both, sweeping the angle between them; the same function draws all three. An angle of 0° (the arrow along that axis) has no arc. An arrow pointing exactly opposite an axis has no single plane with it, so its 180° arc turns through the diagonal between the other two axes. The first version turned it through the next axis instead, and the off-screen render showed why that was wrong: along −z, γ's half turn lay exactly on top of α's arc, and the two read as one purple line.
- Each arc and its letter are drawn in their axis's colour, the same red, green and blue as the axes and the component arrows, so each angle is tied to its axis at a glance.
- The values, `angle_text`, come from `core/vector_math.direction_angles`, the function the info panel uses, formatted to two decimals: `α 60.00°   β 45.00°   γ 120.00°`.
- **Always on, for the active vector only.** First built for steering only, as the spec then said; the user asked at G5.5 for the angles to show whenever a vector is active. One vector at a time, like components and shadows. They are hidden while the head-to-tail animation plays, because the arrows are drawn away from their real positions then.
- **Readability, all from looking at the picture.** VTK's built-in font has no Greek letters, so "α 45.00°" would come out as " 45.00°"; the labels use Windows' own Arial, which has them. The values are dark text on a white box outlined in the vector's colour, which reads on every one of the ten colours, including yellow. Since G5.6 the arcs are 2 px and half transparent, each carries only its letter just outside its middle (`arc_tag_position`), and the values are one 12 pt line hung under the vector's letter beside its head - boxes at each arc had covered short vectors entirely.

### Likely questions
- **Why not θ and φ?** They were shown until 2026-10-15. They are spherical coordinates, which first-year students have not met; α, β and γ are what their textbooks use, and what they now type in the "Magnitude + angles" form. Steering still works with θ and φ inside, where nobody sees them.
- **Why is there no red arc when the arrow points along x?** α is 0° then: there is no angle to draw.

---

## 6. Snapping

### In plain words
When you let go of a steered arrow close to an axis or a flat plane, it clicks exactly onto it. While you are still holding it, the camera strip tells you what it would click onto, so you know before you let go.

### Technically
- Snapping works on the arrow's two angles, each on its own: θ snaps to 0°, 90° or 180°, and φ to 0°, 90°, 180° or 270°, when within 5° of one of them **at the moment of release**. Nothing snaps while the hand is moving the arrow.
- θ at 0° or 180° is the z axis; θ at 90° is the XY plane; φ at 0° or 180° is the XZ plane, at 90° or 270° the YZ plane; θ and φ both snapped is the x or y axis. On the z axis φ means nothing and does not snap.
- The snap values are 90° apart, so an angle can be within reach of at most one.
- Snapping can be turned off in settings.

### How it's implemented
Built in G5.6 as snapping while steering; rebuilt as snapping on release on 2026-09-29.

- **The rules** are pure functions in `gestures/hand_to_vector.py`. `snap_near` says what a release would land on: a `Snap` with a θ, a φ, or both. Its `label` names it for the camera strip, such as "+x axis" or "XY plane". `snapped` puts the snapped angles in place of the real ones.
- **On release,** `_landing` in `ui/gesture_controller.py` works out where the arrow lands, if anywhere, and `_commit` edits it there *before* recording the gesture, so the snap is part of the same undo step. A release that would not move the arrow - out of reach, or already exactly on the axis - snaps nothing. A cancelled steer never snaps.
- **The hint.** While within reach, the camera strip says "Steering: release to snap to -y axis"; it keeps the word "Steering", whose place it takes.
- **The cue.** A release that moves the arrow onto an axis or plane flashes its halo brighter for 0.3 s (`SNAP_FLASH_OPACITY`, `SNAP_FLASH_MS` in `render/vector_actor.py`). The release ends the gesture, so the window's full redraw has already drawn the arrow where it landed; `_flash_snapped` in `ui/main_window.py` then redraws only its halo, brighter, and one `QTimer` puts it back.
- **Why it changed.** Snapping while steering held a snapped arrow still until the hand had pushed 8° away, then let it jump. With an arrow that follows the hand, a snap mid-drag would stop it while the hand kept moving. Snapping on release keeps the drag smooth and still lands the arrow exactly.
- Snapping can be switched off from the Gesture settings box (section 6a). It is read at the moment of release, so switching it off mid-drag takes effect.

### Likely questions
- **Can I leave an arrow 3° off an axis?** Turn snapping off in settings, or type the exact value in the panel.
- **The strip says "release to snap to XY plane" the whole time I move sideways - why?** Sideways movement never changes θ, so an arrow lying on the floor stays exactly on it; letting go keeps it there.

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
- **The progress ring** is drawn by `ui/camera_preview.py` around the hand making the shape: the machine's `HoldStatus` says which hand, `hold_ring` centres the ring on the middle of that hand's 21 points and sizes it from its hand scale (1.4 hs), and it fills clockwise from twelve o'clock over a faint full circle. Yellow, like the steering grab mark.
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
*The panel half was built in step G2.8; the gesture half arrived with creating by hand in G5.3 and was verified across every gesture in G5.9.*

`src/vectra3d/state/undo.py` holds a `History` of snapshots. A snapshot is the vectors plus which one was active — the active vector is in there because creating a vector makes it active, so undoing a create has to put the highlight back where it was rather than guess.

Each snapshot is a plain dictionary copy rather than a deep one. That is safe because a `Vector` is frozen and cannot be edited in place, so two snapshots sharing the same vector object can never come to disagree. It is also what makes taking a snapshot before *every* change cheap enough not to think about.

The snapshots are recorded in `state/actions.py`, the one place every change passes through — the same property that lets gestures reuse all of this in G5. An action records only once its change is certain to happen: creating an eleventh vector, or editing or deleting a locked one, is refused and records nothing, because a step recorded for a change that never happened would make undo appear to do nothing.

**Undo and Redo sit in the toolbar**, with Ctrl+Z and Ctrl+Y, and grey out when there is nothing to do. F-19 originally asked for them in the panel; the criterion was changed deliberately at G2.8, because panel height is what the vector list competes for and a toolbar is where people look for undo. While a text field has focus, Ctrl+Z is that field's own text undo and the vector history is left alone — the shortcut undoes whatever you are currently doing.

What undo deliberately does *not* cover: the camera, which vector is active, which are ticked for an operation, and the components and shadows toggles. Those are ways of looking at the scene rather than changes to it, so a vector restored by undo comes back unticked with its overlays off.

**Gestures: one gesture, one step.** A hand gesture changes a vector on every camera frame, which would fill the twenty-step history in under a second. So a gesture runs as a *session* in the store: `actions.begin_gesture` remembers the scene when the pinch begins, every action skips recording while the session runs, and `commit_gesture` records the remembered scene once when the gesture ends - or nothing, if nothing changed. `cancel_gesture` puts the remembered scene back and records nothing. Built at G5.3, because creating by hand needed it, and reused unchanged by resizing and steering. Undo and Redo are greyed out while a gesture runs, so a scene can never be restored from under the hands. The lock hold gesture is a single action like the panel's Lock button, so it records one step through the ordinary route.

G5.9 added `tests/ui/test_gesture_undo.py`, which proves this from raw hand frames rather than from intents: synthetic hands go into the window's frame slot and pass through the hand metrics, the state machine, the controller and the store, the whole way a student's do. It covers a create, a resize and a steer each taken back by one Undo; a gesture ended by both hands leaving the picture, which counts as a release (spec section 4.4); a 300-frame steer that leaves the five earlier steps in the history untouched; a gesture after an undo clearing the redo history; a cancelled steer recording nothing; and a result that followed a steered vector coming back with it. The tests were checked against a deliberately broken session that records every frame, and three of them fail against it.

There is no undo *gesture*: Undo is the toolbar button or Ctrl+Z. The spec lists only three hold gestures, for the same reason it has no delete gesture - a misread hand shape should not silently take back work.

### Likely questions
- **Why snapshots instead of recording each action?** With at most 10 vectors, copying everything is simpler and less error-prone than a command system.
- **Is there a gesture for undo?** No. Use the Undo button or Ctrl+Z. A misread hand shape should never take back your work without you asking.
