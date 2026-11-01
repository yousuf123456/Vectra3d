# Vectra3D — packaged app verification (F-18)

Run this for every build that is given to students. It proves the three F-18
criteria in `context/features.md`:

1. the `.exe` runs on a machine without Python,
2. the model is bundled and the app works fully with the internet off,
3. every G1–G5 criterion still passes when run from the `.exe`.

It is one guided session, not a list of seventy separate checks: each step
says which criteria it proves. A few criteria cannot differ between the
source and the `.exe`; they are listed at the end with what proves them
instead.

## Where to run it

A **second Windows laptop that has never had Python**, like a student's -
not the development machine. Run it twice:

- **Session A — with the camera.** Everything below except Session B.
- **Session B — without a camera.** Only Session B.

Before starting: build and zip with the commands in `CLAUDE.md`, and run
`uv run pytest` on the same commit - it must pass. Then build the installer
(the last command there). Get `Vectra3D-0.1.0-setup.exe` - and the zip, the
fallback - onto the laptop by **downloading** them: a downloaded file is what
makes Windows show the SmartScreen warning a student will see.

(Windows Sandbox works too, with a `.wsb` file setting `<Networking>Disable`
and `<VideoInput>` to `Enable` or `Disable`. It cannot show SmartScreen,
because files mapped in from the host are not marked as downloaded. A `.wsb`
holds an absolute path on the development machine, so none is kept in this
repository.)

Tick each box as you go. Anything that fails: stop, note what happened, and
report it rather than carrying on.

---

## Session A — with the camera

### A0. Clean machine, no internet, install, first launch
- [ ] In PowerShell, `python --version` is **not** a working Python (an
      error, or an offer to install it from the Store). *(F-18 criterion 1)*
- [ ] Download `Vectra3D-0.1.0-setup.exe` (and the zip, to check it too).
      Then **turn the internet off** (Wi-Fi off, cable out) and leave it
      off for both sessions. The taskbar's network icon shows no
      connection. *(F-18 criterion 2)*
- [ ] Run the setup file. If Windows shows "Windows protected your PC",
      **More info** then **Run anyway** gets past it: shown / not shown ______.
- [ ] Setup asks for **no administrator password**, offers the folder
      (default under `AppData\Local\Programs\Vectra3D`) and a desktop
      shortcut, and finishes with "Launch Vectra3D" ticked.
- [ ] On launch, the **loading window** (icon, "Vectra3D", a changing
      "Loading ..." line) appears within a few seconds: ______ s. It gives
      way to the main window: ______ s from the click. The window has the
      app icon on it and on the taskbar. *(F-18 criteria 1 and 2)*
- [ ] Vectra3D is in the Start menu, with "Vectra3D - read me first" beside
      it; the note reads correctly in Notepad.
- [ ] *(Zip fallback.)* Extract All on the zip: the `Vectra3D` folder holds
      `Vectra3D.exe`, `Read me first.txt` and `_internal`, and the `.exe`
      starts the same way.

### A1. The scene — F-01
- [ ] x, y, z axes drawn and labelled in red, green, blue, with the origin
      and a grid.
- [ ] Drag to rotate, scroll (or right-drag) to zoom, Shift-drag (or middle-drag) to pan.
- [ ] **Reset view** returns to the default angle.

### A2. Creating by typing — F-04, global vector rules
- [ ] Toggle between **Components (x, y, z)** and **Magnitude + angles**.
- [ ] Try: an empty field, `abc`, `3,5`, and `0, 0, 0`. Each shows an error
      and creates nothing.
- [ ] Create `(3, 4, 0)` in components, then `r = 5, θ = 90, φ = 90` in
      magnitude + angles. They appear as **A** and **B**, B exactly on +y,
      each becoming the active vector (highlighted) as it is made.
- [ ] Create `(0, 0, 5)` as **C**. The three colours are all different, and
      none is red, green, blue or the result's near-black.

### A3. The info panel and selection — F-11, F-05a, F-12
- [ ] Each card shows name, colour swatch, components, magnitude, α β γ,
      unit vector and lock state, to 2 decimals, never `-0.00`.
- [ ] C `(0, 0, 5)` reads α = 90.00°, β = 90.00°, γ = 0.00°, unit `(0.00,
      0.00, 1.00)`. A reads magnitude 5.00. *(F-12)*
- [ ] Clicking a card makes that vector active; exactly one is active.
- [ ] Each card has a tick box for multi-select, separate from being active.

### A4. Editing, locking, deleting — F-08, F-09a, F-10
- [ ] Make A active and edit it to `(1, 2, 2)` with **Apply**. The arrow
      and card change at once; magnitude reads 3.00.
- [ ] Lock A. The card shows it locked, the edit form is greyed, and
      A's delete button is disabled.
- [ ] A can still be ticked and can still show its components.
- [ ] Unlock A. Delete B. Create a new vector: it is named **B** again
      (lowest free letter).
- [ ] Lock one vector, then **Clear all**: the prompt says locked vectors
      are removed too. Cancel it for now.

### A5. Components and shadows — F-13a, F-14
- [ ] Turn on A's components: red, green and blue arrows along the axes,
      dashed lines, an outline box, and values labelled in the view.
- [ ] Turn on A's shadows: its projection on each of the three planes.
- [ ] Edit A: components and shadows follow.

### A6. Undo and redo — F-19 (panel)
- [ ] **Undo** and **Redo** are in the toolbar; `Ctrl+Z` and `Ctrl+Y` work
      too (with no text field focused).
- [ ] Undo steps back through a create, an edit, a lock and a delete, in
      order; redo brings them back.
- [ ] Toggling components or shadows is **not** undone.
- [ ] After undoing, make a new change: Redo is now greyed.

### A7. Operations — F-15, F-16, global result rules
- [ ] Tick A and B, press **Resultant**. A near-black arrow labelled
      `A + B` appears, and the panel lists it with components, magnitude,
      angles and unit vector.
- [ ] **Show how**: the vectors slide head to tail, the resultant is drawn,
      it pauses, and they slide back. Afterwards A and B read exactly as
      before.
- [ ] Edit A: the result glides to its new value.
- [ ] `[ A ] − [ B ]` replaces the sum with `A − B`. Choosing the same
      vector on both sides gives the zero vector with a note.
- [ ] **Save as vector** turns the result into the next lettered vector.
- [ ] Make a result from A, then delete A: the result disappears.
- [ ] With ten vectors, **Save as vector** is disabled with a message.

### A8. Ten vectors — limits
- [ ] Create vectors until there are ten (A–J). An eleventh by typing is
      refused with the limit message. *(F-04)*

### A9. The camera — F-02
- [ ] The camera strip under the 3D view shows your picture mirrored,
      with the hand's points drawn on it.
- [ ] It names the gesture you are making, or says "No hand detected".
- [ ] Steering shows the grab point and a line to your hand.

### A10. Gestures — F-03, F-05b, F-06, F-07, F-09b, F-13b, F-19, F-20
Clear all, then work at a normal laptop distance, leaning in, and sitting
back. Hold your hands palms towards the camera.

- [ ] **Create** (F-03): pinch both hands close together and pull apart.
      A vector follows the line between your hands live, and on release
      gets the next letter and becomes active. With ten vectors, the
      gesture shows the limit message instead.
- [ ] **Resize** (F-07): pinch with the hands apart. The length changes,
      not the direction, and freezes on release.
- [ ] **Steer** (F-06): pinch one hand and drag. A still hand keeps the
      vector still. Up raises the head towards +z from any view; keep going
      and it passes over the top. Right always spins it the same way round.
      Magnitude never changes. Release freezes it.
- [ ] **Snap** (F-06): release within 5° of an axis or plane - the strip
      says "release to snap to ..." first, then it lands exactly and the
      halo flashes.
- [ ] **Cancel**: while steering, an open palm with the *other* hand puts
      the vector back exactly.
- [ ] **Settings** (F-20): turn **Snapping** off - no hint, no snap. Change
      **Magnitude sensitivity** - a full stretch now creates a different
      length.
- [ ] **Holds** (F-05b, F-09b, F-13b): each fires once after half a second,
      with the ring filling round the hand. `Pointing_Up` makes the next
      unlocked vector active; `Thumb_Up` locks and unlocks; `Victory` shows
      and hides components, which then follow the vector as a hand moves it.
- [ ] **Locked** (F-09b): a locked vector ignores resize and steer, and the
      strip says "Vector A is locked."
- [ ] **Undo** (F-19): one create, resize or steer is one Undo step.

### A11. Closing and relaunching
- [ ] Close the window: it closes cleanly, with no error dialog.
- [ ] Launch again from the Start menu: the main window appears faster than
      the first time: ______ s.
- [ ] *(After both sessions.)* Settings > Apps > Vectra3D > **Uninstall**
      removes it, its folder and its shortcuts.

---

## Session B — without a camera

- [ ] Close the app. Switch the camera off in **Device Manager**: Cameras
      (or Imaging devices) → right-click the webcam → **Disable device**.
      Internet still off.
- [ ] Launch Vectra3D from the Start menu. The camera strip says "No webcam found.
      Everything still works from the panels." Nothing crashes.
      *(F-02 criterion 4, proven with a real missing camera)*
- [ ] Create a vector by typing and run a resultant: everything works from
      the panels.
- [ ] Re-enable the webcam in Device Manager afterwards.

---

## Not rechecked by hand here

| Criterion | Why not | What proves it |
|---|---|---|
| F-12, F-15, F-16 "automated tests pass" | Tests run against the source, not the `.exe` | `uv run pytest` on the commit the build was made from |
| F-19 "keeps the last 20 steps" | Twenty-one changes by hand prove nothing the test does not | `tests/state/test_undo.py` on the same commit |
| F-02 "tracking does not slow the 3D view" | A measurement needs the profiling script and the source | The G5 review measurement (`progress-tracker.md`, 2026-09-26); on this laptop, judge by eye in A9-A10 that nothing freezes |

## Result

| Session | Date | Laptop | Build commit | SmartScreen shown | Launch time (first / second) | Result |
|---|---|---|---|---|---|---|
| A | | | | | | |
| B | | | | | | |
