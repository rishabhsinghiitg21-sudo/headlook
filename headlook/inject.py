"""Synthetic mouse movement on macOS via Quartz CGEvent.

We post mouse-moved events with BOTH an absolute target position and the
delta fields set. Games that read relative motion (most FPS/sim free-look)
pick up the deltas; we also nudge the real cursor so it doesn't pile into a
screen edge in windowed mode.

Requires: System Settings -> Privacy & Security -> Accessibility, and the
app running this (Terminal / iTerm / your IDE) must be allowed.
"""
import Quartz
from ApplicationServices import AXIsProcessTrusted


def _cursor_pos():
    e = Quartz.CGEventCreate(None)
    return Quartz.CGEventGetLocation(e)


def move_relative(dx, dy):
    """Move the look by (dx, dy) mouse pixels. Posts a synthetic event."""
    if dx == 0 and dy == 0:
        return
    pos = _cursor_pos()
    target = Quartz.CGPointMake(pos.x + dx, pos.y + dy)
    ev = Quartz.CGEventCreateMouseEvent(
        None, Quartz.kCGEventMouseMoved, target, Quartz.kCGMouseButtonLeft
    )
    Quartz.CGEventSetIntegerValueField(ev, Quartz.kCGMouseEventDeltaX, int(round(dx)))
    Quartz.CGEventSetIntegerValueField(ev, Quartz.kCGMouseEventDeltaY, int(round(dy)))
    Quartz.CGEventPost(Quartz.kCGHIDEventTap, ev)


def accessibility_trusted():
    """True if this process is allowed to post input events."""
    try:
        return bool(AXIsProcessTrusted())
    except Exception:
        return None  # symbol not available; let the actual post fail loudly
