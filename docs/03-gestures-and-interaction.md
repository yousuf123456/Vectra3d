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
*To be filled in by the agent after step G5.2.*

### Likely questions
- **Why not control everything with hands?** Some actions are simply faster and more accurate with a click. The aim is learning vectors, not fighting the interface.

---

## 2. The gesture state machine

### In plain words
The app is always in exactly one "mode": idle, creating, resizing, steering, or holding a gesture. What your hands do next decides which mode comes next. This stops two gestures from fighting over the same vector.

### Technically
A finite state machine with states IDLE, CREATING, RESIZING, STEERING, and HOLDING.
- A two-hand pinch (second hand pinching within 0.3 s of the first) beats a one-hand pinch.
- Hold gestures are recognized only in IDLE.
- An open palm during any pinch gesture cancels it and restores the vector exactly.
- Losing a hand for more than 0.3 s counts as a normal release.
- The state machine outputs **intents** ("begin create," "update," "commit," "cancel") rather than changing vectors itself; the app turns intents into the same actions the panel uses.

### How it's implemented
*To be filled in by the agent after step G5.2.*

### Likely questions
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
*To be filled in by the agent after step G5.3.*

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
*To be filled in by the agent after steps G2.8 and G5.9.*

### Likely questions
- **Why snapshots instead of recording each action?** With at most 10 vectors, copying everything is simpler and less error-prone than a command system.
