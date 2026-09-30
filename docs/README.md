# Vectra3D — How It Works

These documents explain Vectra3D for **people**: the developer, professors, and students. They are not agent instructions (those live in `context/`).

## How to use these documents
Every topic is written in layers, so you can pick the depth that fits your audience:

- **In plain words:** for students, non-technical listeners, and quick demos. No formulas.
- **Technically:** the math, algorithms, and design reasoning, for professors and technical questions.
- **How it's implemented:** where and how the topic lives in the actual code. Written by the agent after each approved build step, so it always matches the real code.
- **Likely questions:** questions audiences tend to ask, with short answers.

## Documents

| File | Covers |
|---|---|
| [01-vector-math.md](01-vector-math.md) | Coordinate system, components, magnitude, angles, unit vector, resultant, subtraction, scaling, projections |
| [02-hand-tracking.md](02-hand-tracking.md) | How the webcam sees hands, landmarks, pinch detection, smoothing, privacy |
| [03-gestures-and-interaction.md](03-gestures-and-interaction.md) | Gesture state machine, creating, resizing, steering, snapping, hold gestures, undo |
| [04-software-design.md](04-software-design.md) | Why these libraries, how the code is organized, threads, testing, packaging |

## The one-minute explanation
Vectra3D turns 3D vectors into something students can hold. A webcam watches the student's hands; a machine-learning model finds 21 points on each hand, many times per second, entirely on the laptop. The app turns simple hand shapes, mostly pinches, into actions: pull two pinched hands apart to create a vector, pinch one hand and drag to steer it. Every vector is drawn in a 3D scene the student can rotate, and every number (components, magnitude, angles) updates live as the vector moves. Anything done by hand can also be done precisely by typing, so the app works as both an exploration tool and an exact calculator.

## Keeping these documents accurate
- Concept sections were written during planning, before any code existed.
- After each approved build step, the agent fills in or updates the matching **How it's implemented** sections and corrects any concept section the real implementation changed.
- Before presenting, check the "How it's implemented" sections are filled in for the features you'll show.
