"""Art of Rally head-tracker.

Webcam -> MediaPipe head pose -> UDP packet (opentrack-compatible: 6 little-endian
doubles  x,y,z,yaw,pitch,roll) sent to the BepInEx camera plugin on localhost.

Also shows a CLICK-THROUGH, ALWAYS-ON-TOP webcam+face-mesh overlay pinned to the
bottom-right of the screen, so it floats over the game without stealing any mouse
or keyboard input (ignoresMouseEvents + joins all spaces / over full screen).

Run (from the repo root):  .venv/bin/python -m headlook.ratrack
"""
import signal
import socket
import struct
import subprocess
import sys

import cv2
import objc
from AppKit import (
    NSApplication, NSApplicationActivationPolicyAccessory, NSColor, NSImage,
    NSImageScaleAxesIndependently, NSImageView, NSObject, NSScreen,
    NSScreenSaverWindowLevel, NSTimer, NSWindow,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowCollectionBehaviorStationary,
)
from Foundation import NSData, NSMakeRect

from .config import Config
from .tracker import HeadTracker

UDP_HOST, UDP_PORT = "127.0.0.1", 4242
GAME_PROC = "Contents/MacOS/art of rally"   # tracker auto-quits when this game process ends
OVERLAY_W, OVERLAY_H = 300, 225
MARGIN = 24
STYLE_BORDERLESS = 0
BACKING_BUFFERED = 2
FONT = cv2.FONT_HERSHEY_SIMPLEX


class Driver(NSObject):
    """Capture loop (driven by an NSTimer on the main run loop) + overlay updater."""

    def initWithView_(self, image_view):
        self = objc.super(Driver, self).init()
        if self is None:
            return None
        cfg = Config()
        self.view = image_view
        self.cap = cv2.VideoCapture(cfg.camera_index)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        if not self.cap.isOpened():
            self.cap.release()
            sys.exit(f"[ratrack] could not open the webcam (index {cfg.camera_index}).\n"
                     "  Allow Camera for your terminal in System Settings > Privacy & Security > Camera,\n"
                     "  fully quit and reopen the terminal, then run again.")
        self.tracker = HeadTracker(cfg.model_path)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.ts = 0
        self.n = 0
        self.missed = 0
        self.seen_game = False
        return self

    def _game_alive(self):
        return subprocess.run(["pgrep", "-f", GAME_PROC],
                              capture_output=True).returncode == 0

    def _shutdown(self, why="game closed"):
        print(f"[ratrack] {why} -> stopping camera + tracker", flush=True)
        try: self.cap.release()        # turns the camera light OFF
        except Exception: pass
        try: self.tracker.close()
        except Exception: pass
        NSApplication.sharedApplication().terminate_(None)

    def tick_(self, _timer):
        # auto-stop ~1-2s after the game exits, so the camera only runs in-game
        self.n += 1
        if self.n % 30 == 0:
            if self._game_alive():
                self.missed = 0
                self.seen_game = True
            else:
                self.missed += 1
            # Once the game has been seen, quit ~2 s after it exits. Before that,
            # give it up to a minute to start (it can take a while to launch).
            if self.missed >= (2 if self.seen_game else 60):
                self._shutdown()
                return

        ok, frame = self.cap.read()
        if not ok:
            return
        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.ts += 33
        pose = self.tracker.process(rgb, self.ts)   # (pitch, yaw, roll) or None

        if pose is not None:
            pitch, yaw, roll = pose
            pkt = struct.pack("<6d", 0.0, 0.0, 0.0, yaw, pitch, roll)
            try:
                self.sock.sendto(pkt, (UDP_HOST, UDP_PORT))
            except OSError:
                pass

        lm = getattr(self.tracker, "landmarks", None)
        h, w = frame.shape[:2]
        if lm:
            for x, y in lm:
                cv2.circle(frame, (int(x * w), int(y * h)), 1, (80, 255, 140), -1)
        cv2.putText(frame, "TRACKING" if lm else "NO FACE", (8, h - 10), FONT, 0.55,
                    (80, 255, 140) if lm else (90, 90, 240), 2, cv2.LINE_AA)
        if pose is not None:
            cv2.putText(frame, f"yaw {pose[1]:+5.1f}  pitch {pose[0]:+5.1f}", (8, 22),
                        FONT, 0.5, (0, 255, 255), 1, cv2.LINE_AA)

        small = cv2.resize(frame, (OVERLAY_W, OVERLAY_H))
        okk, buf = cv2.imencode(".png", small)
        if okk:
            data = NSData.dataWithBytes_length_(buf.tobytes(), int(buf.size))
            img = NSImage.alloc().initWithData_(data)
            if img is not None:
                self.view.setImage_(img)


def main():
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)  # no dock icon / no focus steal

    scr = NSScreen.mainScreen().frame()
    rect = NSMakeRect(scr.size.width - OVERLAY_W - MARGIN, MARGIN, OVERLAY_W, OVERLAY_H)

    win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
        rect, STYLE_BORDERLESS, BACKING_BUFFERED, False)
    win.setOpaque_(False)
    win.setBackgroundColor_(NSColor.clearColor())
    win.setLevel_(NSScreenSaverWindowLevel)        # float above the game
    win.setIgnoresMouseEvents_(True)               # click-through (no input interference)
    win.setCollectionBehavior_(
        NSWindowCollectionBehaviorCanJoinAllSpaces
        | NSWindowCollectionBehaviorFullScreenAuxiliary
        | NSWindowCollectionBehaviorStationary)
    win.setHasShadow_(True)

    view = NSImageView.alloc().initWithFrame_(NSMakeRect(0, 0, OVERLAY_W, OVERLAY_H))
    view.setImageScaling_(NSImageScaleAxesIndependently)
    win.setContentView_(view)
    win.orderFrontRegardless()

    driver = Driver.alloc().initWithView_(view)
    print(f"[ratrack] head pose -> udp {UDP_HOST}:{UDP_PORT}; click-through overlay bottom-right.", flush=True)
    # Ctrl-C / kill: the Cocoa run loop swallows the default KeyboardInterrupt, so handle
    # the signal explicitly. It runs between timer ticks, and releases the camera cleanly.
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: driver._shutdown("interrupted"))
    NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        1.0 / 30.0, driver, "tick:", None, True)
    app.run()


if __name__ == "__main__":
    main()
