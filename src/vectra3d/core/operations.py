"""Combining vectors: addition, subtraction and scaling.

The three operations `features.md` gives group G3 (F-15, F-16, F-17), as pure
arithmetic on component triples. Nothing here knows a vector's name or colour,
and nothing here builds the temporary result the student sees - that is G3.2's
job, where the expression label and the reserved colour belong with the object
that carries them.

Three things about how these are calculated are worth knowing.

**Sums use `math.fsum`, not `+`** - though not for the reason it first looks
like. `fsum` does *not* make decimal-looking values cancel: 0.1 + 0.2 - 0.3 is
2.78e-17 with it and 5.55e-17 without, because those three floats genuinely do
not add up to zero. F-15's "vectors that cancel to zero" case is A + (-A), and
that is exactly zero either way, since equal floats cancel exactly.

What `fsum` buys is that **the answer does not depend on the order the vectors
happen to be in**. Adding the components one at a time, which is what this
function would otherwise do, gives 20 different answers for the seven
components 0.1, 0.2, 0.3, 100.7, -100.7, 0.4 and 0.5 depending on the order
they arrive in - ordinary numbers at the scale the app runs at, not contrived
ones. `fsum` is exactly rounded, so it gives one answer, 1.5, which is the
right one. A resultant is the sum of a *set* of ticked vectors, which has no
meaningful order, and `docs/01-vector-math.md` tells the student outright that
the order does not matter - a promise adding one at a time cannot keep.

Note the comparison there is against adding the components up in a loop, not
against Python's builtin `sum`, which since 3.12 does its own compensated
summation and would have hidden most of the difference. That mistake was made
once while this module was being written; it is recorded here so it is not made
again. This is otherwise the same reasoning that put `math.hypot` in
`vector_math.py`: where the values are scalars rather than an array, take the
correctly rounded function.

**A result that is not finite is refused, not returned.** Scalar
multiplication reaches infinity from input the app accepts as perfectly finite
- a large vector times a large k - and addition does the same near the float
limit. An infinity returned quietly would travel into the scene sizing and fail
there instead, far from what caused it. Raising here matches `parse_number`,
which refuses nan and inf where numbers are typed, and `extent_for`, which
raises rather than searching forever. The check also catches a value that
arrives non-finite, because infinity propagates through the arithmetic; `core`
does not assume its caller guarded anything.

**NumPy is absent**, as it is in `vector_math.py`. `architecture.md` section 1
gives NumPy the vector maths, and these three scalars are not what that rule is
for. The departure is deliberate and matches the module next door; NumPy stays
the rule wherever the data is genuinely array-shaped.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from vectra3d.core.vector_math import Triple


def resultant(vectors: Sequence[Triple]) -> Triple:
    """The sum of any number of vectors, added component by component.

    A `Sequence` rather than an iterable, because each axis is summed in its
    own pass and an iterator would be empty by the second.

    Any count is allowed: no vectors give the zero vector, one gives that
    vector back. F-15's rule that the student must pick two or more belongs to
    the panel, not here - the same split as `create_vector`, which accepts a
    zero vector that typed input refuses.
    """
    return _checked(
        (
            _axis_sum(vectors, 0),
            _axis_sum(vectors, 1),
            _axis_sum(vectors, 2),
        ),
        "resultant",
    )


def _axis_sum(vectors: Sequence[Triple], axis: int) -> float:
    """Add one axis across every vector, as a finite number or as inf or nan.

    `math.fsum` does not overflow to infinity the way plain addition does. It
    raises `OverflowError` when the total is too large, and `ValueError` for
    inf + -inf, so a total that is not finite never reaches `_checked` on its
    own. Turning each case back into the value it means keeps every refusal in
    `_checked`, with one message, rather than splitting the rule in two.
    """
    try:
        return math.fsum(vector[axis] for vector in vectors)
    except OverflowError:
        return math.inf
    except ValueError:
        return math.nan


def subtract(a: Triple, b: Triple) -> Triple:
    """`a - b`, component by component.

    Subtracting a vector from itself gives exactly the zero vector, because
    floating-point subtraction of equal values is exact.
    """
    return _checked((a[0] - b[0], a[1] - b[1], a[2] - b[2]), "subtraction")


def scale(k: float, v: Triple) -> Triple:
    """`k * v`: every component multiplied by the same number.

    A negative k reverses the direction and keeps the line; k of 0 gives the
    zero vector. F-17 asks the panel to note both of those for the student,
    which it can do from the value it passed in.
    """
    return _checked((k * v[0], k * v[1], k * v[2]), "scalar multiplication")


def _checked(components: Triple, operation: str) -> Triple:
    """Return the components, or raise if any of them is not a finite number.

    Named after the operation so the message says what overflowed rather than
    only that something did.
    """
    if not all(math.isfinite(component) for component in components):
        raise ValueError(f"{operation} has no finite result for these values")
    return components
