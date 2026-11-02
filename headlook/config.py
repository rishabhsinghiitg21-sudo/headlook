"""Tunable parameters for headlook.

Everything you'll want to tweak lives here. Angles are in degrees,
speeds are in mouse-pixels per frame.
"""
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Config:
    # --- camera ---
    camera_index: int = 0          # which webcam (0 = default/built-in)
    frame_width: int = 640         # capture resolution (smaller = faster)
    frame_height: int = 480
    mirror: bool = True            # mirror preview so it feels like a mirror

    # --- mapping: head angle -> look velocity ---
    # Below `deadzone` degrees from neutral, nothing happens (kills drift).
    # At `span` degrees from neutral, you get full `max_speed`.
    yaw_deadzone: float = 4.0      # left/right
    pitch_deadzone: float = 4.0    # up/down
    yaw_span: float = 22.0         # head turn that = full-speed pan
    pitch_span: float = 18.0
    max_speed_x: float = 28.0      # max horizontal mouse px/frame
    max_speed_y: float = 18.0      # max vertical mouse px/frame
    response_gamma: float = 2.0    # >1 = gentle near center, punchy at edges

    invert_x: bool = False         # flip if you look right and view goes left
    invert_y: bool = True          # most mouse-look: head up -> view up

    # --- absolute mapping (FlightGear / position-mode backends) ---
    # view_offset_degrees = (head_angle - deadzone) * gain, clamped to max.
    # gain > 1 lets a small head turn cover a big view sweep.
    view_gain_x: float = 4.5       # head yaw -> view heading offset
    view_gain_y: float = 3.0       # head pitch -> view pitch offset
    view_max_x: float = 120.0      # clamp heading offset (deg); 120 = glance back
    view_max_y: float = 70.0       # clamp pitch offset (deg)

    # --- FlightGear telnet property server ---
    fg_host: str = "127.0.0.1"
    fg_port: int = 5401

    # --- smoothing ---
    smoothing: float = 0.35        # EMA factor 0..1 (higher = smoother/laggier)

    # --- hotkeys (pynput key names; F-keys are 'f8' etc.) ---
    key_toggle: str = "f8"         # enable/disable look
    key_recenter: str = "f9"       # set current head pose as neutral
    key_quit: str = "f10"          # quit the app
    hold_to_look: bool = False     # if True, look only while toggle key held

    # --- model ---
    # downloaded by setup.sh; resolved from the repo root, so any working dir works
    model_path: str = str(REPO_ROOT / "models" / "face_landmarker.task")

    start_enabled: bool = False    # whether look is active on launch
