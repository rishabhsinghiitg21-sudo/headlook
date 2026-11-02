"""FlightGear output backend — drive the cockpit view directly.

Instead of faking a mouse, we connect to FlightGear's built-in telnet
property server and set the view offset properties. This gives an absolute,
1:1 head->view mapping with FG's own smoothing (the "goal-" properties).

Launch FlightGear with the property server enabled, e.g.:
    fgfs --telnet=5401 ...
or, in the FlightGear.app launcher, add `--telnet=5401` to the additional
settings / command-line options box.

Protocol: line-based. `set <prop> <value>\\r\\n` assigns; no reply needed.
See https://wiki.flightgear.org/Telnet_usage
"""
import socket

HEADING_PROP = "/sim/current-view/goal-heading-offset-deg"
PITCH_PROP = "/sim/current-view/goal-pitch-offset-deg"


class FGFSView:
    def __init__(self, host="127.0.0.1", port=5401, timeout=3.0):
        self.host = host
        self.port = port
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.sock.settimeout(timeout)
        # switch the telnet server to non-prompt 'data' mode so it doesn't
        # echo prompts back at us between commands
        self._send("data")

    def _send(self, line):
        self.sock.sendall((line + "\r\n").encode("ascii"))

    def set_view(self, heading_deg, pitch_deg):
        """Set the absolute view offset (degrees from straight-ahead)."""
        self._send(f"set {HEADING_PROP} {heading_deg:.2f}")
        self._send(f"set {PITCH_PROP} {pitch_deg:.2f}")

    def recenter_view(self):
        self.set_view(0.0, 0.0)

    def close(self):
        try:
            self.recenter_view()
            self._send("quit")
        except OSError:
            pass
        try:
            self.sock.close()
        except OSError:
            pass


def try_connect(host="127.0.0.1", port=5401, timeout=3.0):
    """Return an FGFSView or None with a helpful message if FG isn't reachable."""
    try:
        return FGFSView(host, port, timeout)
    except (ConnectionRefusedError, OSError) as e:
        print(f"Could not reach FlightGear property server at {host}:{port} ({e}).")
        print("Launch FlightGear with  --telnet=5401  and try again.")
        return None
