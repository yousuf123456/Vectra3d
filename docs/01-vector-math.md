# 01 — Vector Math

All the mathematics Vectra3D computes and displays. Every result here is shown live in the info panel.

---

## 1. The coordinate system

### In plain words
Imagine the corner of a room. One edge of the floor is the **x axis** (red), the other floor edge is the **y axis** (green), and the vertical edge going up the wall is the **z axis** (blue). The corner itself is the **origin**, the point (0, 0, 0). Every vector in the app starts at this corner.

### Technically
- **Right-handed** system with **z up**: if the fingers of your right hand curl from +x toward +y, your thumb points along +z. This matches most physics textbooks.
- The scene starts at −10 to 10 on each axis and grows in a 1-2-5 sequence (10, 20, 50, 100, …) when a vector goes beyond it, then shrinks back when it can. It only rescales after a movement ends, never during one, so a vector never seems to shrink under the student's hand.

### How it's implemented
*Built in step G1.2.*

`src/vectra3d/render/scene.py` draws the world. The floor is a grid of plain line segments on the XY plane, and the three axes run right through the origin from −extent to +extent, each with an arrowhead, a letter, tick marks and numbers at its positive and negative ends. A small dark sphere marks the origin. The x, y and z colors here are the same ones the component arrows use later, so a red arrow always means "along x" wherever it appears.

**Scene extent** is the half-width of the world: how far the grid and axes reach. `extent_for()` returns the smallest step of the 1-2-5 sequence that fits the furthest component of any vector, never going below 10. Nothing remembers the extent from before, so shrinking needs no separate rule: delete the long vector and the answer is simply small again.

The scene is redrawn whenever the vectors change. That is exactly when the spec allows rescaling, because a gesture in progress does not change the stored vectors — only releasing it does — so the world can never resize under the student's hand.

Everything in the scene is sized as a fraction of the extent, including how far away the camera sits. The geometry and the camera therefore change in the **same frame**. An earlier version redrew the grid at once and slid the camera out over 300 ms to catch up, which meant the world really was ten times too big for that third of a second: the origin dot swelled to fill the view and the grid shot off the edges of the screen. Changed together, the grid keeps its ten divisions at a proportional distance, so its lines land in almost the same pixels and what visibly changes is the numbers on the axes — which is the part the student needs to notice.

### Likely questions
- **Why is z up and not y?** Physics and engineering textbooks usually draw z up. Some computer graphics tools use y up, but matching the students' course matters more.
- **What does "right-handed" mean and why does it matter?** It fixes which way +z points relative to x and y. With the opposite (left-handed) choice, cross products would point the wrong way, so it matters for the planned cross-product feature.

---

## 2. Position vectors and components

### In plain words
A vector is an arrow with a length and a direction. In Vectra3D every arrow starts at the origin, like a flagpole planted in the corner of the room. Its **components** are how far you'd walk along x, then along y, then up along z to reach the arrow's tip.

### Technically
A position vector **v** = (x, y, z) = x**i** + y**j** + z**k**, where **i**, **j**, **k** are the unit vectors along the axes. Its tail is at the origin and its head at the point (x, y, z).

When components are shown, the app draws three arrows along the axes (x red, y green, z blue), dashed projection lines, and a box outline whose opposite corner is the vector's head. This shows visually that the vector is the diagonal of a box with side lengths x, y, and z.

The data model also stores a tail position (always the origin for now), so "free vectors" placed anywhere can be added later.

### How it's implemented
*The data model was built in step G1.1. The drawing of components in 3D comes in step G2.6 and will be added here then.*

A vector is a `Vector` in `src/vectra3d/state/models.py`: a name, its components, and its tail, each stored as a plain `(x, y, z)` tuple of floats. The tail defaults to `ORIGIN`, which is `(0.0, 0.0, 0.0)`. It is stored on every vector rather than assumed, so that free vectors can be added later without changing everything that reads a vector.

`Vector` is a **frozen** dataclass, which means it cannot be edited in place. Changing a vector creates a replacement. That sounds inconvenient but buys two things: undo can save the whole scene by copying a dictionary of vectors rather than copying each one deeply, and no part of the app can change a vector without going through `state/actions.py`.

Each vector is drawn in the 3D view by `src/vectra3d/render/vector_actor.py` as an arrow from its tail, with its letter at the head in its own color. The **active** vector — the one the panel and, later, the student's hands act on — is wrapped in a translucent copy of itself, which reads as a glow around it. Drawing it thicker was tried first and dropped: thickness would then mean two things at once, and it matters more once the component arrows arrive.

A zero vector has no arrow, because it has no direction to point in. It still exists, still has its name and its row in the info panel. This is not a hypothetical: from G3 a student can save `A − B` as a vector, and that can be zero.

Names and colors live in `src/vectra3d/state/naming.py`. Vectors are named A to J, and a new vector always takes the lowest free letter, so deleting B makes the next new vector B again. Each letter owns a fixed color from a palette of ten, so the color is worked out from the name rather than stored on the vector. A reused letter therefore comes back in the color the student already associates with that row.

Choosing those ten took three attempts, because red, green and blue are all reserved for the axes and the component arrows, and that leaves a narrow band to fit ten distinguishable colors into. Separating them by hue alone produced two olives and two teals; separating same-family pairs by lightness was still hard to read at a glance. The palette in use now takes colors from a set designed for maximum contrast with each other and keeps only those safely clear of the three axis colors, so no two vectors share a color family.

### Likely questions
- **Why are all vectors fixed at the origin?** Position vectors keep the first version simple and match how they're first taught. Free vectors are planned as a later feature.
- **Can a component be negative?** Yes. A negative component just means walking in the negative direction along that axis; the component arrow then points the other way.

---

## 3. Magnitude

### In plain words
The magnitude is the arrow's length: how far the tip is from the corner of the room, measured in a straight line.

### Technically
|**v**| = √(x² + y² + z²)

This is Pythagoras applied twice: √(x² + y²) is the diagonal across the floor, and combining that with z gives the diagonal through the box.

### How it's implemented
*To be filled in by the agent after step G2.1.*

### Likely questions
- **Why is it Pythagoras twice?** The floor diagonal forms a right triangle with the vertical side z, so the 2D theorem applies a second time.
- **What are the units?** Unitless. The app is about the geometry, so "units" can stand for metres, newtons, or anything else.

---

## 4. Direction angles (α, β, γ)

### In plain words
Three angles describe which way the arrow points: how far it leans away from the x axis (α), from the y axis (β), and from the z axis (γ). An arrow pointing straight up has γ = 0°, because it isn't leaning away from the z axis at all.

### Technically
cos α = x / |**v**|,  cos β = y / |**v**|,  cos γ = z / |**v**|

These cosines are called the **direction cosines**, and they always satisfy:

cos²α + cos²β + cos²γ = 1

Each angle is between 0° and 180°. The app displays angles in degrees with 2 decimals.

### How it's implemented
*To be filled in by the agent after step G2.1.*

### Likely questions
- **Why do the squared cosines always add to 1?** Substitute the formulas: (x² + y² + z²) / |**v**|² = |**v**|² / |**v**|² = 1.
- **If I know two angles, do I know the third?** Almost: the identity gives cos²γ, which fixes γ up to a choice between two angles (above or below the XY plane). That's why all three are shown.

---

## 5. Unit vector

### In plain words
The unit vector is the same arrow shrunk (or stretched) to length exactly 1. It keeps only the direction and throws away the size.

### Technically
**û** = **v** / |**v**| = (cos α, cos β, cos γ)

The components of the unit vector are exactly the direction cosines.

### How it's implemented
*To be filled in by the agent after step G2.1.*

### Likely questions
- **Why does the zero vector have no unit vector?** Dividing by a magnitude of 0 is undefined; a zero-length arrow points nowhere. The app shows "—" and a note instead of a number.

---

## 6. Spherical angles (r, θ, φ)

### In plain words
Another way to describe a vector: how long it is (r), how far it tips away from straight up (θ), and which compass direction it faces on the floor (φ). This is the "magnitude + angles" option when typing a vector.

### Technically
Physics convention:
- **r** = |**v**|
- **θ** = angle from the +z axis, 0° to 180°: θ = arccos(z / r)
- **φ** = angle in the XY plane from +x toward +y, 0° to 360°: φ = atan2(y, x)

Converting back:
x = r sin θ cos φ,  y = r sin θ sin φ,  z = r cos θ

When the vector lies on the z axis (θ = 0° or 180°), φ is undefined and shown as "—".

### How it's implemented
*The conversion into components was built in step G1.3. Going the other way, showing an existing vector's r, θ and φ, comes with the full info panel in G2.3.*

`src/vectra3d/core/spherical.py` holds `to_components(r, θ, φ)`, which is the three formulas above and nothing else. `normalize_phi()` brings any φ into 0–360° first, so typing 370 gives the same vector as 10, and −90 the same as 270.

The two angles are treated differently on purpose. **φ is normalized silently**, because every value of it means something once wrapped into a turn. **θ is rejected outside 0–180°**, because outside that range it is not defined at all — the form says so rather than quietly wrapping it and creating a vector pointing somewhere the student did not ask for.

Typing is checked when **Create** is pressed rather than keystroke by keystroke, so a student who writes `3,5` is told to use a dot instead of having the comma silently refused. Those checks are plain functions in `ui/action_panel.py`, separate from the widgets, which is how they are tested without opening a window.

### Likely questions
- **Why does my textbook use different symbols?** Mathematics courses often swap θ and φ. The app uses the physics convention, which is also the international standard (ISO 80000-2).
- **Why atan2 and not arctan(y/x)?** arctan alone can't tell opposite directions apart (for example, (1, 1) and (−1, −1) give the same ratio). atan2 looks at the signs of both x and y to get the correct quadrant.

---

## 7. Resultant (vector addition)

### In plain words
The resultant is the single arrow that has the same effect as several arrows combined. Picture walking along the first arrow, then from where you stopped walking along the second, and so on. The resultant is a straight line from where you started to where you ended. The **Show how** animation plays exactly this walk.

### Technically
**R** = **A** + **B** + **C** + … = (Aₓ + Bₓ + …, A_y + B_y + …, A_z + B_z + …)

Components simply add. The head-to-tail animation slides each vector so its tail sits on the previous vector's head; the resultant runs from the origin to the last head. Addition is commutative and associative, so the order doesn't change the result, only the shape of the path.

### How it's implemented
*To be filled in by the agent after steps G3.1, G3.2, and G3.3.*

### Likely questions
- **Does the order of vectors matter?** No. Any order ends at the same point; the animation's path changes shape, but the resultant doesn't.
- **Can a resultant be zero?** Yes, when the vectors cancel out, like equal forces pulling in opposite directions.
- **Why does the result update when I move a vector?** Results are live: if an input changes, the result is recalculated and glides to its new value.

---

## 8. Subtraction

### In plain words
**A − B** is the arrow you'd add to B to get to A. If both arrows start at the corner, A − B has the same length and direction as the arrow drawn from B's tip to A's tip.

### Technically
**A − B** = **A** + (−**B**) = (Aₓ − Bₓ, A_y − B_y, A_z − B_z)

Subtraction is not commutative: **B − A** = −(**A − B**), same length, opposite direction. That's why the app uses two dropdowns, so the order is always explicit.

### How it's implemented
*To be filled in by the agent after step G3.4.*

### Likely questions
- **Why is the result drawn from the origin, not between the tips?** All vectors in this version are position vectors starting at the origin. The tip-to-tip picture becomes possible once free vectors are added.

---

## 9. Scalar multiplication

### In plain words
Multiplying by a number stretches or shrinks the arrow. Multiplying by 2 doubles its length; by 0.5 halves it; by a negative number flips it to point the opposite way.

### Technically
k**A** = (kAₓ, kA_y, kA_z),  |k**A**| = |k| · |**A**|

For k > 0 the direction is unchanged; for k < 0 it reverses; for k = 0 the result is the zero vector.

### How it's implemented
*To be filled in by the agent after step G3.5.*

### Likely questions
- **Is −1 × A the same as "A backwards"?** Yes: same length, exactly opposite direction.

---

## 10. Plane projections ("shadows")

### In plain words
Shine a light straight down on the arrow and look at its shadow on the floor: that's its projection on the XY plane. The same idea works for the two walls.

### Technically
Projections onto the coordinate planes simply drop one component:
- XY plane: (x, y, 0)
- YZ plane: (0, y, z)
- XZ plane: (x, 0, z)

A projection onto a plane is different from a component: a component lies along one axis, while a projection lies in a plane and combines two components.

### How it's implemented
*To be filled in by the agent after step G2.7.*

### Likely questions
- **What's the difference between a projection and a component?** The x component is (x, 0, 0), a single axis. The XY projection is (x, y, 0), the shadow on a whole plane.

---

## 11. Precision and display

### In plain words
The app calculates with full precision and only rounds the numbers when showing them, so rounding never builds up errors.

### Technically
- Calculations use 64-bit floating point (NumPy). Values are rounded to 2 decimals only for display.
- "−0.00" is displayed as "0.00", since a tiny negative value like −0.001 would otherwise look strange.
- The zero vector is handled explicitly: its magnitude is 0 and its direction values are shown as "—".

### How it's implemented
*Built across steps G1.3 and G1.4. The em dash shown for values the zero vector does not have comes with the full info panel in G2.3.*

Nothing is rounded or snapped when a vector is stored. A vector typed as r = 1, θ = 90°, φ = 90° keeps an x of 6.1e-17 rather than a tidy zero, because that genuinely is cos(90°) in floating point. Rounding it at the point of storage would be a small lie that later calculations would inherit; rounding it only when it is shown gives "0.00" on screen with the true value still underneath.

`core/formatting.py` is where that rounding happens, and it is the only place it happens. `format_number()` gives two decimals and turns anything that rounds to zero into "0.00", so a component like that 6.1e-17, or a −0.001, never appears as "−0.00". Values that survive rounding keep their sign as normal: −0.006 still shows as −0.01.

### Likely questions
- **Why might a value show 4.99 when I expect 5?** Converting angles to components involves sin and cos, which produce tiny floating-point errors. Full precision is kept internally, so this only affects display, and rounding to 2 decimals usually hides it.
