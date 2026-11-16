/* Technical Officials Scheduler – splash screen shown while the app starts.
 * TOSSplash.show(container, { video, poster, icon, minMs, ready }) → { skip(), replay(), done }
 * The opening video holds three stacked scenes (run / bike / swim); each panel draws one scene from it,
 * in race order: swim, bike, run. Tap, click, Esc, Enter or Space skips. */
(function (W) {
  'use strict';
  // the scenes inside the 716 × 1284 video (thin navy lines between them are left out)
  var SCENES = {
    swim: { y: 863, h: 421, focus: 0.55 },
    bike: { y: 433, h: 419, focus: 0.50 },
    run:  { y: 0,   h: 421, focus: 0.38 }
  };
  var VW = 716, VH = 1284;

  function el(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text) e.textContent = text; return e; }

  function show(container, opts) {
    opts = opts || {};
    var minMs = opts.minMs == null ? 3000 : opts.minMs;
    var root = el('div', 'tos-splash');
    root.setAttribute('role', 'img');
    root.setAttribute('aria-label', 'Technical Officials Scheduler – www.trisport.me');

    var brand = el('div', 'sp-brand');
    var icon = el('img', 'sp-icon'); icon.src = opts.icon || 'icons/icon-512.png'; icon.alt = '';
    var nameWrap = el('div');
    var name = el('h1', 'sp-name');
    name.appendChild(el('span', '', 'Technical Officials'));
    name.appendChild(el('span', 'sp-gold', 'Scheduler'));
    nameWrap.appendChild(name); nameWrap.appendChild(el('div', 'sp-rule'));
    brand.appendChild(icon); brand.appendChild(nameWrap);

    var panels = el('div', 'sp-panels');
    var canvases = [];
    ['swim', 'bike', 'run'].forEach(function (key) {
      var p = el('div', 'sp-panel');
      var c = el('canvas'); c.dataset.scene = key;
      p.appendChild(c); p.appendChild(el('span', 'sp-label', key.toUpperCase()));
      panels.appendChild(p); canvases.push(c);
    });

    var site = el('div', 'sp-site'); site.innerHTML = 'www.<b>trisport</b>.me';
    var skipHint = el('div', 'sp-skip', 'Tap to skip');

    var video = el('video');
    video.muted = true; video.defaultMuted = true; video.loop = true; video.playsInline = true;
    video.setAttribute('muted', ''); video.setAttribute('playsinline', ''); video.setAttribute('webkit-playsinline', '');
    video.preload = 'auto'; video.src = opts.video || 'splash/splash.mp4';
    var poster = new Image(); poster.src = opts.poster || 'splash/poster.jpg';

    var stage = el('div', 'sp-stage');
    stage.appendChild(brand); stage.appendChild(panels);
    root.appendChild(stage); root.appendChild(site); root.appendChild(skipHint); root.appendChild(video);
    container.appendChild(root);

    // layout: film strip in wide windows, stacked scenes on tall screens
    function layout() {
      var r = root.getBoundingClientRect();
      var wide = r.width >= r.height * 1.05;
      root.classList.toggle('band', wide); root.classList.toggle('stack', !wide);
      canvases.forEach(function (c) {
        var b = c.getBoundingClientRect(), d = Math.min(W.devicePixelRatio || 1, 2);
        c.width = Math.max(2, Math.round(b.width * d)); c.height = Math.max(2, Math.round(b.height * d));
      });
      draw();
    }

    // draw each scene into its panel, cropped to fill it ("cover"), around the athlete
    function draw() {
      var src = video.readyState >= 2 ? video : (poster.complete && poster.naturalWidth ? poster : null);
      if (!src) return;
      var sx = (src === poster ? poster.naturalWidth / VW : 1);
      canvases.forEach(function (c) {
        var s = SCENES[c.dataset.scene], ctx = c.getContext('2d');
        var cw = c.width, ch = c.height, sa = VW / s.h, ca = cw / ch, w, h, x, y;
        if (ca > sa) { w = VW; h = VW / ca; x = 0; y = s.y + (s.h - h) / 2; }
        else { h = s.h; w = s.h * ca; y = s.y; x = Math.min(VW - w, Math.max(0, VW * s.focus - w / 2)); }
        ctx.drawImage(src, x * sx, y * sx, w * sx, h * sx, 0, 0, cw, ch);
      });
    }

    var running = true;
    function loop() {
      if (!running) return;
      draw();
      if (video.requestVideoFrameCallback) video.requestVideoFrameCallback(loop);
      else W.requestAnimationFrame(loop);
    }

    var ro = W.ResizeObserver ? new W.ResizeObserver(layout) : null;
    if (ro) ro.observe(root); else W.addEventListener('resize', layout);
    poster.onload = draw;
    video.addEventListener('loadeddata', draw);
    layout();

    function start() {
      root.classList.remove('go', 'out'); void root.offsetWidth; root.classList.add('go');
      try { video.currentTime = 0; } catch (e) { /* not loaded yet */ }
      var p = video.play(); if (p && p.catch) p.catch(function () { /* autoplay refused: the poster stays */ });
      running = true; loop();
    }

    var resolveDone, finished = false, timer;
    var done = new Promise(function (r) { resolveDone = r; });
    var ready = opts.ready || Promise.resolve();
    function finish() {
      if (finished) return; finished = true;
      clearTimeout(timer);
      root.classList.add('out');
      setTimeout(function () {
        running = false; video.pause();
        if (!opts.keep) { if (ro) ro.disconnect(); root.remove(); }
        document.removeEventListener('keydown', onKey, true);
        resolveDone();
      }, 520);
    }
    function onKey(e) { if (e.key === 'Escape' || e.key === 'Enter' || e.key === ' ') { e.preventDefault(); finish(); } }
    root.addEventListener('click', finish);
    document.addEventListener('keydown', onKey, true);

    start();
    var t0 = Date.now();
    ready.then(function () { timer = setTimeout(finish, Math.max(0, minMs - (Date.now() - t0))); });

    return {
      done: done,
      skip: finish,
      replay: function () {   // preview only: play the intro again
        finished = false; clearTimeout(timer); document.addEventListener('keydown', onKey, true);
        start(); timer = setTimeout(finish, minMs);
      }
    };
  }

  W.TOSSplash = { show: show };
})(window);
