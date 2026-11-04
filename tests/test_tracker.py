"""Tracker postconditions on synthetic frames from gen_assets."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tryon.tracker import track
from tryon.gen_assets import person_frame

W, H = 320, 240
SHIRT = (200, 60, 60)


def frame(**kw):
    return person_frame(W, H, kw.get("sway", 0), kw.get("shirt", SHIRT))


class TestTracker(unittest.TestCase):
    def test_finds_torso_center(self):
        q = track(frame(), W, H, SHIRT, 0.08)
        self.assertIsNotNone(q)
        self.assertLess(abs(q["cx"] - W / 2), 6)
        # torso occupies y 78..228; centroid pulled up slightly by arms
        self.assertLess(abs(q["cy"] - 150), 14)

    def test_long_axis_is_vertical(self):
        q = track(frame(), W, H, SHIRT, 0.08)
        # torso is taller than wide: the long axis u should be ~vertical
        self.assertGreater(abs(q["u"][1]), 0.97)
        self.assertGreater(q["hw"], q["hh"])
        self.assertGreater(q["hw"], 60)
        self.assertLess(q["hw"], 105)

    def test_follows_sway(self):
        still = track(frame(), W, H, SHIRT, 0.08)
        moved = track(frame(sway=12), W, H, SHIRT, 0.08)
        self.assertGreater(moved["cx"], still["cx"] + 8)

    def test_no_target_returns_none(self):
        f = frame(shirt=(40, 80, 220))                 # blue shirt
        self.assertIsNone(track(f, W, H, SHIRT, 0.02))  # red target

    def test_pure_function_deterministic(self):
        f = frame(sway=5)
        self.assertEqual(track(f, W, H, SHIRT, 0.08), track(f, W, H, SHIRT, 0.08))

    def test_bad_pixels_length_raises(self):
        with self.assertRaises(ValueError):
            track([1, 2, 3], W, H, SHIRT, 0.08)


if __name__ == "__main__":
    unittest.main()
