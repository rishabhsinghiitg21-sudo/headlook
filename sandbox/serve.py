#!/usr/bin/env python3
"""Static server for the headlook sandbox (serves this folder on localhost).

Browsers only allow the webcam on https or on localhost, so open the page via
this server, not by double-clicking the file. Caching is disabled so edits to
sandbox.html always show up on reload.

    python3 sandbox/serve.py            # http://localhost:8000/sandbox.html
    PORT=9000 python3 sandbox/serve.py
"""
import functools
import http.server
import os
import socketserver

DIR = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", "8000"))


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def log_message(self, *args):
        pass


socketserver.ThreadingTCPServer.allow_reuse_address = True
handler = functools.partial(NoCacheHandler, directory=DIR)
try:
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", PORT), handler)
except OSError as e:
    raise SystemExit(f"Could not listen on port {PORT} ({e.strerror}). "
                     f"Something else is using it: try  PORT={PORT + 1} python3 sandbox/serve.py")
with httpd:
    print(f"headlook sandbox: http://localhost:{PORT}/sandbox.html   (Ctrl-C to stop)")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
