"""tryon - offline garment projection onto webcam/video, zero dependencies.

Color-region tracking: the user clicks their shirt once; the tracker
follows that color region and the client draws the garment onto it.
The Python tracker here is the reference implementation (unittest'd on
synthetic frames); www/js/tracker.js mirrors it for realtime use —
pixels never leave the browser.
"""

__version__ = "0.1.0"

from .tracker import track  # noqa: F401
