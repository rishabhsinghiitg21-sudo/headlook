"""Turn a head angle (relative to neutral) into a look velocity.

Velocity mode: how far your head is turned past a deadzone sets how fast the
view pans. Re-center your head -> velocity returns to zero. This behaves like
a self-centering joystick and sidesteps the "mouse is relative" problem.
"""


def _deadzoned(angle, deadzone):
    """Angle with the deadzone removed, staying continuous past the edge."""
    mag = abs(angle)
    if mag <= deadzone:
        return 0.0
    return (mag - deadzone) if angle > 0 else -(mag - deadzone)


def _delta(angle, neutral):
    """Signed angle from neutral in degrees, wrapped to [-180, 180).

    Euler angles jump by 360 at +-180; without this, a pose near that edge
    would flip the view the moment it crossed it.
    """
    return (angle - neutral + 180.0) % 360.0 - 180.0


def _clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def _axis_velocity(angle, deadzone, span, max_speed, gamma):
    mag = abs(angle)
    if mag <= deadzone:
        return 0.0
    # normalize 0..1 across the usable range past the deadzone
    t = (mag - deadzone) / max(span - deadzone, 1e-6)
    t = min(t, 1.0)
    speed = (t ** gamma) * max_speed
    return speed if angle > 0 else -speed


class Mapper:
    def __init__(self, cfg):
        self.cfg = cfg
        self.neutral_yaw = 0.0
        self.neutral_pitch = 0.0
        self._sx = 0.0  # smoothed velocity x
        self._sy = 0.0  # smoothed velocity y

    def recenter(self, pitch, yaw):
        self.neutral_pitch = pitch
        self.neutral_yaw = yaw
        self._sx = self._sy = 0.0

    def velocity(self, pitch, yaw):
        """Return (dx, dy) mouse-pixel velocity for this frame."""
        c = self.cfg
        d_yaw = _delta(yaw, self.neutral_yaw)
        d_pitch = _delta(pitch, self.neutral_pitch)

        vx = _axis_velocity(d_yaw, c.yaw_deadzone, c.yaw_span,
                            c.max_speed_x, c.response_gamma)
        vy = _axis_velocity(d_pitch, c.pitch_deadzone, c.pitch_span,
                            c.max_speed_y, c.response_gamma)
        if c.invert_x:
            vx = -vx
        if c.invert_y:
            vy = -vy

        # exponential moving average to kill webcam jitter
        a = c.smoothing
        self._sx = a * self._sx + (1 - a) * vx
        self._sy = a * self._sy + (1 - a) * vy
        return self._sx, self._sy

    def position(self, pitch, yaw):
        """Absolute view offset (heading, pitch) in degrees, for FlightGear.

        Maps head angle directly to a view angle: 1:1 (scaled) rather than a
        pan speed. Re-center your head -> view returns to straight ahead.
        """
        c = self.cfg
        d_yaw = _deadzoned(_delta(yaw, self.neutral_yaw), c.yaw_deadzone)
        d_pitch = _deadzoned(_delta(pitch, self.neutral_pitch), c.pitch_deadzone)

        hx = _clamp(d_yaw * c.view_gain_x, -c.view_max_x, c.view_max_x)
        hy = _clamp(d_pitch * c.view_gain_y, -c.view_max_y, c.view_max_y)
        if c.invert_x:
            hx = -hx
        if c.invert_y:
            hy = -hy

        a = c.smoothing
        self._sx = a * self._sx + (1 - a) * hx
        self._sy = a * self._sy + (1 - a) * hy
        return self._sx, self._sy
