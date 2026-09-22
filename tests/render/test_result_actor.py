"""Drawing the temporary result, and the transition it slides along.

No window is opened here. What is tested is the part that can be worked out
as numbers: where the expression label sits, how the scene is sized to fit a
result, and where the arrow is partway through a transition. How the arrow
actually looks is judged by rendering the scene off screen and reading the
image, as adopted at G2.6.
"""

from __future__ import annotations

import pytest

from vectra3d.render.animations import interpolate
from vectra3d.render.result_actor import label_position
from vectra3d.render.scene import extent_for_vectors
from vectra3d.state.models import Result, Vector


def result(components: tuple[float, float, float], expression: str = "A + B") -> Result:
    return Result(
        expression=expression, components=components, sources=("A", "B")
    )


class TestLabelPosition:
    def test_the_label_sits_past_the_head_along_the_result(self) -> None:
        # A result of (10, 0, 0) is labelled a little further out than 10,
        # on its own line, so the label cannot land on the arrow.
        x, y, z = label_position(result((10.0, 0.0, 0.0)))
        assert x > 10.0
        assert (y, z) == (0.0, 0.0)

    def test_the_offset_is_proportional_to_the_result(self) -> None:
        # Twice as long, twice as far past the head, so the gap looks the
        # same at any size - the same rule as a vector's letter.
        near = label_position(result((10.0, 0.0, 0.0)))[0] - 10.0
        far = label_position(result((20.0, 0.0, 0.0)))[0] - 20.0
        assert far == pytest.approx(near * 2.0)

    def test_a_zero_result_labels_the_origin(self) -> None:
        # Vectors that cancel give the zero vector, which has no direction to
        # offset along. The label has nowhere to go but the origin.
        assert label_position(result((0.0, 0.0, 0.0))) == (0.0, 0.0, 0.0)


class TestTheSceneFitsTheResult:
    def test_a_result_longer_than_its_vectors_makes_the_scene_grow(self) -> None:
        # Two vectors of 8 fit in the smallest scene; their sum of 16 does
        # not. `interaction-spec.md` section 3 sizes the scene to any vector
        # *or the current result*.
        vectors = [
            Vector(name="A", components=(8.0, 0.0, 0.0)),
            Vector(name="B", components=(8.0, 0.0, 0.0)),
        ]
        assert extent_for_vectors(vectors) == 10
        assert extent_for_vectors(vectors, result((16.0, 0.0, 0.0))) == 20

    def test_a_result_inside_the_vectors_changes_nothing(self) -> None:
        vectors = [Vector(name="A", components=(30.0, 0.0, 0.0))]
        assert extent_for_vectors(vectors, result((1.0, 0.0, 0.0))) == 50

    def test_no_result_is_the_same_as_before(self) -> None:
        vectors = [Vector(name="A", components=(3.0, 0.0, 0.0))]
        assert extent_for_vectors(vectors, None) == extent_for_vectors(vectors)


class TestInterpolate:
    START = (0.0, 0.0, 0.0)
    END = (10.0, -20.0, 4.0)

    def test_progress_of_zero_is_the_start(self) -> None:
        assert interpolate(self.START, self.END, 0.0) == self.START

    def test_progress_of_one_is_the_end(self) -> None:
        assert interpolate(self.START, self.END, 1.0) == self.END

    def test_halfway(self) -> None:
        assert interpolate(self.START, self.END, 0.5) == (5.0, -10.0, 2.0)

    def test_it_moves_from_wherever_it_started(self) -> None:
        assert interpolate((2.0, 2.0, 2.0), (4.0, 6.0, 10.0), 0.5) == (3.0, 4.0, 6.0)

    @pytest.mark.parametrize("progress", [-0.5, 1.5, 2.0])
    def test_progress_outside_the_range_is_clamped(self, progress: float) -> None:
        # An easing curve can overshoot. The arrow must not fly past where it
        # is going and come back.
        moved = interpolate(self.START, self.END, progress)
        assert moved in (self.START, self.END)
