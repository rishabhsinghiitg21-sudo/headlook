"""headlook — webcam head-tracking free-look for macOS games.

Modes:
  test-mouse  No camera. Wiggles the cursor to verify Accessibility +
              that your GAME reacts to synthetic mouse-look. Run this FIRST.
  preview     Camera + tracking overlay, NO injection. Check tracking quality
              and tune deadzone/span. Press the recenter key to set neutral.
  run         Full pipeline: head -> mouse-look injected into the focused app.

Hotkeys (global, default): F8 toggle look, F9 recenter, F10 quit.
(Reading global keys needs Input Monitoring permission for your terminal.)
"""
import argparse
import sys
import time

import cv2
import numpy as np
from pynput import keyboard

from .config import Config
from .mapping import Mapper
from . import inject
from . import fgfs


class Hotkeys:
    """Global key listener for toggle / recenter / quit."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.enabled = cfg.start_enabled
        self.recenter_requested = False
        self.quit = False
        self._held = False
        self._listener = keyboard.Listener(
            on_press=self._on_press, on_release=self._on_release
        )
        self._listener.start()

    def _name(self, key):
        if isinstance(key, keyboard.Key):
            return key.name
        if isinstance(key, keyboard.KeyCode) and key.char:
            return key.char.lower()
        return None

    def _on_press(self, key):
        n = self._name(key)
        if n == self.cfg.key_toggle:
            if self.cfg.hold_to_look:
                self._held = True
            else:
                self.enabled = not self.enabled
                print(f"[look {'ON' if self.enabled else 'OFF'}]")
        elif n == self.cfg.key_recenter:
            self.recenter_requested = True
        elif n == self.cfg.key_quit:
            self.quit = True

    def _on_release(self, key):
        if self.cfg.hold_to_look and self._name(key) == self.cfg.key_toggle:
            self._held = False

    @property
    def looking(self):
        return self._held if self.cfg.hold_to_look else self.enabled


def _open_camera(cfg):
    cap = cv2.VideoCapture(cfg.camera_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.frame_width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.frame_height)
    if not cap.isOpened():
        return None
    return cap


def _camera_help(cfg):
    print("\n  !! Could not open the webcam (index "
          f"{cfg.camera_index}).\n"
          "     Grant Camera permission to your terminal app:\n"
          "       System Settings > Privacy & Security > Camera > enable it,\n"
          "     then fully quit and reopen the terminal and run again.\n"
          "     If you have multiple cameras, try  --camera 1\n")


# --------------------------------------------------------------------------- #
# modes
# --------------------------------------------------------------------------- #
def mode_test_mouse(cfg):
    trusted = inject.accessibility_trusted()
    print(f"Accessibility trusted: {trusted}")
    if trusted is False:
        print("-> Not trusted. Add your terminal under System Settings > "
              "Privacy & Security > Accessibility, then re-run.")
    print("Focus your GAME now. Moving the look in a small circle for 6s...")
    print("If the in-game camera pans, synthetic mouse-look WORKS. (Ctrl-C to stop.)")
    t0 = time.time()
    try:
        while time.time() - t0 < 6.0:
            ang = (time.time() - t0) * 4.0
            inject.move_relative(8 * np.cos(ang), 6 * np.sin(ang))
            time.sleep(1 / 60)
    except KeyboardInterrupt:
        print("Stopped.")
        return
    print("Done.")


def _draw_overlay(frame, pitch, yaw, vx, vy, looking, cfg):
    h, w = frame.shape[:2]
    cv2.putText(frame, f"yaw {yaw:+6.1f}  pitch {pitch:+6.1f}",
                (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    cv2.putText(frame, f"vel  x {vx:+5.1f}  y {vy:+5.1f}",
                (10, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    state = "LOOK ON" if looking else "look off"
    color = (0, 200, 0) if looking else (120, 120, 120)
    cv2.putText(frame, state, (10, h - 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    # velocity vector from center
    cx, cy = w // 2, h // 2
    cv2.circle(frame, (cx, cy), 4, (255, 255, 255), -1)
    cv2.arrowedLine(frame, (cx, cy), (int(cx + vx * 4), int(cy + vy * 4)),
                    (0, 255, 255), 2, tipLength=0.3)


def _run_loop(cfg, output, show_window):
    """output: None (preview), 'mouse', or 'fgfs'."""
    from .tracker import HeadTracker  # lazy: avoids loading model in test-mouse
    tracker = HeadTracker(cfg.model_path)
    mapper = Mapper(cfg)
    keys = Hotkeys(cfg)

    view = None
    if output == "fgfs":
        view = fgfs.try_connect(cfg.fg_host, cfg.fg_port)
        if view is None:
            tracker.close()
            sys.exit(1)

    cap = _open_camera(cfg)
    if cap is None:
        _camera_help(cfg)
        tracker.close()
        if view is not None:
            view.close()
        sys.exit(1)

    label = {None: "PREVIEW", "mouse": "RUN/mouse", "fgfs": "RUN/FlightGear"}[output]
    print(f"[{label}] running. Quit with Ctrl-C or {cfg.key_quit}.")
    if output is not None:
        print(f"Look {'ON' if cfg.start_enabled else 'OFF'} at start — "
              f"{cfg.key_toggle} engage, {cfg.key_recenter} recenter.")

    primed = False  # auto-set neutral on first good frame
    try:
        while True:
            if keys.quit:
                break
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.01)   # camera hiccup or unplugged: don't spin
                continue
            if cfg.mirror:
                frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pose = tracker.process(rgb, int(time.time() * 1000))

            looking = keys.looking
            do_recenter = keys.recenter_requested
            if do_recenter:
                keys.recenter_requested = False

            ox = oy = 0.0
            pitch = yaw = 0.0
            if pose is not None:
                pitch, yaw, _roll = pose
                if not primed:
                    mapper.recenter(pitch, yaw)
                    primed = True
                if do_recenter:
                    mapper.recenter(pitch, yaw)
                    print("[recentered]")

                if output == "fgfs":
                    if looking:
                        ox, oy = mapper.position(pitch, yaw)
                else:  # mouse / preview
                    ox, oy = mapper.velocity(pitch, yaw)

            if output == "fgfs":
                try:
                    view.set_view(ox, oy)          # off -> (0,0) = forward
                except OSError as e:
                    print(f"Lost the FlightGear connection ({e}). Quitting.")
                    break
            elif output == "mouse" and looking:
                inject.move_relative(ox, oy)

            if show_window:
                _draw_overlay(frame, pitch, yaw, ox, oy, looking, cfg)
                cv2.imshow("headlook", frame)
                if cv2.waitKey(1) & 0xFF == 27:  # Esc in window
                    break
    except KeyboardInterrupt:
        pass
    finally:
        cap.release()
        cv2.destroyAllWindows()
        tracker.close()
        if view is not None:
            view.close()


def main(argv=None):
    p = argparse.ArgumentParser(description="headlook — head-tracking free-look")
    p.add_argument("--mode", choices=["test-mouse", "preview", "run"],
                   default="preview")
    p.add_argument("--output", choices=["mouse", "fgfs"], default="mouse",
                   help="run-mode backend: synthetic mouse, or FlightGear telnet")
    p.add_argument("--camera", type=int, help="camera index override")
    p.add_argument("--hold", action="store_true",
                   help="hold toggle key to look (instead of toggle)")
    p.add_argument("--start-on", action="store_true",
                   help="look active immediately in run mode")
    args = p.parse_args(argv)

    cfg = Config()
    if args.camera is not None:
        cfg.camera_index = args.camera
    if args.hold:
        cfg.hold_to_look = True
    if args.start_on:
        cfg.start_enabled = True

    if args.mode == "test-mouse":
        mode_test_mouse(cfg)
    elif args.mode == "preview":
        _run_loop(cfg, output=None, show_window=True)
    else:
        _run_loop(cfg, output=args.output, show_window=False)


if __name__ == "__main__":
    main()
