# Vectra3D — Project Brief

## One-line summary
Vectra3D is a Windows desktop app that lets students create, move, and analyze 3D vectors with their hands through a webcam, with an on-screen action panel as a precise fallback.

## The problem
First-year students learn 3D vectors from flat, 2D textbook diagrams. Components, direction angles, and resultants are hard to picture when you can't rotate the scene or change a vector and watch the numbers respond. Vectra3D makes vectors something students can grab, steer, and take apart, while every value updates live.

## Target users
- **Primary:** first-year university / college students.
- **Secondary:** teachers demonstrating concepts in lectures.

## How it is used
- **Self-study:** a student alone at a laptop, exploring freely.
- **Lecture demos:** a teacher stands at their own laptop and uses the app; the laptop screen is projected. The interaction is the same single-person, laptop-webcam setup as self-study.
- **Guided lab exercises:** NOT in the MVP. Planned only if the student trial is positive (see "After the MVP").

In every case: **one person, sitting or standing in front of a laptop's built-in webcam or a desk webcam.**

## Core experience
- **Hands first, panel as fallback.** Continuous, feel-based actions (creating a vector, resizing it, steering its direction) are done with hand gestures. Precise or discrete actions (selecting a specific vector, typing exact values, running operations) are done in the on-screen action panel.
- **Vectors are position vectors.** Every vector's tail is fixed at the origin in v1.
- **Every gesture has a panel equivalent.** Anything that can be done by hand can also be done in the action panel, so the app stays usable in poor lighting or when a gesture is not recognized.
- **Math is always visible.** An information panel lists every vector with its components, magnitude, and angles, updating live as vectors change.
- Full gesture definitions live in `interaction-spec.md`. Full feature list lives in `features.md`.

## MVP scope (in)
- Create vectors by hand gesture or by typed values.
- Change a vector's direction and magnitude by hand.
- Lock / unlock vectors so they cannot be changed accidentally.
- Resolve a vector into its x, y, z components and show them in 3D alongside the original vector.
- Select multiple vectors and compute / display their resultant, with a head-to-tail animation showing how they add.
- Vector subtraction. (Scalar multiplication was moved to post-MVP on 2026-09-23; see `features.md` P-06.)
- Direction angles (α, β, γ) and the unit vector for every vector.
- Projections ("shadows") of a vector on the XY, YZ, and XZ planes.
- Typed input in either components (x, y, z) or magnitude + angles, with a toggle.
- Information panel showing all vectors, their components, and operation results.
- Action panel for precise input and all operations.
- Packaged as a Windows `.exe`; students do not need Python installed.

## Non-goals for v1 (do NOT build these)
- Free vectors (tails away from the origin). Planned for later; see below.
- Guided lab exercises, challenge mode, or answer checking.
- macOS or Linux support.
- Any language other than English.
- Multi-user or multi-person hand tracking.
- Gestures that rely on moving the hand toward or away from the camera (single-webcam depth is unreliable).
- Accounts, cloud features, or online services.
- AR or overlaying vectors on the live camera image as the main view.

## After the MVP (only if the student trial is positive)
- Guided lab exercises for classes.
- Free vectors that can be placed away from the origin. The data model must already store a tail position for every vector (always the origin in v1) so this can be added without rewriting the core.
- Dot product with the angle between two vectors.
- Cross product, drawn perpendicular to both vectors (right-hand rule).
- Save / load scenes.
- Additional features marked "stretch" in `features.md`.

## Constraints
- **Language:** built in Python, using existing libraries wherever possible rather than writing things from scratch.
- **Platform:** Windows only.
- **Distribution:** packaged `.exe`; must run without a Python installation.
- **Hardware:** modern laptops from roughly the last 5 years, with a built-in or standard USB webcam. Integrated graphics only; no dedicated GPU may be assumed.
- **Interface language:** English only.
- **Network:** works offline by default. Network access is acceptable only if a specific feature truly requires it. The hand-tracking model file must be bundled with the app, not downloaded at runtime.
- **Privacy:** webcam frames are processed in memory only. They are never saved to disk and never sent anywhere. The hand-tracking library (MediaPipe) sends anonymous performance statistics to Google when online; this is disclosed to students in a first-launch notice.
- **Timeline:** no fixed deadline. The goal is a complete MVP with every feature in its scope, not a fast partial version.

## Success criteria
**The MVP is done when** a student can, without help:
1. Create a vector with a two-hand gesture and see it in 3D.
2. Steer and resize it by hand, and set exact values through the panel.
3. Lock it, show its components, and read its values in the info panel.
4. Select two or more vectors and see their resultant.
5. Do all of this from the packaged `.exe` on a Windows laptop.

**Continuing past the MVP** depends on one thing: students find it useful in a trial.
