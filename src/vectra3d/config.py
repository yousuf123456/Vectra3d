"""Every tunable value in Vectra3D.

These are the starting values from `interaction-spec.md` section 9, plus the
default user settings from section 8. They are collected here so that tuning
the app never means hunting for numbers buried in the code.

Rules for changing anything in this file (`interaction-spec.md` section 9):
- Change a value only after testing with real hands, never to make a test pass.
- Record every change in `context/progress-tracker.md` with the reason.

Units are written exactly as the spec states them, with no conversion, so this
file can be compared against section 9 line by line. `hs` is a hand-scale unit:
the distance from the wrist to the base of the middle finger, which keeps
measurements the same whether the hand is near the camera or far from it.
"""

from __future__ import annotations

# --- Pinch detection (spec section 4.2) ---
# A pinch starts below the first distance and ends above the second. The gap
# between them stops the pinch flickering on and off when a hand is held still.
PINCH_START_HS: float = 0.25  # hand-scale units
PINCH_END_HS: float = 0.35  # hand-scale units

# --- Losing a hand (spec section 4.4) ---
# A tracked hand missing for longer than this ends the gesture as a normal
# release, not a cancel.
HAND_LOST_TIMEOUT_S: float = 0.3  # seconds

# --- Gesture state machine (spec section 5) ---
# A second pinch within this window makes it a two-hand gesture.
TWO_HAND_PINCH_WINDOW_S: float = 0.3  # seconds

# --- Creating a vector (spec section 6.2) ---
# Pinch points closer than this count as "hands together", which starts
# creating rather than resizing.
HANDS_TOGETHER_HS: float = 1.0  # hand-scale units
# The hand travel that equals one full magnitude sensitivity step.
FULL_STRETCH_HS: float = 8.0  # hand-scale units
# Vectors shorter than this are not created, and resizing never goes below it.
MIN_MAGNITUDE: float = 0.1  # scene units
# If both hands moved within this margin of each other, neither is clearly
# leading, so the head goes to the hand on the right of the screen.
EQUAL_MOVEMENT_MARGIN: float = 0.10  # fraction (10%)

# --- Steering (spec section 6.4) ---
# Hand movement inside the dead zone does not rotate the vector, so a small
# shake while holding a pinch leaves the vector where it is.
STEER_DEAD_ZONE_HS: float = 0.3  # hand-scale units
STEER_MAX_SPEED_DEG_PER_S: float = 90.0  # degrees per second
# Deflection at which the maximum rotation speed is reached.
STEER_MAX_SPEED_HS: float = 1.5  # hand-scale units

# --- Snapping (spec section 6.5) ---
# The vector snaps onto an axis or plane within the first angle, and only
# breaks free past the second, so it does not flicker at the boundary.
SNAP_IN_DEG: float = 5.0  # degrees
SNAP_RELEASE_DEG: float = 8.0  # degrees

# --- Hold gestures (spec section 7) ---
# A hold gesture must be recognized continuously for this long, at this
# confidence, before it triggers once.
HOLD_DURATION_S: float = 0.5  # seconds
HOLD_CONFIDENCE: float = 0.6  # 0.0 to 1.0

# --- Animation and transitions (spec sections 3 and 10) ---
# A result moves to its new value over this time instead of jumping.
RESULT_TRANSITION_MS: int = 150  # milliseconds
# The grid and camera grow or shrink to a new scene extent over this time.
SCENE_RESCALE_MS: int = 300  # milliseconds
# The four phases of the head-to-tail animation (spec section 10).
HEAD_TO_TAIL_SLIDE_S: float = 1.0  # seconds
HEAD_TO_TAIL_DRAW_S: float = 0.5  # seconds
HEAD_TO_TAIL_PAUSE_S: float = 0.7  # seconds
HEAD_TO_TAIL_RETURN_S: float = 0.5  # seconds

# --- Default user settings (spec section 8) ---
# These are only the starting values. Once the app is running, the live values
# belong to the settings in `state/`, which the student changes from the
# action panel.
SNAPPING_DEFAULT: bool = True
# How many units of magnitude one full hand stretch produces.
MAGNITUDE_SENSITIVITY_DEFAULT: int = 25  # scene units per full stretch
MAGNITUDE_SENSITIVITY_MIN: int = 5
MAGNITUDE_SENSITIVITY_MAX: int = 50
MAGNITUDE_SENSITIVITY_STEP: int = 5
