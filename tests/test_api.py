"""API edges on a loopback server: garments, track, static, validation."""

import json
import os
import socket
import sys
import threading
import time
import unittest
import urllib.request
import urllib.error
from http.server import HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tryon.server import Handler

s = socket.socket(); s.bind(("127.0.0.1", 0)); PORT = s.getsockname()[1]; s.close()
BASE = "http://127.0.0.1:%d" % PORT


def get(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=10) as r:
            return r.status, r.headers.get("Content-Type"), r.read()
    except urllib.error.HTTPError as e:
        b = e.read(); e.close()
        return e.code, None, b


def post(path, obj, raw=None):
    body = raw if raw is not None else json.dumps(obj).encode()
    req = urllib.request.Request(BASE + path, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        b = e.read(); e.close()
        return e.code, json.loads(b) if b else {}


def blob_frame(w=40, h=30):
    """Target-colored rectangle in the middle on a dark background."""
    px = []
    for y in range(h):
        for x in range(w):
            if 10 <= x < 30 and 8 <= y < 22:
                px += [200, 60, 60]
            else:
                px += [20, 20, 30]
    return px


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", PORT), Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_garments_listed(self):
        code, _, body = get("/api/garments")
        self.assertEqual(code, 200)
        data = json.loads(body)
        ids = [g["id"] for g in data["garments"]]
        self.assertEqual(ids, ["garment_checks", "garment_collar",
                               "garment_real_beige_midi_dress",
                               "garment_real_black_shirtdress",
                               "garment_real_brown_shirtdress",
                               "garment_real_layered_tee",
                               "garment_real_navy_pattern_shirt",
                               "garment_real_puffer_jacket",
                               "garment_stripes"])

    def test_track_endpoint(self):
        code, data = post("/api/track", {"w": 40, "h": 30, "target": [200, 60, 60],
                                         "tol": 0.08, "pixels": blob_frame()})
        self.assertEqual(code, 200)
        q = data["quad"]
        self.assertIsNotNone(q)
        self.assertLess(abs(q["cx"] - 19.5), 1.5)
        self.assertLess(abs(q["cy"] - 14.5), 1.5)

    def test_track_deterministic_over_http(self):
        payload = {"w": 40, "h": 30, "target": [200, 60, 60],
                   "tol": 0.08, "pixels": blob_frame()}
        self.assertEqual(post("/api/track", payload), post("/api/track", payload))

    def test_validation_rejects(self):
        good = {"w": 40, "h": 30, "target": [200, 60, 60], "tol": 0.08,
                "pixels": blob_frame()}
        def broken(**kw):
            d = dict(good); d.update(kw); return d
        self.assertEqual(post("/api/track", broken(pixels=[1, 2, 3]))[0], 400)
        self.assertEqual(post("/api/track", broken(tol=2.0))[0], 400)
        self.assertEqual(post("/api/track", broken(target=[300, 0, 0]))[0], 400)
        self.assertEqual(post("/api/track", broken(w=10000, h=10000))[0], 400)
        self.assertEqual(post("/api/track", None, raw=b"not json")[0], 400)
        self.assertEqual(get("/api/nope")[0], 404)

    def test_static_samples_served(self):
        code, ctype, body = get("/samples/model.png")
        self.assertEqual(code, 200)
        self.assertEqual(ctype, "image/png")
        self.assertTrue(body.startswith(b"\x89PNG"))
        code, _, _ = get("/samples/model.webm")
        self.assertEqual(code, 200)
        code, ctype, body = get("/samples/real/model_real.png")
        self.assertEqual(code, 200)
        code, _, _ = get("/samples/real/model_real.webm")
        self.assertEqual(code, 200)
        # studio models (green screen) + occasion backgrounds
        for name in ("gs_slim.jpg", "gs_avg.jpg", "gs_plus.jpg",
                     "bg_studio.jpg", "bg_park.jpg", "bg_beach.jpg",
                     "bg_cafe.jpg", "bg_street.jpg"):
            code, _, body = get("/samples/real/" + name)
            self.assertEqual(code, 200, name)
            self.assertTrue(body[:3] == b"\xff\xd8\xff", name)  # JPEG magic
        for name in ("gs_slim.webm", "gs_avg.webm", "gs_plus.webm"):
            code, _, _ = get("/samples/real/" + name)
            self.assertEqual(code, 200, name)
        # real-room footage (non-green-screen)
        code, _, body = get("/samples/real/room.jpg")
        self.assertEqual(code, 200)
        self.assertTrue(body[:3] == b"\xff\xd8\xff")
        code, _, _ = get("/samples/real/room.webm")
        self.assertEqual(code, 200)

    def test_traversal_blocked(self):
        self.assertEqual(get("/../tryon/server.py")[0], 404)
        self.assertEqual(get("/samples/../../tryon/tracker.py")[0], 404)


if __name__ == "__main__":
    unittest.main()
