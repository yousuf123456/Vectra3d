"""Magnitude, direction angles and the unit vector (`interaction-spec.md` 2.4).

Every expected value here is worked out by hand, from examples chosen because
their arithmetic closes exactly: 3-4-5 gives a magnitude of 5, (1, 2, 2) gives
3, and (2, 3, 6) gives 7. That means the magnitudes can be asserted as exact
equality rather than approximately, and the cosines are simple fractions whose
arccos can be checked against a table.
"""

from __future__ import annotations

import math

import pytest

from vectra3d.core.vector_math import (
    Triple,
    direction_angles,
    direction_cosine_sum,
    from_direction_angles,
    magnitude,
    unit_vector,
)

# Angles are compared to eight decimal places. The values below are the
# textbook ones, and nothing in the app displays more than two decimals.
ANGLE_TOLERANCE = 1e-8


class TestMagnitude:
    @pytest.mark.parametrize(
        ("components", "expected"),
        [
            ((3.0, 4.0, 0.0), 5.0),  # 9 + 16 = 25
            ((1.0, 2.0, 2.0), 3.0),  # 1 + 4 + 4 = 9
            ((2.0, 3.0, 6.0), 7.0),  # 4 + 9 + 36 = 49
            ((0.0, 0.0, 0.0), 0.0),
            ((5.0, 0.0, 0.0), 5.0),
            ((0.0, -4.0, 0.0), 4.0),
        ],
    )
    def test_hand_calculated(
        self, components: tuple[float, float, float], expected: float
    ) -> None:
        assert magnitude(components) == expected

    def test_sign_does_not_matter(self) -> None:
        assert magnitude((-3.0, -4.0, 0.0)) == 5.0

    def test_very_large_components_do_not_overflow(self) -> None:
        # numpy.linalg.norm squares the components first, so it returns inf
        # here from input that is perfectly finite. math.hypot does not.
        result = magnitude((1e200, 1e200, 1e200))
        assert math.isfinite(result)
        assert result == pytest.approx(math.sqrt(3) * 1e200)

    def test_very_small_components_do_not_underflow(self) -> None:
        # The same squaring underflows to zero at the bottom of the range,
        # which would report a real vector as having no length at all.
        result = magnitude((1e-200, 1e-200, 1e-200))
        assert result > 0.0
        assert result == pytest.approx(math.sqrt(3) * 1e-200)


class TestDirectionAngles:
    def test_three_four_five(self) -> None:
        # |v| = 5, so cos a = 3/5 = 0.6, cos b = 4/5 = 0.8, cos c = 0.
        alpha, beta, gamma = direction_angles((3.0, 4.0, 0.0))
        assert alpha == pytest.approx(53.13010235, abs=ANGLE_TOLERANCE)
        assert beta == pytest.approx(36.86989765, abs=ANGLE_TOLERANCE)
        assert gamma == pytest.approx(90.0, abs=ANGLE_TOLERANCE)

    def test_one_two_two(self) -> None:
        # |v| = 3, so cos a = 1/3 and cos b = cos c = 2/3.
        alpha, beta, gamma = direction_angles((1.0, 2.0, 2.0))
        assert alpha == pytest.approx(70.52877937, abs=ANGLE_TOLERANCE)
        assert beta == pytest.approx(48.18968510, abs=ANGLE_TOLERANCE)
        assert gamma == pytest.approx(48.18968510, abs=ANGLE_TOLERANCE)

    def test_two_three_six(self) -> None:
        # |v| = 7, so the cosines are 2/7, 3/7 and 6/7.
        alpha, beta, gamma = direction_angles((2.0, 3.0, 6.0))
        assert alpha == pytest.approx(73.39845040, abs=ANGLE_TOLERANCE)
        assert beta == pytest.approx(64.62306647, abs=ANGLE_TOLERANCE)
        assert gamma == pytest.approx(31.00271913, abs=ANGLE_TOLERANCE)

    @pytest.mark.parametrize(
        ("components", "expected"),
        [
            ((5.0, 0.0, 0.0), (0.0, 90.0, 90.0)),
            ((-5.0, 0.0, 0.0), (180.0, 90.0, 90.0)),
            ((0.0, 4.0, 0.0), (90.0, 0.0, 90.0)),
            ((0.0, -4.0, 0.0), (90.0, 180.0, 90.0)),
            ((0.0, 0.0, 2.5), (90.0, 90.0, 0.0)),
            ((0.0, 0.0, -2.5), (90.0, 90.0, 180.0)),
        ],
    )
    def test_along_each_axis(
        self,
        components: tuple[float, float, float],
        expected: tuple[float, float, float],
    ) -> None:
        # A vector on an axis makes 0 degrees with it, 180 with the opposite
        # direction, and a right angle with the other two. This is the case
        # where the cosine reaches exactly 1 or -1, the edge of arccos.
        angles = direction_angles(components)
        assert angles is not None
        for angle, want in zip(angles, expected):
            assert angle == pytest.approx(want, abs=ANGLE_TOLERANCE)

    def test_the_zero_vector_has_no_direction(self) -> None:
        assert direction_angles((0.0, 0.0, 0.0)) is None

    @pytest.mark.parametrize(
        "components",
        [
            (3.0, 4.0, 0.0),
            (1.0, 2.0, 2.0),
            (-7.5, 0.25, 11.0),
            (5.0, 0.0, 0.0),
            (1e200, 1e200, 1e200),
        ],
    )
    def test_cosines_square_to_one(
        self, components: tuple[float, float, float]
    ) -> None:
        # The identity every set of direction angles must satisfy:
        # cos^2 a + cos^2 b + cos^2 c = 1.
        angles = direction_angles(components)
        assert angles is not None
        total = sum(math.cos(math.radians(angle)) ** 2 for angle in angles)
        assert total == pytest.approx(1.0)

    @pytest.mark.parametrize(
        "components",
        [
            (3.0, 4.0, 0.0),
            (-7.5, 0.25, 11.0),
            (0.0, 0.0, -2.5),
            (1e-200, 1e-200, 1e-200),
        ],
    )
    def test_every_angle_is_within_zero_to_180(
        self, components: tuple[float, float, float]
    ) -> None:
        angles = direction_angles(components)
        assert angles is not None
        assert all(0.0 <= angle <= 180.0 for angle in angles)

    def test_no_angle_is_ever_nan(self) -> None:
        # arccos returns nan one ulp outside [-1, 1], and a nan reaching the
        # scene froze the app once already. Components far apart in size are
        # where a ratio could round above 1.
        for components in [
            (1.0, 1e-17, 0.0),
            (1e150, 1.0, -1.0),
            (1e-150, 1e-300, 0.0),
        ]:
            angles = direction_angles(components)
            assert angles is not None
            assert not any(math.isnan(angle) for angle in angles)


class TestUnitVector:
    def test_three_four_five(self) -> None:
        assert unit_vector((3.0, 4.0, 0.0)) == (0.6, 0.8, 0.0)

    def test_one_two_two(self) -> None:
        x, y, z = unit_vector((1.0, 2.0, 2.0))
        assert x == pytest.approx(1 / 3)
        assert y == pytest.approx(2 / 3)
        assert z == pytest.approx(2 / 3)

    def test_direction_is_kept_and_sign_survives(self) -> None:
        assert unit_vector((0.0, -4.0, 0.0)) == (0.0, -1.0, 0.0)

    def test_a_vector_already_of_length_one_is_unchanged(self) -> None:
        assert unit_vector((1.0, 0.0, 0.0)) == (1.0, 0.0, 0.0)

    @pytest.mark.parametrize(
        "components",
        [
            (3.0, 4.0, 0.0),
            (1.0, 2.0, 2.0),
            (-7.5, 0.25, 11.0),
            (1e200, 1e200, 1e200),
            (1e-200, 1e-200, 1e-200),
        ],
    )
    def test_the_result_always_has_magnitude_one(
        self, components: tuple[float, float, float]
    ) -> None:
        unit = unit_vector(components)
        assert unit is not None
        assert magnitude(unit) == pytest.approx(1.0)

    def test_the_zero_vector_has_no_unit_vector(self) -> None:
        assert unit_vector((0.0, 0.0, 0.0)) is None

    def test_the_angles_of_the_unit_vector_match_the_originals(self) -> None:
        # Scaling a vector must not change the direction it points in.
        components = (-7.5, 0.25, 11.0)
        original = direction_angles(components)
        unit = unit_vector(components)
        assert original is not None
        assert unit is not None
        scaled = direction_angles(unit)
        assert scaled is not None
        for angle, want in zip(scaled, original):
            assert angle == pytest.approx(want, abs=ANGLE_TOLERANCE)


class TestFullPrecisionIsKept:
    def test_nothing_is_rounded(self) -> None:
        # `interaction-spec.md` 2.2: rounding happens only when a value is
        # displayed. A tenth of a degree would survive rounding to two
        # decimals, so this would be visible in the info panel.
        alpha, _, _ = direction_angles((1.0, 2.0, 2.0))
        assert alpha != round(alpha, 2)

    def test_the_input_is_not_changed(self) -> None:
        components = (3.0, 4.0, 0.0)
        magnitude(components)
        direction_angles(components)
        unit_vector(components)
        assert components == (3.0, 4.0, 0.0)


class TestFromDirectionAngles:
    """|v| (cos alpha, cos beta, cos gamma): the form's "Magnitude + angles"."""

    def test_a_textbook_example(self) -> None:
        # |A| = 10, alpha 60, beta 45, gamma 120: cosines 1/2, 1/sqrt 2, -1/2,
        # whose squares add up to exactly 1. So A = (5, 7.07, -5).
        assert direction_cosine_sum(60.0, 45.0, 120.0) == pytest.approx(1.0)
        assert from_direction_angles(10.0, 60.0, 45.0, 120.0) == pytest.approx(
            (5.0, 10.0 / math.sqrt(2.0), -5.0)
        )

    @pytest.mark.parametrize(
        ("angles", "want"),
        [
            ((0.0, 90.0, 90.0), (4.0, 0.0, 0.0)),
            ((90.0, 0.0, 90.0), (0.0, 4.0, 0.0)),
            ((90.0, 90.0, 0.0), (0.0, 0.0, 4.0)),
            ((180.0, 90.0, 90.0), (-4.0, 0.0, 0.0)),
            ((90.0, 180.0, 90.0), (0.0, -4.0, 0.0)),
            ((90.0, 90.0, 180.0), (0.0, 0.0, -4.0)),
        ],
    )
    def test_along_each_axis_the_other_components_are_exactly_zero(
        self, angles: Triple, want: Triple
    ) -> None:
        # cos 90 is 6e-17 in floating point; typed 90 means exactly square.
        assert from_direction_angles(4.0, *angles) == want

    def test_three_angles_that_do_not_fit_together_show_in_the_sum(self) -> None:
        # 60 degrees from every axis: three quarters, not 1.
        assert direction_cosine_sum(60.0, 60.0, 60.0) == pytest.approx(0.75)

    def test_rounded_angles_still_give_exactly_the_typed_length(self) -> None:
        # The diagonal's angles are 54.7356...; typed as 54.7 they miss the
        # identity by about 0.003, and the cosines are scaled to fit.
        assert abs(direction_cosine_sum(54.7, 54.7, 54.7) - 1.0) < 0.01
        assert magnitude(from_direction_angles(6.0, 54.7, 54.7, 54.7)) == pytest.approx(
            6.0, abs=1e-12
        )

    def test_the_angles_come_back_out(self) -> None:
        angles = direction_angles(from_direction_angles(10.0, 60.0, 45.0, 120.0))
        assert angles == pytest.approx((60.0, 45.0, 120.0))
