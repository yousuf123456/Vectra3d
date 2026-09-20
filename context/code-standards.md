# Vectra3D — Code Standards

Rules for every line of code in the project. Structure and layers are in `architecture.md`; library-specific rules are in `library-docs.md`.

---

## 1. Write only the code that is needed
- Build only what the current step's acceptance criteria require. No extra features, options, or "might be useful later" code.
- **Use library features instead of writing custom code** whenever the library already does the job (e.g. PyVista's arrows, labels, and camera controls; Qt's widgets and settings storage; NumPy's vector operations).
- No speculative abstractions: no base classes, plugin systems, or configuration layers unless a feature needs them now.
- No unused functions, parameters, imports, or commented-out code. Delete dead code rather than keeping it.
- Handle the errors the specs describe (invalid input, no webcam, zero vector), not imaginary ones.
- **Exception:** things the context files explicitly require for the future, such as the vector tail position (`project-overview.md`), are required, not extra.

## 2. Respect the layers
- Follow the layers and folder structure in `architecture.md`. A layer may only import from layers below it.
- `core` and `gestures` never import Qt, PyVista, OpenCV, or MediaPipe.
- Vector data lives only in `state`. Every change goes through `state/actions.py`, whether it comes from the panel or from gestures.
- Do not add a library that is not listed in `architecture.md` section 1 without asking first.

## 3. Style
- Type hints on all functions. Dataclasses for data.
- Small, single-purpose modules and short functions.
- No global mutable state.
- Every tunable value from `interaction-spec.md` section 9 lives in `config.py`, never as a magic number in the code.
- Keep full precision internally; round only in `core/formatting.py`.
- Guard every division by magnitude against the zero vector.

## 4. Tests
- All vector math and gesture logic gets automated pytest tests with hand-calculated expected values, runnable without the UI or a webcam (see `architecture.md` section 5).
- Write tests alongside the code in the same step, not later.
- All tests must pass before a step is reported as done. Never delete, skip, or weaken a test to make it pass.
