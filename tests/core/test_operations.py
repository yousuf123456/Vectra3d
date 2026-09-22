"""Resultant, subtraction and scalar multiplication (F-15, F-16, F-17).

Every expected value here is worked out by hand. The examples are chosen so the
arithmetic closes exactly - whole numbers, and magnitudes that come out whole -
so results can be asserted as exact equality rather than approximately. Where a
test is about exactness itself (vectors cancelling to zero), exact equality is
the point of the test and `pytest.approx` would hide the fault.
"""

from __future__ import annotations

import math

import pytest

from vectra3d.core.operations import resultant, scale, subtract
from vectra3d.core.vector_math import Triple, magnitude, unit_vector

ZERO: Triple = (0.0, 0.0, 0.0)

# Tolerance for the few checks that compare a derived quantity rather than the
# components themselves, such as a magnitude relationship.
TOLERANCE = 1e-12


def _added_one_at_a_time(vectors: list[Triple]) -> float:
    """Add up the x components in a loop: what `resultant` would do without fsum.

    Deliberately not `sum`, which since Python 3.12 compensates as it goes and
    so is far less order-sensitive than writing the addition out.
    """
    total = 0.0
    for vector in vectors:
        total = total + vector[0]
    return total


class TestResultant:
    def test_two_vectors(self) -> None:
        # (1+4, 2+5, 3+6)
        assert resultant([(1.0, 2.0, 3.0), (4.0, 5.0, 6.0)]) == (5.0, 7.0, 9.0)

    def test_three_vectors_one_along_each_axis(self) -> None:
        vectors: list[Triple] = [(1.0, 0.0, 0.0), (0.0, 2.0, 0.0), (0.0, 0.0, 3.0)]
        assert resultant(vectors) == (1.0, 2.0, 3.0)

    def test_ten_vectors(self) -> None:
        # The tenth vector is the limit a scene can hold. 1 + 2 + ... + 10 = 55,
        # so the components are (55, 110, -55).
        vectors: list[Triple] = [
            (float(i), float(2 * i), float(-i)) for i in range(1, 11)
        ]
        assert resultant(vectors) == (55.0, 110.0, -55.0)

    def test_vectors_that_cancel_give_exactly_zero(self) -> None:
        # F-15 names this case. Exact equality, not approx: a resultant that is
        # nearly zero still reports a magnitude and three direction angles.
        assert resultant([(3.0, -4.0, 5.0), (-3.0, 4.0, -5.0)]) == ZERO

    def test_order_does_not_change_the_result(self) -> None:
        # This is what fsum is here for. A resultant sums a *set* of ticked
        # vectors, which has no order, and the docs tell the student the order
        # does not matter.
        #
        # The two orders below are the same seven vectors. Adding their
        # components one at a time gives a different answer for each order;
        # fsum gives 1.5, which is right. The components are ordinary numbers
        # at the scale the app runs at, not contrived ones.
        #
        # `_added_one_at_a_time` is written out rather than using the builtin
        # `sum`, which since Python 3.12 does its own compensated summation and
        # would hide most of the difference. Comparing against `sum` is how
        # this test first failed to show a real effect.
        components = [0.1, 0.2, 0.3, 100.7, -100.7, 0.4, 0.5]
        one_order: list[Triple] = [(x, 0.0, 0.0) for x in components]
        another_order: list[Triple] = [
            (x, 0.0, 0.0) for x in [0.1, 0.2, 0.3, 100.7, 0.4, -100.7, 0.5]
        ]

        assert resultant(one_order) == (1.5, 0.0, 0.0)
        assert resultant(one_order) == resultant(another_order)

        # The example really is order-sensitive, so the test cannot quietly
        # stop testing anything if the components are ever edited.
        assert _added_one_at_a_time(one_order) != _added_one_at_a_time(another_order)

    def test_a_vector_and_its_negative_cancel_exactly(self) -> None:
        # Worth stating plainly: this is exact because equal floats subtract
        # exactly, not because of fsum. fsum does not make 0.1 + 0.2 - 0.3 zero
        # either - those three floats do not add up to zero, and nothing that
        # sums them can say otherwise.
        a: Triple = (0.1, 0.2, 0.3)
        negated: Triple = (-0.1, -0.2, -0.3)
        assert resultant([a, negated]) == ZERO

    def test_no_vectors_gives_the_zero_vector(self) -> None:
        assert resultant([]) == ZERO

    def test_one_vector_gives_that_vector_back(self) -> None:
        assert resultant([(1.5, -2.5, 3.5)]) == (1.5, -2.5, 3.5)

    def test_accepts_a_tuple_as_well_as_a_list(self) -> None:
        # Each axis is summed in its own pass, so the argument is read three
        # times. Any sequence works; an iterator would not.
        assert resultant(((1.0, 2.0, 3.0), (4.0, 5.0, 6.0))) == (5.0, 7.0, 9.0)


class TestSubtract:
    def test_hand_calculated(self) -> None:
        # (5-1, 7-2, 9-3)
        assert subtract((5.0, 7.0, 9.0), (1.0, 2.0, 3.0)) == (4.0, 5.0, 6.0)

    def test_negative_components(self) -> None:
        # (2-(-3), -4-1, 0-(-5))
        assert subtract((2.0, -4.0, 0.0), (-3.0, 1.0, -5.0)) == (5.0, -5.0, 5.0)

    def test_reversing_the_order_negates_the_answer(self) -> None:
        # F-16 names this: A - B = -(B - A).
        a: Triple = (1.0, 2.0, 3.0)
        b: Triple = (4.0, 6.0, 8.0)
        forward = subtract(a, b)
        backward = subtract(b, a)
        assert forward == tuple(-component for component in backward)

    def test_a_vector_minus_itself_is_exactly_zero(self) -> None:
        # Awkward values on purpose: equal floats subtract exactly.
        a: Triple = (0.1, 0.2, 0.3)
        assert subtract(a, a) == ZERO

    def test_subtracting_from_the_zero_vector_negates(self) -> None:
        assert subtract(ZERO, (1.0, -2.0, 3.0)) == (-1.0, 2.0, -3.0)


class TestScale:
    @pytest.mark.parametrize(
        ("k", "v", "expected"),
        [
            (2.0, (1.0, 2.0, 3.0), (2.0, 4.0, 6.0)),
            (-1.0, (1.0, 2.0, 3.0), (-1.0, -2.0, -3.0)),
            (-3.0, (1.0, -2.0, 0.0), (-3.0, 6.0, -0.0)),
            (0.5, (2.0, 4.0, 6.0), (1.0, 2.0, 3.0)),
            (0.25, (8.0, -4.0, 0.0), (2.0, -1.0, 0.0)),
        ],
    )
    def test_hand_calculated(self, k: float, v: Triple, expected: Triple) -> None:
        # F-17 names positive, negative and fractional k.
        assert scale(k, v) == expected

    def test_k_of_one_changes_nothing(self) -> None:
        assert scale(1.0, (1.5, -2.5, 3.5)) == (1.5, -2.5, 3.5)

    def test_k_of_zero_gives_the_zero_vector(self) -> None:
        # F-17 names this. Components compare equal to zero whatever their sign;
        # -0.0 == 0.0 is true, and formatting already refuses to print "-0.00".
        assert scale(0.0, (3.0, -4.0, 5.0)) == ZERO

    def test_scaling_the_zero_vector_gives_the_zero_vector(self) -> None:
        assert scale(7.0, ZERO) == ZERO

    def test_negative_k_reverses_the_direction(self) -> None:
        # Checked through the unit vector rather than by eye: the direction is
        # exactly opposite, not merely different.
        v: Triple = (1.0, 2.0, 2.0)  # magnitude 3, so the unit vector is exact
        forward = unit_vector(v)
        backward = unit_vector(scale(-2.0, v))
        assert forward is not None and backward is not None
        assert backward == tuple(-component for component in forward)

    @pytest.mark.parametrize("k", [2.0, -2.0, 0.5, -0.5, 0.0])
    def test_magnitude_scales_by_the_size_of_k(self, k: float) -> None:
        # |k v| = |k| |v|, cross-checked against vector_math.
        v: Triple = (2.0, 3.0, 6.0)  # magnitude 7
        assert magnitude(scale(k, v)) == pytest.approx(abs(k) * 7.0, abs=TOLERANCE)


class TestResultsThatAreNotFinite:
    """Finite input can still overflow, so the result is checked, not assumed."""

    def test_scaling_a_large_vector_by_a_large_number_is_refused(self) -> None:
        with pytest.raises(ValueError, match="scalar multiplication"):
            scale(1e308, (10.0, 0.0, 0.0))

    def test_adding_large_vectors_is_refused(self) -> None:
        with pytest.raises(ValueError, match="resultant"):
            resultant([(1e308, 0.0, 0.0), (1e308, 0.0, 0.0), (1e308, 0.0, 0.0)])

    def test_subtracting_large_vectors_is_refused(self) -> None:
        with pytest.raises(ValueError, match="subtraction"):
            subtract((-1e308, 0.0, 0.0), (1e308, 0.0, 0.0))

    @pytest.mark.parametrize("bad", [math.inf, -math.inf, math.nan])
    def test_input_that_is_not_finite_is_refused(self, bad: float) -> None:
        # Typed input is guarded already, but core does not rely on that.
        with pytest.raises(ValueError):
            scale(2.0, (bad, 0.0, 0.0))
        with pytest.raises(ValueError):
            resultant([(bad, 0.0, 0.0), (1.0, 0.0, 0.0)])
        with pytest.raises(ValueError):
            subtract((bad, 0.0, 0.0), (1.0, 0.0, 0.0))

    def test_opposite_infinities_are_refused_rather_than_becoming_nan(self) -> None:
        with pytest.raises(ValueError, match="resultant"):
            resultant([(math.inf, 0.0, 0.0), (-math.inf, 0.0, 0.0)])

    def test_the_largest_finite_result_is_allowed_through(self) -> None:
        # The guard refuses what overflows, not what is merely large.
        assert scale(2.0, (1e308 / 2.0, 0.0, 0.0)) == (1e308, 0.0, 0.0)
