"""Reference color-region tracker. Pure function, deterministic.

Algorithm (mirrored exactly in www/js/tracker.js):
1. mask   : pixel is "shirt" if normalized RGB distance to target <= tol
2. moment : centroid + covariance of masked pixels
3. fit    : eigen-decomposition of covariance -> oriented rectangle
            (unit vectors u, v; half-extents 2*sqrt(lambda))
4. reject : fewer than min_area pixels -> no target

Input pixels: flat RGB list [r,g,b, ...] length 3*w*h, ints 0..255.
"""

import math

_MAX_DIST = math.sqrt(3.0 * 255.0 * 255.0)


def track(pixels, w, h, target, tol, min_frac=0.0005):
    """Return {'cx','cy','u','v','hw','hh','count'} or None."""
    if len(pixels) != 3 * w * h:
        raise ValueError("pixels must have length 3*w*h")
    tr, tg, tb = target
    count = 0
    sx = sy = 0.0
    for y in range(h):
        base = 3 * y * w
        for x in range(w):
            i = base + 3 * x
            d = math.sqrt((pixels[i] - tr) ** 2 + (pixels[i + 1] - tg) ** 2
                          + (pixels[i + 2] - tb) ** 2)
            if d / _MAX_DIST <= tol:
                count += 1
                sx += x
                sy += y
    if count < max(4, int(min_frac * w * h)):
        return None
    cx, cy = sx / count, sy / count
    sxx = sxy = syy = 0.0
    for y in range(h):
        base = 3 * y * w
        for x in range(w):
            i = base + 3 * x
            d = math.sqrt((pixels[i] - tr) ** 2 + (pixels[i + 1] - tg) ** 2
                          + (pixels[i + 2] - tb) ** 2)
            if d / _MAX_DIST <= tol:
                dx, dy = x - cx, y - cy
                sxx += dx * dx
                sxy += dx * dy
                syy += dy * dy
    cxx, cxy, cyy = sxx / count, sxy / count, syy / count
    theta = 0.5 * math.atan2(2.0 * cxy, cxx - cyy)
    # eigenvalues of [[cxx, cxy], [cxy, cyy]]
    mean = (cxx + cyy) / 2.0
    disc = math.sqrt(max(0.0, ((cxx - cyy) / 2.0) ** 2 + cxy * cxy))
    l1, l2 = mean + disc, mean - disc
    u = [math.cos(theta), math.sin(theta)]
    v = [-math.sin(theta), math.cos(theta)]
    hw = 2.0 * math.sqrt(max(l1, 0.0))
    hh = 2.0 * math.sqrt(max(l2, 0.0))
    # u should be the long axis (the torso's width direction)
    if hw < hh:
        u, v = v, u
        hw, hh = hh, hw
    return {"cx": round(cx, 2), "cy": round(cy, 2),
            "u": [round(u[0], 6), round(u[1], 6)],
            "v": [round(v[0], 6), round(v[1], 6)],
            "hw": round(hw, 2), "hh": round(hh, 2), "count": count}
