"""Static + API server. Loopback-only in tests.

GET  /                -> www/index.html
GET  /api/garments    -> bundled sample garments
POST /api/track       -> run the reference tracker on posted pixels
                          {w, h, target:[r,g,b], tol, pixels:[...]}
Pixels are capped (<= 640x480, body <= 8 MB); everything validated.
"""

import json
import os
import posixpath
from http.server import HTTPServer, BaseHTTPRequestHandler

from . import tracker

WWW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "www")
MAX_PIXELS = 640 * 480
MAX_BODY = 8 * 1024 * 1024


def _bad(h, code, msg):
    body = json.dumps({"error": msg}).encode()
    h.send_response(code)
    h.send_header("Content-Type", "application/json")
    h.send_header("Content-Length", str(len(body)))
    h.end_headers()
    h.wfile.write(body)


def garments():
    d = os.path.join(WWW, "samples")
    out = []
    if os.path.isdir(d):
        for name in sorted(os.listdir(d)):
            if name.startswith("garment_") and name.endswith(".png"):
                out.append({"id": name[:-4], "url": "samples/" + name,
                            "label": name[8:-4].replace("_", " ").title()})
    return out


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj, sort_keys=True).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        from urllib.parse import urlparse
        parsed = urlparse(self.path)
        if parsed.path == "/api/garments":
            return self._json({"garments": garments()})
        path = parsed.path.lstrip("/") or "index.html"
        path = posixpath.normpath(path)
        if path.startswith("..") or path.startswith("/") or "\x00" in path:
            return _bad(self, 404, "not found")
        fpath = os.path.join(WWW, path)
        if not os.path.abspath(fpath).startswith(os.path.abspath(WWW) + os.sep) \
                or not os.path.isfile(fpath):
            return _bad(self, 404, "not found")
        ctype = ("text/html" if fpath.endswith(".html") else
                 "text/css" if fpath.endswith(".css") else
                 "application/javascript" if fpath.endswith(".js") else
                 "image/png" if fpath.endswith(".png") else
                 "video/webm" if fpath.endswith(".webm") else
                 "application/octet-stream")
        with open(fpath, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        from urllib.parse import urlparse
        if urlparse(self.path).path != "/api/track":
            return _bad(self, 404, "not found")
        n = int(self.headers.get("Content-Length") or 0)
        if n <= 0 or n > MAX_BODY:
            return _bad(self, 413 if n > MAX_BODY else 400, "bad body size")
        try:
            req = json.loads(self.rfile.read(n).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return _bad(self, 400, "body must be JSON")
        try:
            w = int(req["w"])
            h = int(req["h"])
            target = [int(c) for c in req["target"]]
            tol = float(req["tol"])
            pixels = [int(v) for v in req["pixels"]]
        except (KeyError, TypeError, ValueError):
            return _bad(self, 400, "missing/malformed fields")
        if not (0 < w <= 640 and 0 < h <= 480):
            return _bad(self, 400, "w,h out of range")
        if w * h > MAX_PIXELS:
            return _bad(self, 400, "frame too large")
        if len(target) != 3 or not all(0 <= c <= 255 for c in target):
            return _bad(self, 400, "target must be [r,g,b] 0..255")
        if not (0.0 <= tol <= 1.0):
            return _bad(self, 400, "tol must be 0..1")
        if len(pixels) != 3 * w * h:
            return _bad(self, 400, "pixels must have length 3*w*h")
        if not all(0 <= v <= 255 for v in pixels[:30] + pixels[-30:]):
            return _bad(self, 400, "pixels must be 0..255")
        try:
            quad = tracker.track(pixels, w, h, target, tol)
        except ValueError as e:
            return _bad(self, 400, str(e))
        return self._json({"quad": quad})


def serve(port=8620):
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    import sys
    serve(int(sys.argv[1]) if len(sys.argv) > 1 else 8620)
