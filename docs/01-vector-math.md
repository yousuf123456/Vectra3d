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
*To be filled in by the agent after step G1.2.*

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
*To be filled in by the agent after steps G1.1 and G2.6.*

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
*To be filled in by the agent after step G1.3.*

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
*To be filled in by the agent after step G1.3.*

### Likely questions
- **Why might a value show 4.99 when I expect 5?** Converting angles to components involves sin and cos, which produce tiny floating-point errors. Full precision is kept internally, so this only affects display, and rounding to 2 decimals usually hides it.
