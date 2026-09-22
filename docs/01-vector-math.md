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

**Looking at the scene from different angles.** The toolbar has **Reset view**, which returns to the default three-quarter angle, and **Front**, **Right** and **Top**, which look straight down the y, x and z axes. Those three matter more than they sound: seen from an angle, a vector leaning towards x looks much like one leaning towards y, and the only way to be sure is to remove the perspective. Looking down an axis does exactly that — the axis facing you shrinks to a point and the other two are seen true, so the view becomes an ordinary 2D graph you can read values off.

The camera is placed by hand rather than through PyVista's built-in `view_xy` and friends, which reframe themselves around whatever is currently in the scene. That would make the zoom lurch every time a vector was created or deleted. Placing it keeps every view at the same distance with z upwards, so switching between them feels like walking around one fixed object rather than being teleported.

How far back the camera sits is worked out from the camera's own lens angle, so that the whole world — out to the axis letters, which sit a little past the tips — is inside the picture. It used to be a fixed multiple of the extent, and that number was too small for its own scene: the axes were cut off before their tips and the x and z letters were off-screen entirely. Nobody noticed until the preset views arrived, because an angled view foreshortens everything towards the middle and hid it.

**Where the numbers sit.** Each axis decides for itself, for the current view, which way to push its numbers clear of its line. The rule is a cross product of the axis direction with the direction the camera is looking, which gives a direction perpendicular to the axis that lies flat in the plane of the screen — "sideways from this line, as the student sees it". The sign is chosen so the numbers hang below their axis, the way they do on a printed graph; an axis drawn up and down the screen has no below, so its numbers go to the left instead.

This replaced a fixed choice — x numbers always towards −y, y and z always towards −x — which was right for the default view and wrong for every other. Turned around, it pushed the x numbers across the vector; seen edge-on, it piled them into each other. An axis pointing within about 12° of the camera is hidden altogether, numbers and letter: it is a single point on screen, so there is nothing to read along it, and drawing its twenty numbers would stack them all on the origin in one unreadable smudge. The positions are recalculated as the view is dragged, so the numbers keep up with it.

### Likely questions
- **Why is z up and not y?** Physics and engineering textbooks usually draw z up. Some computer graphics tools use y up, but matching the students' course matters more.
- **What does "right-handed" mean and why does it matter?** It fixes which way +z points relative to x and y. With the opposite (left-handed) choice, cross products would point the wrong way, so it matters for the planned cross-product feature.
- **Why does an axis disappear when I look straight down it?** Because there is nothing left of it to see. Pointing at you, it is a dot, and its numbers would all land on the origin together. Hiding it is what turns the top view into a clean XY graph. Turn the view slightly and it comes straight back.
- **Why do the numbers move when I rotate the view?** They are staying out of the way. Each one sits just off its axis on the side that happens to be clear from where you are looking, and that side changes as you move.

---

## 2. Position vectors and components

### In plain words
A vector is an arrow with a length and a direction. In Vectra3D every arrow starts at the origin, like a flagpole planted in the corner of the room. Its **components** are how far you'd walk along x, then along y, then up along z to reach the arrow's tip.

### Technically
A position vector **v** = (x, y, z) = x**i** + y**j** + z**k**, where **i**, **j**, **k** are the unit vectors along the axes. Its tail is at the origin and its head at the point (x, y, z).

When components are shown, the app draws three arrows along the axes (x red, y green, z blue), dashed projection lines, and a box outline whose opposite corner is the vector's head. This shows visually that the vector is the diagonal of a box with side lengths x, y, and z. **One vector shows its components at a time** — switching it on for one turns it off for whichever had it.

The data model also stores a tail position (always the origin for now), so "free vectors" placed anywhere can be added later.

### How it's implemented
*The data model was built in step G1.1; the drawing of components in 3D in step G2.6.*

A vector is a `Vector` in `src/vectra3d/state/models.py`: a name, its components, and its tail, each stored as a plain `(x, y, z)` tuple of floats. The tail defaults to `ORIGIN`, which is `(0.0, 0.0, 0.0)`. It is stored on every vector rather than assumed, so that free vectors can be added later without changing everything that reads a vector.

`Vector` is a **frozen** dataclass, which means it cannot be edited in place. Changing a vector creates a replacement. That sounds inconvenient but buys two things: undo can save the whole scene by copying a dictionary of vectors rather than copying each one deeply, and no part of the app can change a vector without going through `state/actions.py`.

Each vector is drawn in the 3D view by `src/vectra3d/render/vector_actor.py` as an arrow from its tail, with its letter at the head in its own color. The **active** vector — the one the panel and, later, the student's hands act on — is wrapped in a translucent copy of itself, which reads as a glow around it. Drawing it thicker was tried first and dropped: thickness would then mean two things at once, and it matters more once the component arrows arrive.

A zero vector has no arrow, because it has no direction to point in. It still exists, still has its name and its row in the info panel. This is not a hypothetical: from G3 a student can save `A − B` as a vector, and that can be zero.

`src/vectra3d/render/overlays.py` draws the components. The box is the cuboid with the vector as its space diagonal, and only **nine** of its twelve edges are drawn dashed: the other three run along the axes from the tail, and those are the component arrows. A vector lying in a coordinate plane flattens the cuboid to a rectangle, where opposite faces coincide and the duplicates are dropped; a vector lying along an axis collapses it to a line, and no box is drawn at all. PyVista has no dashed-line style, so each dash is real geometry — about 72 short segments per box, batched into one mesh so the whole box stays a single actor.

Only one vector shows its components at a time, and the store holds *which* vector rather than a set of them, so there is no state in which two are shown. The reason is that every vector resolves onto the same three axes: two at once means two arrows of the same colour lying on the same line, with their value labels crowding the same corner.

Making the component arrows readable took three attempts, all judged by rendering the scene and looking at it. They were invisible at first, because their thickness was scaled to each component's own length — a component is shorter than its vector, so its shaft came out thinner than the axis line it sits on, and it read as part of the axis. Thickness is now worked out from the vector's magnitude, so all three match each other. Made thick enough to see, they then looked more important than the vector itself; they are now held back by being flat-shaded and partly transparent instead of thin, so they read as workings drawn onto the scene rather than objects in it. Below about 0.9 thickness and 0.45 opacity they vanish into the axes again.

The value labels sit four fifths of the way along their own arrow, away from the tail where all four arrows converge. The x and y values are lifted in z, because the axis tick numbers hang below their axis lines, and the z value is pushed out sideways, away from whichever quadrant the vector leans into. Offsetting into two negative axes at once was tried first and reads as no offset at all from many angles, because the two displacements cancel in projection and the label lands back on the origin.

**Projections (G2.7).** A separate overlay in the same file draws a vector's three shadows: on the XY plane it keeps its x and y and loses its height, on YZ it loses its depth, on XZ its width. Each shadow is an arrow from the origin, in the vector's own colour, with a dashed line dropping from the vector's head to the shadow's tip — without that line the three read as three more vectors sharing the origin rather than as one vector seen from three sides. A vector already lying in a plane is its own shadow there, and a vector along an axis casts nothing at all on the plane perpendicular to it, so no arrow and no drop line are drawn for that plane.

Shadows are drawn fainter than the component arrows, which looks inconsistent and is not. A component arrow lies along an axis and is fixed to that axis's colour, so it needs bulk to be told apart from the axis; a shadow is in its own vector's colour, which nothing else in the scene uses, so it can be faint and still read. Components and projections are switched on separately, so a vector can show both.

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
`magnitude()` in `core/vector_math.py` takes the three components and returns the length.

It calls Python's `math.hypot(x, y, z)` rather than writing out `sqrt(x*x + y*y + z*z)`, and rather than NumPy's `linalg.norm`, which is what the rest of the project uses for vector maths. The reason is that the obvious formula squares each component before adding them, and squaring is where the arithmetic falls apart at the extremes. A vector with components around 10²⁰⁰ squares to infinity, so the answer comes back as infinity even though the real length is a perfectly ordinary number. At the other end, components around 10⁻²⁰⁰ square to zero, so a real vector is reported as having no length at all. `math.hypot` is built to avoid both, and it is also *correctly rounded*, meaning it gives the closest possible answer every time: `hypot(3, 4, 0)` is exactly `5.0`, not `4.999999999999999`.

That exactness is why the tests in `tests/core/test_vector_math.py` use examples whose arithmetic closes: (3, 4, 0) has magnitude 5, (1, 2, 2) has 3, and (2, 3, 6) has 7. The magnitudes can then be checked as exact equality rather than "close enough".

### Likely questions
- **Why is it Pythagoras twice?** The floor diagonal forms a right triangle with the vertical side z, so the 2D theorem applies a second time.
- **What are the units?** Unitless. The app is about the geometry, so "units" can stand for metres, newtons, or anything else.
- **Would a student ever type a vector big enough to overflow?** Almost certainly not — it takes components above about 10¹⁵⁴. The guard is there because it costs nothing and because the same function will later be handed the output of operations like scalar multiplication, where a large vector times a large number can reach those sizes without anyone typing them.

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
`direction_angles()` in `core/vector_math.py` returns the three angles in degrees, as a tuple in the order α, β, γ. For the zero vector it returns `None` instead — see the unit vector section below, which does the same thing for the same reason.

Each angle is worked out by the small helper `_angle_with_axis()`, which divides one component by the magnitude and takes `math.acos` of the result, converting from radians to degrees with `math.degrees`. Because `acos` naturally returns an angle between 0 and 180°, the range the maths requires comes for free; nothing has to fold or correct it.

The one subtlety is the line that clamps the ratio into the range −1 to 1 before `acos` sees it. Arc cosine is only defined on that range, and Python's `math.acos` does not return a nonsense value outside it — it raises `ValueError: math domain error`, which would crash the app. A vector lying exactly on an axis, such as (5, 0, 0), has a true ratio of exactly 1, which sits right on the boundary. Floating-point division does not always land exactly where the algebra says it will, and a result one step past 1 would be enough. The clamp costs one comparison and removes the possibility entirely. It cannot hide a genuine error either, because a ratio of a component to its own vector's magnitude can never legitimately exceed 1.

### Likely questions
- **Why do the squared cosines always add to 1?** Substitute the formulas: (x² + y² + z²) / |**v**|² = |**v**|² / |**v**|² = 1.
- **Is that identity actually checked?** Yes. `tests/core/test_vector_math.py` asserts it for a spread of vectors, including one on an axis and one at the extreme end of the number range. It is a useful test because it would catch a mistake in any one of the three angles.
- **If I know two angles, do I know the third?** Almost: the identity gives cos²γ, which fixes γ up to a choice between two angles (above or below the XY plane). That's why all three are shown.

---

## 5. Unit vector

### In plain words
The unit vector is the same arrow shrunk (or stretched) to length exactly 1. It keeps only the direction and throws away the size.

### Technically
**û** = **v** / |**v**| = (cos α, cos β, cos γ)

The components of the unit vector are exactly the direction cosines.

### How it's implemented
`unit_vector()` in `core/vector_math.py` divides each component by the magnitude and returns the three results as a tuple. For the zero vector it returns `None`.

That `None` is the main design decision in this step. The alternative was to return the special floating-point value `nan` ("not a number"), which is what the arithmetic itself would produce from dividing zero by zero. `None` was chosen because it forces the rest of the app to notice. A `nan` looks like a number to every piece of code that receives it, passes silently through additions and comparisons, and only surfaces much later somewhere unrelated — which is exactly what happened earlier in this project, when a typed "nan" reached the code that sizes the scene and locked the window up with no error message. `None` cannot do that: the code that displays a unit vector has to handle the empty case before it can show anything, and that is where the "—" described above comes from.

The same applies to `direction_angles()`, and both functions decide it the same way, by checking whether the magnitude is exactly zero before dividing by it.

### Likely questions
- **Why does the zero vector have no unit vector?** Dividing by a magnitude of 0 is undefined; a zero-length arrow points nowhere. The app shows "—" and a note instead of a number.
- **Does scaling a vector change its direction angles?** No, and the tests check it: the angles of a vector and the angles of its unit vector come out the same. That is the point of a unit vector — it keeps the direction and discards the length.

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
*The conversion into components was built in step G1.3; the inverse, reading an existing vector's r, θ and φ, in step G2.4.*

`src/vectra3d/core/spherical.py` holds `to_components(r, θ, φ)`, which is the three formulas above and nothing else. `normalize_phi()` brings any φ into 0–360° first, so typing 370 gives the same vector as 10, and −90 the same as 270.

The two angles are treated differently on purpose. **φ is normalized silently**, because every value of it means something once wrapped into a turn. **θ is rejected outside 0–180°**, because outside that range it is not defined at all — the form says so rather than quietly wrapping it and creating a vector pointing somewhere the student did not ask for.

Typing is checked when **Create** is pressed rather than keystroke by keystroke, so a student who writes `3,5` is told to use a dot instead of having the comma silently refused. Those checks are plain functions in `ui/action_panel.py`, separate from the widgets, which is how they are tested without opening a window.

`to_spherical(x, y, z)` (G2.4) goes the other way, and is what fills the **Edit vector** form when it shows an existing vector in "magnitude + angles" mode. It does not compute θ itself: the angle from the +z axis *is* the direction angle γ from section 4, so it asks `vector_math.direction_angles` for it. That is not only tidiness — that function already clamps the ratio before `arccos` sees it, and without the clamp a vector lying exactly on the z axis can crash the app (section 4 explains why).

φ raises a small problem the info panel does not have. On the z axis it is undefined, and a card can simply print "—"; an input box cannot, because whatever it holds has to be read back when **Apply** is pressed. So the box shows `0.00` and a line underneath says *"φ has no effect while the vector points along z."* That is honest: section 2.3 of the spec treats a typed φ as irrelevant there, so any value would do, and zero is the least surprising one.

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
`resultant()` in `core/operations.py` (G3.1) takes any number of vectors as plain (x, y, z) tuples and returns their sum as another tuple. It knows nothing about vector names, colours or the screen — that arrives with the temporary result in G3.2.

It adds each axis with **`math.fsum`** rather than with `+`. This is worth explaining, because the obvious reason is the wrong one. `fsum` does *not* rescue decimals that look like they should cancel: 0.1 + 0.2 − 0.3 comes to about 2.8 × 10⁻¹⁷ either way, because those three values are not stored exactly in the first place and genuinely do not add up to zero. What `fsum` guarantees is that the answer **doesn't depend on the order the vectors are added in**. Adding seven ordinary components one at a time — 0.1, 0.2, 0.3, 100.7, −100.7, 0.4, 0.5 — produces 20 slightly different answers depending on their order; `fsum` always returns 1.5, which is correct. Since a resultant adds a *set* of ticked vectors, which has no natural order, that promise matters, and the first "Likely question" below depends on it.

The function also **refuses to return a result that isn't a finite number**. Multiplying or adding very large vectors can reach infinity even though every number that went in was ordinary, and an infinity travelling quietly onward would fail somewhere far away from the cause. Instead all three operations raise an error naming the operation, which the panel turns into a message.

*The temporary result object, its colour and its live updates are added in G3.2; the head-to-tail animation in G3.3.*

### Likely questions
- **Does the order of vectors matter?** No. Any order ends at the same point; the animation's path changes shape, but the resultant doesn't. The app takes some care to keep this literally true down to the last decimal place — see "How it's implemented" above.
- **What if the numbers get astronomically large?** The operation refuses rather than returning infinity, and the panel says so. It takes components beyond roughly 10³⁰⁸ to trigger, so no ordinary work will meet it.
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
The arithmetic is `subtract(a, b)` in `core/operations.py`, built in G3.1: it returns `a − b` component by component, and like the other two operations refuses a result that isn't finite.

One detail is free rather than designed. Subtracting a vector from itself gives *exactly* the zero vector, with no leftover dust, because subtracting two identical floating-point values is always exact. That is what makes "picking the same vector in both dropdowns gives the zero vector" reliable rather than approximately true.

*The two dropdowns and the note shown for A − A are added in G3.4.*

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
`scale(k, v)` in `core/operations.py` (G3.1) multiplies each component by k. The tests check the promise made just above — that |k**A**| really does come to |k| · |**A**| — and that a negative k reverses the direction *exactly*, by comparing unit vectors rather than by eye.

Scalar multiplication is the one operation that can reach infinity from values a student could plausibly type, since a large vector times a large k overflows where addition would not. `scale` refuses such a result rather than returning infinity.

*The vector dropdown, the k field, and the notes shown for k = 0 and negative k are added in G3.5.*

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
*Built across steps G1.3, G1.4 and G2.3.*

Nothing is rounded or snapped when a vector is stored. A vector typed as r = 1, θ = 90°, φ = 90° keeps an x of 6.1e-17 rather than a tidy zero, because that genuinely is cos(90°) in floating point. Rounding it at the point of storage would be a small lie that later calculations would inherit; rounding it only when it is shown gives "0.00" on screen with the true value still underneath.

`core/formatting.py` is where that rounding happens, and it is the only place it happens. `format_number()` gives two decimals and turns anything that rounds to zero into "0.00", so a component like that 6.1e-17, or a −0.001, never appears as "−0.00". Values that survive rounding keep their sign as normal: −0.006 still shows as −0.01.

`format_angle()` does the same for angles, adding the degree sign, and `format_triple()` writes the unit vector as one bracketed value. Both take the *absence* of a value as well as a value: the maths hands back nothing at all for a zero vector's direction, and these turn that into the em dash. Doing it here rather than in the panel means the rule lives in one place and no display code has to ask whether a vector happens to be zero.

That the maths returns nothing, rather than a number meaning "nothing", is what makes this safe. A special numeric value would look like a real number to every piece of code it passed through and would surface much later somewhere unrelated — which is exactly what happened earlier in this project, when a typed "nan" reached the code that sizes the scene and locked the window up.

### Likely questions
- **Why does the zero vector show "0.00" for its length but a dash for everything else?** Its length genuinely is zero, which is a number. Its direction does not exist at all — an arrow with no length points nowhere — so there is nothing to round and nothing to print.
- **Why might a value show 4.99 when I expect 5?** Converting angles to components involves sin and cos, which produce tiny floating-point errors. Full precision is kept internally, so this only affects display, and rounding to 2 decimals usually hides it.
