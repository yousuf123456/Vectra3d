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
*To be filled in by the agent after step G5.4.*

### Likely questions
- **How does it know whether I want to create or resize?** By how far apart your hands are when you pinch: together means create, apart means resize.

---

## 5. Steering: the joystick

### In plain words
Pinch with one hand and hold. The spot where you pinched becomes the center of an invisible joystick. Nudge your hand right, and the arrow swings right; nudge it up, and the arrow tilts up. The farther you move from the center, the faster it turns. Small shakes near the center are ignored.

### Technically
- **Rate control, not position control:** hand offset from the anchor sets angular *speed*, not the angle itself. This hides jitter and avoids tiring, large arm movements.
- Offset d (in hs) → speed ω = ω_max × clamp((d − d₀) / (d_max − d₀), 0, 1), with dead zone d₀ = 0.3 hs, d_max = 1.5 hs, ω_max = 90°/s.
- **Screen-relative:** the rotation axes come from the 3D camera's current orientation. Horizontal offset rotates around the camera's *up* direction; vertical offset rotates around its *right* direction. So "right" always means right on screen, even when viewing the scene from behind.
- Each frame rotates the vector by angle Δ = ω·Δt around unit axis **u** using **Rodrigues' rotation formula**:
  **v**′ = **v** cos Δ + (**u** × **v**) sin Δ + **u**(**u** · **v**)(1 − cos Δ)
- Rotations preserve length, so magnitude never changes while steering.

### How it's implemented
*To be filled in by the agent after step G5.5.*

### Likely questions
- **Why a joystick instead of pointing where I want?** Pointing needs accurate depth, which one webcam can't give. The joystick only needs left/right/up/down.
- **Why does it rotate relative to the screen?** If rotation followed fixed world axes, moving your hand right could move the arrow left on screen when the view is rotated, which feels broken.

---

## 6. Snapping

### In plain words
While steering, the arrow gently "clicks" onto an axis or a flat plane when it gets close, making it easy to point exactly along x or lie exactly flat.

### Technically
- Angle to an axis **a**: arccos(|**v** · **a**| / |**v**|). Angle to a plane with normal **n**: arcsin(|**v** · **n**| / |**v**|).
- Snaps in below 5°, releases above 8°: hysteresis again, so it doesn't flicker at the boundary.
- Axis snaps take priority over plane snaps. Snapping can be turned off in settings.

### How it's implemented
*To be filled in by the agent after step G5.6.*

### Likely questions
- **Can I avoid snapping for an angle like 3° off the axis?** Turn snapping off in settings, or type the exact value in the panel.

---

## 7. Hold gestures

### In plain words
Three hand signs trigger actions if you hold them for half a second: pointing up selects the next vector, thumbs up locks or unlocks it, and a peace sign shows or hides its components. A ring fills up in the camera view while you hold, so you can see it coming.

### Technically
- Recognized with MediaPipe's built-in gesture classifier: `Pointing_Up`, `Thumb_Up`, `Victory`.
- Must be recognized continuously for 0.5 s with confidence of at least 0.6, triggers once, and re-arms only after the hand changes shape.
- There is deliberately no delete gesture: a misread gesture should never destroy work.

### How it's implemented
*To be filled in by the agent after step G5.8.*

### Likely questions
- **Why the half-second wait?** It stops hand shapes you pass through by accident from triggering actions.

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
