/* tryon JS tracker - mirrors tryon/tracker.py exactly.
   Same mask, same moments, same eigen fit: the Python reference is the
   tested spec; this twin runs realtime because pixels never leave the browser. */
(function () {
  "use strict";
  window.TRY = window.TRY || {};

  var MAX_DIST = Math.sqrt(3 * 255 * 255);

  function track(imageData, target, tol, minFrac) {
    var d = imageData.data, w = imageData.width, h = imageData.height;
    var tr = target[0], tg = target[1], tb = target[2];
    var count = 0, sx = 0, sy = 0, x, y, i, dr, dg, db;
    for (y = 0; y < h; y++) {
      for (x = 0; x < w; x++) {
        i = (y * w + x) * 4;
        dr = d[i] - tr; dg = d[i + 1] - tg; db = d[i + 2] - tb;
        if (Math.sqrt(dr * dr + dg * dg + db * db) / MAX_DIST <= tol) {
          count++; sx += x; sy += y;
        }
      }
    }
    if (count < Math.max(4, (minFrac || 0.0005) * w * h)) return null;
    var cx = sx / count, cy = sy / count;
    var sxx = 0, sxy = 0, syy = 0, dx, dy;
    for (y = 0; y < h; y++) {
      for (x = 0; x < w; x++) {
        i = (y * w + x) * 4;
        dr = d[i] - tr; dg = d[i + 1] - tg; db = d[i + 2] - tb;
        if (Math.sqrt(dr * dr + dg * dg + db * db) / MAX_DIST <= tol) {
          dx = x - cx; dy = y - cy;
          sxx += dx * dx; sxy += dx * dy; syy += dy * dy;
        }
      }
    }
    var cxx = sxx / count, cxy = sxy / count, cyy = syy / count;
    var theta = 0.5 * Math.atan2(2 * cxy, cxx - cyy);
    var mean = (cxx + cyy) / 2;
    var disc = Math.sqrt(Math.max(0, ((cxx - cyy) / 2) * ((cxx - cyy) / 2) + cxy * cxy));
    var l1 = mean + disc, l2 = mean - disc;
    var ux = Math.cos(theta), uy = Math.sin(theta);
    var vx = -uy, vy = ux;
    var hw = 2 * Math.sqrt(Math.max(l1, 0)), hh = 2 * Math.sqrt(Math.max(l2, 0));
    if (hw < hh) { var tx = ux; ux = vx; vx = tx; var ty = uy; uy = vy; vy = ty; var t = hw; hw = hh; hh = t; }
    return { cx: cx, cy: cy, u: [ux, uy], v: [vx, vy], hw: hw, hh: hh, count: count };
  }

  window.TRY.track = track;
})();
