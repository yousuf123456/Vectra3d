"""The geometry behind the two overlays: components (F-13a) and shadows (F-14).

Worked out by hand from the cuboid whose space diagonal is the vector: its
eight corners are every combination of (0 or x, 0 or y, 0 or z), and its
twelve edges join corners that differ in exactly one component. Three of those
edges run along the axes from the tail, and the component arrows draw those,
so nine are left for the dashed box.

No plotter is opened.
"""

from __future__ import annotations

import pytest

from vectra3d.render.overlays import (
    ALONG_ARROW,
    DASH_FRACTION,
    MIN_DASHES,
    box_edges,
    component_offsets,
    dash_segments,
    label_positions,
    label_text,
    projection_offsets,
)


def edge_set(components: tuple[float, float, float]) -> set[frozenset]:
    """The edges as unordered pairs, so a test does not depend on direction."""
    return {frozenset((start, end)) for start, end in box_edges(components)}


# --- The three component vectors ---


def test_a_vector_splits_into_three_axis_offsets() -> None:
    assert component_offsets((3.0, 4.0, 5.0)) == (
        (3.0, 0.0, 0.0),
        (0.0, 4.0, 0.0),
        (0.0, 0.0, 5.0),
    )


def test_negative_components_keep_their_sign() -> None:
    # The arrow points the other way along the axis; it is not flipped.
    assert component_offsets((-2.0, 0.0, -7.0)) == (
        (-2.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (0.0, 0.0, -7.0),
    )


def test_the_offsets_add_back_to_the_vector() -> None:
    components = (1.5, -2.5, 3.0)
    total = tuple(sum(offset[i] for offset in component_offsets(components))
                  for i in range(3))
    assert total == components


# --- The outline box ---


def test_a_general_vector_has_nine_dashed_edges() -> None:
    # Twelve edges of the cuboid, less the three the arrows draw.
    assert len(box_edges((3.0, 4.0, 5.0))) == 9


def test_no_dashed_edge_runs_along_an_axis_from_the_tail() -> None:
    arrows = set(component_offsets((3.0, 4.0, 5.0)))
    for start, end in box_edges((3.0, 4.0, 5.0)):
        assert not (start == (0.0, 0.0, 0.0) and end in arrows)
        assert not (end == (0.0, 0.0, 0.0) and start in arrows)


def test_every_edge_changes_exactly_one_component() -> None:
    for start, end in box_edges((3.0, 4.0, 5.0)):
        differing = sum(1 for a, b in zip(start, end) if a != b)
        assert differing == 1


def test_every_corner_of_the_box_is_reached() -> None:
    corners = {point for edge in box_edges((3.0, 4.0, 5.0)) for point in edge}
    # All eight, except the tail itself, which only the arrows touch.
    assert len(corners) == 7
    assert (3.0, 4.0, 5.0) in corners  # the head
    assert (0.0, 0.0, 0.0) not in corners


def test_the_head_is_joined_by_three_edges() -> None:
    head = (3.0, 4.0, 5.0)
    touching = [edge for edge in box_edges(head) if head in edge]
    assert len(touching) == 3


def test_a_vector_in_a_plane_has_only_the_two_far_edges() -> None:
    # z = 0 flattens the cuboid to a rectangle. Two of its four edges are the
    # arrows; the opposite face sits exactly on top and is not drawn twice.
    assert edge_set((3.0, 4.0, 0.0)) == {
        frozenset(((3.0, 0.0, 0.0), (3.0, 4.0, 0.0))),
        frozenset(((0.0, 4.0, 0.0), (3.0, 4.0, 0.0))),
    }


@pytest.mark.parametrize(
    "components", [(3.0, 4.0, 0.0), (0.0, 4.0, 5.0), (3.0, 0.0, 5.0)]
)
def test_every_coordinate_plane_flattens_the_same_way(
    components: tuple[float, float, float]
) -> None:
    assert len(box_edges(components)) == 2


@pytest.mark.parametrize(
    "components", [(3.0, 0.0, 0.0), (0.0, 4.0, 0.0), (0.0, 0.0, 5.0), (-3.0, 0.0, 0.0)]
)
def test_a_vector_on_an_axis_has_no_box_at_all(
    components: tuple[float, float, float]
) -> None:
    # The cuboid is a line, and the component arrow is already drawing it.
    assert box_edges(components) == ()


def test_the_zero_vector_has_no_box() -> None:
    assert box_edges((0.0, 0.0, 0.0)) == ()


def test_negative_components_still_give_nine_edges() -> None:
    assert len(box_edges((-2.0, 3.0, -4.0))) == 9


def test_no_edge_is_listed_twice() -> None:
    edges = box_edges((3.0, 4.0, 5.0))
    assert len(edge_set((3.0, 4.0, 5.0))) == len(edges)


# --- Dashes ---


def test_an_edge_is_cut_into_dashes() -> None:
    segments = dash_segments((0.0, 0.0, 0.0), (10.0, 0.0, 0.0), 1.0)
    assert len(segments) >= MIN_DASHES


def test_the_dashes_start_at_one_end_and_finish_at_the_other() -> None:
    segments = dash_segments((0.0, 0.0, 0.0), (10.0, 0.0, 0.0), 1.0)
    assert segments[0][0] == pytest.approx((0.0, 0.0, 0.0))
    assert segments[-1][1] == pytest.approx((10.0, 0.0, 0.0))


def test_the_dashes_leave_gaps() -> None:
    # Each drawn piece must be shorter than the step to the next one, or it
    # is a solid line.
    segments = dash_segments((0.0, 0.0, 0.0), (10.0, 0.0, 0.0), 1.0)
    drawn = segments[0][1][0] - segments[0][0][0]
    step = segments[1][0][0] - segments[0][0][0]
    assert drawn < step


def test_a_short_edge_still_reads_as_dashed() -> None:
    # Rather than rounding down to one solid stroke.
    segments = dash_segments((0.0, 0.0, 0.0), (0.2, 0.0, 0.0), 1.0)
    assert len(segments) == MIN_DASHES


def test_an_edge_of_no_length_has_no_dashes() -> None:
    assert dash_segments((1.0, 1.0, 1.0), (1.0, 1.0, 1.0), 0.5) == ()


def test_a_longer_edge_gets_more_dashes() -> None:
    short = dash_segments((0.0, 0.0, 0.0), (5.0, 0.0, 0.0), 0.2)
    long = dash_segments((0.0, 0.0, 0.0), (20.0, 0.0, 0.0), 0.2)
    assert len(long) > len(short)


def test_the_dash_size_follows_the_vector_so_proportions_hold() -> None:
    # A vector ten times longer gets dashes ten times longer, so both look
    # the same on screen - the rule the arrows already follow.
    small = dash_segments((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), 1.0 * DASH_FRACTION)
    big = dash_segments((0.0, 0.0, 0.0), (10.0, 0.0, 0.0), 10.0 * DASH_FRACTION)
    assert len(small) == len(big)


# --- Labels ---


def test_each_component_is_labelled_with_its_value() -> None:
    assert label_text((3.0, -4.0, 0.5)) == ("3.00", "-4.00", "0.50")


def test_a_label_never_shows_negative_zero() -> None:
    # Section 2.5, the same rule the info panel follows.
    assert label_text((-0.001, 0.0, 1.0))[0] == "0.00"


def test_a_zero_component_is_still_labelled() -> None:
    # There is no arrow to draw, but the answer is still zero and worth
    # saying, because a missing label looks like a missing value.
    assert label_text((3.0, 0.0, 5.0))[1] == "0.00"


def test_each_label_sits_along_its_own_component() -> None:
    x_label, y_label, z_label = label_positions((4.0, 6.0, 8.0), magnitude=10.0)
    assert x_label[0] == pytest.approx(4.0 * ALONG_ARROW)
    assert y_label[1] == pytest.approx(6.0 * ALONG_ARROW)
    assert z_label[2] == pytest.approx(8.0 * ALONG_ARROW)


def test_a_label_sits_well_away_from_the_tail() -> None:
    # Near the tail all three arrows and the vector itself converge, and a
    # label placed there ends up behind one of them from some angle.
    x_label, _, _ = label_positions((4.0, 6.0, 8.0), magnitude=10.0)
    assert x_label[0] > 4.0 / 2.0


def test_the_flat_axis_labels_are_lifted_clear_of_the_tick_numbers() -> None:
    # The axis numbers hang below their axis line, so the x and y values go
    # above theirs.
    x_label, y_label, _ = label_positions((4.0, 6.0, 8.0), magnitude=10.0)
    assert x_label[2] > 0.0
    assert y_label[2] > 0.0


def test_the_z_label_is_pushed_out_sideways_instead() -> None:
    # Lifting it in z would only move it along its own arrow.
    _, _, z_label = label_positions((4.0, 6.0, 8.0), magnitude=10.0)
    assert (z_label[0], z_label[1]) != (0.0, 0.0)


def test_the_z_label_leans_away_from_the_vector() -> None:
    # Out of the quadrant the vector occupies, rather than across it.
    _, _, positive = label_positions((4.0, 6.0, 8.0), magnitude=10.0)
    assert positive[0] < 0.0 and positive[1] < 0.0

    _, _, negative = label_positions((-4.0, -6.0, 8.0), magnitude=10.0)
    assert negative[0] > 0.0 and negative[1] > 0.0


def test_labels_do_not_sit_on_their_own_axis_line() -> None:
    for label in label_positions((4.0, 6.0, 8.0), magnitude=10.0):
        assert any(value != 0.0 for value in label)


def test_the_label_offset_scales_with_the_vector() -> None:
    near = label_positions((1.0, 1.0, 1.0), magnitude=1.0)[0][1]
    far = label_positions((10.0, 10.0, 10.0), magnitude=10.0)[0][1]
    assert far == pytest.approx(near * 10.0)


# --- Shadows on the three planes (F-14) ---


def test_each_shadow_drops_the_perpendicular_component() -> None:
    xy, yz, xz = projection_offsets((3.0, 4.0, 5.0))
    assert xy == (3.0, 4.0, 0.0)  # flat on the floor: no height
    assert yz == (0.0, 4.0, 5.0)  # against the far wall: no depth
    assert xz == (3.0, 0.0, 5.0)  # against the side wall


def test_every_shadow_keeps_exactly_two_components() -> None:
    for shadow in projection_offsets((3.0, 4.0, 5.0)):
        assert sum(1 for value in shadow if value == 0.0) == 1


def test_negative_components_survive_into_the_shadow() -> None:
    xy, yz, xz = projection_offsets((-2.0, 3.0, -4.0))
    assert xy == (-2.0, 3.0, 0.0)
    assert yz == (0.0, 3.0, -4.0)
    assert xz == (-2.0, 0.0, -4.0)


def test_a_vector_in_a_plane_is_its_own_shadow_there() -> None:
    # Nothing to project: it is already flat on the floor.
    components = (3.0, 4.0, 0.0)
    assert projection_offsets(components)[0] == components


def test_a_vector_on_an_axis_casts_nothing_on_the_opposite_plane() -> None:
    # Straight up the z axis: no shadow on the floor at all, and the same
    # shadow on each of the two walls that contain the axis.
    xy, yz, xz = projection_offsets((0.0, 0.0, 5.0))
    assert xy == (0.0, 0.0, 0.0)
    assert yz == (0.0, 0.0, 5.0)
    assert xz == (0.0, 0.0, 5.0)


def test_the_zero_vector_casts_no_shadows() -> None:
    assert projection_offsets((0.0, 0.0, 0.0)) == (
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0),
    )


def test_the_three_shadows_sum_to_twice_the_vector() -> None:
    # Each component appears in exactly two of the three shadows, which is
    # another way of saying each is dropped exactly once.
    components = (3.0, 4.0, 5.0)
    total = tuple(
        sum(shadow[i] for shadow in projection_offsets(components)) for i in range(3)
    )
    assert total == tuple(2 * value for value in components)


def test_a_shadow_is_never_longer_than_the_vector() -> None:
    import math

    components = (3.0, 4.0, 5.0)
    length = math.hypot(*components)
    for shadow in projection_offsets(components):
        assert math.hypot(*shadow) <= length


def test_shadows_are_not_the_component_arrows() -> None:
    # A shadow keeps two components; a component arrow keeps one. Easy to
    # conflate, and they are drawn by different overlays.
    components = (3.0, 4.0, 5.0)
    assert set(projection_offsets(components)) & set(component_offsets(components)) == set()
