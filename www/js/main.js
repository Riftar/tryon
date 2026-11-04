/* tryon main client: pick a source (webcam / sample video / sample photo),
   pick a garment, click the shirt once - the tracker follows it and the
   garment is drawn onto it every frame. All local, all offline. */
(function () {
  "use strict";

  var W = 480, H = 360, DW = 240, DH = 180, S = W / DW;

  var state = {
    source: null,          // "webcam" | "video" | "photo"
    video: document.createElement("video"),
    photo: null,
    garment: null,         // HTMLImageElement
    target: null,
    tol: 0.08, scale: 1.0, offX: 0, offY: 0, opacity: 0.95,
    quad: null             // smoothed quad in display coords
  };
  state.video.muted = true; state.video.loop = true; state.video.playsInline = true;

  var canvas = document.getElementById("stage");
  var ctx = canvas.getContext("2d");
  var det = document.createElement("canvas");
  det.width = DW; det.height = DH;
  var dctx = det.getContext("2d", { willReadFrequently: true });
  var statusEl = document.getElementById("status");

  function setStatus(t) { statusEl.textContent = t; }

  function setSource(kind) {
    state.source = kind;
    state.quad = null;
    if (kind !== "webcam" && state.video.srcObject) {
      state.video.srcObject.getTracks().forEach(function (t) { t.stop(); });
      state.video.srcObject = null;
    }
    if (kind === "webcam") {
      navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } })
        .then(function (stream) {
          state.video.srcObject = stream;
          state.video.play();
          setStatus("camera live - click your shirt in the picture to start");
        })
        .catch(function (e) { setStatus("camera unavailable: " + e.message); });
    } else if (kind === "video") {
      state.video.src = "samples/model.webm";
      state.video.play();
      setStatus("sample video playing - click the red shirt to start");
    } else {
      state.photo = new Image();
      state.photo.onload = function () { setStatus("sample photo - click the red shirt to start"); };
      state.photo.src = "samples/model.png";
    }
    document.querySelectorAll(".srcbtn").forEach(function (b) {
      b.classList.toggle("active", b.dataset.src === kind);
    });
  }

  function setGarment(url) {
    var img = new Image();
    img.onload = function () { state.garment = img; };
    img.src = url;
    document.querySelectorAll(".gbtn").forEach(function (b) {
      b.classList.toggle("active", b.dataset.url === url);
    });
  }

  function pickTarget(mx, my) {          // display-canvas coords
    dctx.drawImage(sourceElement(), 0, 0, DW, DH);
    var p = dctx.getImageData(Math.floor(mx / S), Math.floor(my / S), 1, 1).data;
    state.target = [p[0], p[1], p[2]];
    state.quad = null;
    var sw = document.getElementById("swatch");
    sw.style.background = "rgb(" + p[0] + "," + p[1] + "," + p[2] + ")";
    setStatus("tracking color rgb(" + p[0] + "," + p[1] + "," + p[2] + ")");
  }

  function sourceElement() {
    return state.source === "photo" ? state.photo : state.video;
  }

  canvas.addEventListener("click", function (ev) {
    var r = canvas.getBoundingClientRect();
    pickTarget((ev.clientX - r.left) * (W / r.width),
               (ev.clientY - r.top) * (H / r.height));
  });

  // ---------- controls ----------
  function slider(id, label, lo, hi, val, step, oninput) {
    var row = document.createElement("div"); row.className = "control";
    var lab = document.createElement("label");
    var v = document.createElement("span"); v.className = "val";
    lab.appendChild(document.createTextNode(label)); lab.appendChild(v);
    var input = document.createElement("input");
    input.type = "range"; input.min = lo; input.max = hi; input.step = step; input.value = val;
    v.textContent = val;
    input.addEventListener("input", function () { v.textContent = input.value; oninput(+input.value); });
    row.appendChild(lab); row.appendChild(input);
    document.getElementById("controls").appendChild(row);
  }

  slider("tol", "color tolerance", 0.02, 0.4, state.tol, 0.01, function (x) { state.tol = x; });
  slider("scale", "garment size", 0.5, 2.0, state.scale, 0.05, function (x) { state.scale = x; });
  slider("offx", "nudge X", -60, 60, 0, 1, function (x) { state.offX = x; });
  slider("offy", "nudge Y", -60, 60, 0, 1, function (x) { state.offY = x; });
  slider("opacity", "opacity", 0.3, 1.0, state.opacity, 0.05, function (x) { state.opacity = x; });

  document.querySelectorAll(".srcbtn").forEach(function (b) {
    b.addEventListener("click", function () { setSource(b.dataset.src); });
  });

  fetch("/api/garments").then(function (r) { return r.json(); }).then(function (d) {
    var wrap = document.getElementById("garments");
    d.garments.forEach(function (g) {
      var b = document.createElement("button");
      b.className = "gbtn"; b.dataset.url = g.url; b.textContent = g.label;
      b.style.backgroundImage = "url(" + g.url + ")";
      b.addEventListener("click", function () { setGarment(g.url); });
      wrap.appendChild(b);
    });
    var up = document.createElement("button");
    up.className = "gbtn upload"; up.textContent = "upload PNG";
    var file = document.createElement("input");
    file.type = "file"; file.accept = "image/png"; file.style.display = "none";
    up.addEventListener("click", function () { file.click(); });
    file.addEventListener("change", function () {
      if (file.files[0]) setGarment(URL.createObjectURL(file.files[0]));
    });
    wrap.appendChild(up); wrap.appendChild(file);
    setGarment(d.garments[0].url);
  }).catch(function () {
    document.getElementById("gar").textContent = "garment list unavailable";
  });

  setSource("video");

  // ---------- render loop ----------
  function lerp(a, b, k) { return a + (b - a) * k; }

  function loop() {
    var el = sourceElement();
    var ready = state.source === "photo" ? !!state.photo
              : el.readyState >= 2;
    if (ready) {
      ctx.drawImage(el, 0, 0, W, H);
      if (state.target) {
        dctx.drawImage(el, 0, 0, DW, DH);
        var q = TRY.track(dctx.getImageData(0, 0, DW, DH), state.target, state.tol);
        if (q) {
          q.cx *= S; q.cy *= S; q.hw *= S; q.hh *= S;
          if (!state.quad) state.quad = q;
          var sm = state.quad;
          sm.cx = lerp(sm.cx, q.cx, 0.5); sm.cy = lerp(sm.cy, q.cy, 0.5);
          sm.hw = lerp(sm.hw, q.hw, 0.4); sm.hh = lerp(sm.hh, q.hh, 0.4);
          sm.u[0] = lerp(sm.u[0], q.u[0], 0.4); sm.u[1] = lerp(sm.u[1], q.u[1], 0.4);
          drawGarment(sm);
          setStatus("tracking - " + q.count + " px matched");
        } else {
          state.quad = null;
          setStatus("lost the color - click the shirt again");
        }
      }
    }
    requestAnimationFrame(loop);
  }

  function drawGarment(q) {
    if (!state.garment) return;
    var g = state.garment;
    var k = Math.min((2 * q.hw * state.scale) / g.height,
                     (2 * q.hh * state.scale) / g.width);
    var gw = k * g.width, gh = k * g.height;
    // context y-axis (image down) should align with the quad's long axis u
    var phi = Math.atan2(-q.u[0], q.u[1]);
    ctx.save();
    ctx.globalAlpha = state.opacity;
    ctx.translate(q.cx + state.offX, q.cy + state.offY);
    ctx.rotate(phi);
    ctx.drawImage(g, -gw / 2, -gh / 2, gw, gh);
    ctx.restore();
  }

  requestAnimationFrame(loop);
})();
