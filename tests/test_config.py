"""Guards against typos in the tunable values copied from the spec.

These check that every value from `interaction-spec.md` section 9 exists and is
sane. They deliberately do not assert the exact numbers: the spec allows them to
be re-tuned, and a test that repeats each number would only have to be edited
alongside every legitimate change.
"""

from __future__ import annotations

from vectra3d import config

SECTION_9_VALUES = [
    "PINCH_START_HS",
    "PINCH_END_HS",
    "SMOOTHING_MIN_CUTOFF_HZ",
    "SMOOTHING_DERIVATIVE_CUTOFF_HZ",
    "HAND_LOST_TIMEOUT_S",
    "TWO_HAND_PINCH_WINDOW_S",
    "HANDS_TOGETHER_HS",
    "FULL_STRETCH_HS",
    "MIN_MAGNITUDE",
    "EQUAL_MOVEMENT_MARGIN",
    "STEER_DEAD_ZONE_HS",
    "STEER_MAX_SPEED_DEG_PER_S",
    "STEER_MAX_SPEED_HS",
    "SNAP_IN_DEG",
    "SNAP_RELEASE_DEG",
    "HOLD_DURATION_S",
    "HOLD_CONFIDENCE",
    "RESULT_TRANSITION_MS",
    "SCENE_RESCALE_MS",
    "HEAD_TO_TAIL_SLIDE_S",
    "HEAD_TO_TAIL_DRAW_S",
    "HEAD_TO_TAIL_PAUSE_S",
    "HEAD_TO_TAIL_RETURN_S",
]


def test_every_section_9_value_is_present_and_positive() -> None:
    for name in SECTION_9_VALUES:
        value = getattr(config, name)
        assert value > 0, f"{name} must be positive"


def test_pinch_thresholds_leave_room_for_hysteresis() -> None:
    # A pinch must end at a wider distance than it starts, or it flickers.
    assert config.PINCH_END_HS > config.PINCH_START_HS


def test_smoothing_beta_is_not_negative() -> None:
    # Unlike every other section 9 value, beta may be zero: that is where the
    # filter authors' tuning procedure starts. A negative beta would lower the
    # cutoff as the hand speeds up - the opposite of the filter's purpose.
    assert config.SMOOTHING_BETA >= 0


def test_snap_releases_wider_than_it_engages() -> None:
    assert config.SNAP_RELEASE_DEG > config.SNAP_IN_DEG


def test_magnitude_sensitivity_default_is_within_its_range() -> None:
    assert (
        config.MAGNITUDE_SENSITIVITY_MIN
        <= config.MAGNITUDE_SENSITIVITY_DEFAULT
        <= config.MAGNITUDE_SENSITIVITY_MAX
    )
    span = config.MAGNITUDE_SENSITIVITY_MAX - config.MAGNITUDE_SENSITIVITY_MIN
    assert span % config.MAGNITUDE_SENSITIVITY_STEP == 0
