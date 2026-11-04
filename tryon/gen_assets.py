"""Procedural sample assets: garment PNGs with alpha, a synthetic model
photo, and frames for the sample video (assembled by dev-time ffmpeg).

Everything is a pure function of its arguments: same inputs -> same
bytes. PNGs are written with raw zlib+struct (no imaging library).
Run as a script to regenerate www/samples/.
"""

import os
import struct
import zlib


# ---------- raw PNG writer ----------

def write_png(path, w, h, rgba):
    """rgba: flat list, 4 bytes/px, row-major."""
    raw = b"".join(b"\x00" + bytes(rgba[y * 4 * w:(y + 1) * 4 * w]) for y in range(h))

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(png)
    return png


# ---------- garments (RGBA, transparent background) ----------

def garment(variant, w=240, h=280):
    px = [0] * (4 * w * h)

    def put(x, y, r, g, b, a=255):
        if 0 <= x < w and 0 <= y < h:
            i = 4 * (y * w + x)
            px[i], px[i + 1], px[i + 2], px[i + 3] = r, g, b, a

    base = {"stripes": (200, 60, 60), "collar": (60, 90, 190),
            "checks": (70, 160, 90)}[variant]

    # torso: tapered rounded slab; sleeves: two angled blocks
    for y in range(50, h - 20):
        t = (y - 50) / (h - 70)
        half = 62 - 12 * t
        for x in range(w // 2 - int(half), w // 2 + int(half)):
            r, g, b = base
            if variant == "stripes" and (y % 28) < 14:
                r, g, b = 240, 240, 240
            if variant == "checks" and ((x // 20) + (y // 20)) % 2:
                r, g, b = 30, 90, 55
            put(x, y, r, g, b)
    # sleeves
    for y in range(55, 150):
        for x in range(24, 70):
            if (x - 24) + (y - 55) < 105:
                put(x, y, *base)
        for x in range(w - 70, w - 24):
            if (w - 24 - x) + (y - 55) < 105:
                put(x, y, *base)
    # collar / neck notch
    if variant == "collar":
        for y in range(50, 84):
            for x in range(w // 2 - 26, w // 2 + 26):
                if abs(x - w // 2) + (y - 50) > 30:
                    put(x, y, 235, 240, 248)
    else:
        for y in range(50, 74):
            for x in range(w // 2 - 22, w // 2 + 22):
                put(x, y, 0, 0, 0, 0)
    return px, w, h


# ---------- synthetic person frame (RGB flat list) ----------

SKIN = (226, 188, 158)
HAIR = (60, 44, 34)
PANTS = (52, 56, 74)


def person_frame(w, h, sway, shirt=(200, 60, 60), t=0.0):
    px = [0] * (3 * w * h)

    def put(x, y, c):
        if 0 <= x < w and 0 <= y < h:
            i = 3 * (y * w + x)
            px[i], px[i + 1], px[i + 2] = c

    cx = w // 2 + int(sway)
    for y in range(h):
        for x in range(w):
            g = 150 + (y * 40) // h          # soft studio gradient
            n = (x * 7 + y * 13 + ((x * y) % 5)) % 7   # deterministic grain
            put(x, y, (g + n, g + 6 + n, g + 18 + n))
    head_cy = int(h * 0.22)
    # hair + head
    for yy in range(head_cy - 34, head_cy + 30):
        for xx in range(cx - 30, cx + 30):
            d2 = (xx - cx) ** 2 + ((yy - head_cy) * 1.15) ** 2
            if d2 <= 30 * 30:
                put(xx, yy, HAIR if yy < head_cy - 12 else SKIN)
    # torso (shirt) 120 wide, 150 tall
    ty0, ty1 = head_cy + 26, head_cy + 176
    for yy in range(ty0, ty1):
        half = 60 - (yy - ty0) // 12
        for xx in range(cx - half, cx + half):
            put(xx, yy, shirt)
    # arms (slight swing)
    for yy in range(ty0 + 4, ty0 + 78):
        off = int(6 * ((yy - ty0) / 74.0 - 0.5))
        for xx in range(cx - half - 22 + off, cx - half + off):
            put(xx, yy, shirt if yy < ty0 + 26 else SKIN)
        for xx in range(cx + half + off, cx + half + 22 + off):
            put(xx, yy, shirt if yy < ty0 + 26 else SKIN)
    # legs
    ly0 = ty1 - 2
    for yy in range(ly0, min(ly0 + 130, h)):
        for xx in range(cx - 42, cx + 42):
            if abs(xx - cx) > 6:
                put(xx, yy, PANTS)
    return px


def main():
    import math
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    samples = os.path.join(root, "www", "samples")
    for variant in ("stripes", "collar", "checks"):
        px, w, h = garment(variant)
        write_png(os.path.join(samples, "garment_%s.png" % variant), w, h, px)
    model = person_frame(480, 360, 0)
    write_png(os.path.join(samples, "model.png"), 480, 360,
              rgb_to_rgba(model, 480, 360))
    # frames for the sample video (assemble with ffmpeg, see README)
    frames_dir = os.path.join(root, "tests", "frames")
    for i in range(90):
        px = person_frame(480, 360, 12.0 * math.sin(i / 6.0))
        write_png(os.path.join(frames_dir, "f_%03d.png" % i), 480, 360,
                  rgb_to_rgba(px, 480, 360))
    print("samples:", samples, " frames:", frames_dir)


def rgb_to_rgba(rgb, w, h):
    out = [0] * (4 * w * h)
    j = 0
    for i in range(3 * w * h):
        out[j] = rgb[i]
        if i % 3 == 2:
            out[j + 1] = 255
            j += 2
        else:
            j += 1
    return out


if __name__ == "__main__":
    main()
