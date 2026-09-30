/*
 * display test page
 */
(function () {
    var stage = document.getElementById('display_stage');
    var view = document.getElementById('display_view');
    var labelText = document.getElementById('display_label_text');
    if (!stage) return;

    var W = 0, H = 0;  // view in device px
    var test = null, frame = 0;
    var anim = 0, idle = 0, lock = null, gpu = null;
    var hz = 0, speed = 2, paused = false, pinned = false;
    var SPEEDS = [240, 480, 960, 1920, 3840];  // css px/s

    // ------------------------------------------------------------------ helpers
    function dpr() { return window.devicePixelRatio || 1; }
    function px(n) { return Math.round(n * dpr()); }
    function pct(p) { return Math.round(p * 2.55); }
    function gray(v) { return 'rgb(' + v + ',' + v + ',' + v + ')'; }
    function rgb(v, m) { return 'rgb(' + v * m[0] + ',' + v * m[1] + ',' + v * m[2] + ')'; }

    function range(a, b) {
        var out = [];
        for (var i = a; i <= b; i++) out.push(i);
        return out;
    }

    // label color on gray value
    function ink(v) { return gray(v < 128 ? v + 64 : v - 64); }

    // compute a gray as bright as the color
    function luma(c) {
        var y = 0.2126 * Math.pow(c[0] / 255, 2.2) + 0.7152 * Math.pow(c[1] / 255, 2.2)
            + 0.0722 * Math.pow(c[2] / 255, 2.2);
        return Math.round(255 * Math.pow(y, 1 / 2.2));
    }

    function median(list) {
        var s = list.slice().sort(function (a, b) { return a - b; });
        return s[s.length >> 1];
    }

    // median finds frame time, mean of frames near it cancel timer rounding
    // dont care about frame drops
    function rate(deltas) {
        var mid = median(deltas);
        var kept = deltas.filter(function (d) { return d > mid / 2 && d < mid * 1.5; });
        return 1000 * kept.length / kept.reduce(function (a, b) { return a + b; }, 0);
    }

    // advertised rate. in reality clocks run a bit off -> closest multiple of 5 or 12
    // within 1.5%. if none there = nearest integer as fallback
    function nominal(hz) {
        var best = Math.round(hz), off = Infinity;
        for (var n = Math.ceil(hz * 0.985); n <= hz * 1.015; n++) {
            if ((n % 5 === 0 || n % 12 === 0) && Math.abs(n - hz) < off) {
                best = n;
                off = Math.abs(n - hz);
            }
        }
        return best;
    }

    function el(tag, cls) {
        var e = document.createElement(tag);
        if (cls) e.className = cls;
        return e;
    }

    // h 0..1, full saturation
    function hue(h) {
        function k(n) {
            var t = (n + h * 6) % 6;
            return 255 * (1 - Math.max(0, Math.min(t, 4 - t, 1)));
        }
        return [k(5), k(3), k(1)];
    }

    // firefox throws on p3 :<
    function ctx2d(cv, space) {
        try {
            var c = cv.getContext('2d', { colorSpace: space || 'srgb' });
            if (c) return c;
        } catch (err) { }
        return cv.getContext('2d');
    }

    var P3_CANVAS = (function () {
        var c = ctx2d(el('canvas'), 'display-p3');
        return !!(c && c.getContextAttributes && c.getContextAttributes().colorSpace === 'display-p3');
    })();

    // 1 canvas px is now = 1 device px
    function canvas(space) {
        var cv = el('canvas');
        cv.width = W;
        cv.height = H;
        view.append(cv);
        return ctx2d(cv, space);
    }

    // repeat pixels exact
    function pattern(ctx, rows) {
        var tile = el('canvas');
        tile.width = rows[0].length;
        tile.height = rows.length;
        var t = tile.getContext('2d');
        rows.forEach(function (row, y) {
            row.forEach(function (c, x) {
                t.fillStyle = c;
                t.fillRect(x, y, 1, 1);
            });
        });
        return ctx.createPattern(tile, 'repeat');
    }

    function header(ctx, names) {
        var top = px(28);
        ctx.fillStyle = '#000';
        ctx.fillRect(0, 0, W, top);
        ctx.font = px(13) + 'px monospace';
        ctx.textAlign = 'center';
        ctx.fillStyle = gray(200);
        names.forEach(function (name, i) {
            ctx.fillText(name, (i + 0.5) * W / names.length, top - px(9));
        });
        return top;
    }

    // ------------------------------------------------------------------- frames
    var WHITE = [[1, 1, 1]];
    var RGBW = [[1, 1, 1], [1, 0, 0], [0, 1, 0], [0, 0, 1]];
    var COLORS = [['red', '#f00'], ['green', '#0f0'], ['blue', '#00f'],
                  ['cyan', '#0ff'], ['magenta', '#f0f'], ['yellow', '#ff0']]; // the standard primaries

    function bg(name, css) {
        return { name: name, draw: function () { view.style.background = css; } };
    }

    function grays(list) {
        return list.map(function (p) { return bg('gray ' + p + '%', gray(pct(p))); });
    }

    function colors() {
        return COLORS.map(function (c) { return bg(c[0], c[1]); });
    }

    function tag(parent, text, bg, top) {
        var t = el('span', 'display_tag');
        t.textContent = text;
        t.style.color = ink(luma(bg));
        if (top) t.style.top = top;
        parent.append(t);
    }

    // band per level and row per channel
    function bands(levels, masks, labels) {
        return function () {
            var ctx = canvas();
            var n = levels.length;
            ctx.font = px(11) + 'px monospace';
            ctx.textAlign = 'center';
            masks.forEach(function (m, r) {
                var y = Math.round(r * H / masks.length);
                var h = Math.round((r + 1) * H / masks.length) - y;
                levels.forEach(function (v, i) {
                    var x = Math.round(i * W / n), w = Math.round((i + 1) * W / n) - x;
                    ctx.fillStyle = rgb(v, m);
                    ctx.fillRect(x, y, w, h);
                    if (labels) {
                        ctx.fillStyle = ink(v);
                        ctx.fillText(v, x + w / 2, y + px(18));
                    }
                });
            });
        };
    }

    // http://www.lagom.nl/ type-beat style
    function squares(bg, levels, ink) {
        return function () {
            var ctx = canvas();
            var cols = 8, rows = Math.ceil(levels.length / cols);
            var s = Math.floor(Math.min(W / (cols * 1.35), H / (rows * 1.8)));
            var gx = Math.round(s * 0.3), gy = Math.round(s * 0.6);
            var x0 = (W - cols * s - (cols - 1) * gx) >> 1;
            var y0 = (H - rows * s - (rows - 1) * gy) >> 1;
            ctx.fillStyle = gray(bg);
            ctx.fillRect(0, 0, W, H);
            ctx.font = Math.round(s / 5) + 'px monospace';
            ctx.textAlign = 'center';
            levels.forEach(function (v, i) {
                var x = x0 + (i % cols) * (s + gx), y = y0 + Math.floor(i / cols) * (s + gy);
                ctx.fillStyle = gray(v);
                ctx.fillRect(x, y, s, s);
                ctx.fillStyle = gray(ink);
                ctx.fillText(v, x + s / 2, y + s + s / 4);
            });
        };
    }

    // scanlines avg 50% light, matching patch = gamma
    var GAMMAS = [1.8, 2.0, 2.2, 2.4, 2.6];

    function gamma() {
        var ctx = canvas();
        var top = header(ctx, GAMMAS.map(function (g) { return g.toFixed(1); }));
        RGBW.forEach(function (m, r) {
            var y = top + Math.round(r * (H - top) / 4);
            var h = top + Math.round((r + 1) * (H - top) / 4) - y;
            ctx.fillStyle = pattern(ctx, [['#000'], [rgb(255, m)]]);
            ctx.fillRect(0, y, W, h);
            GAMMAS.forEach(function (g, i) {
                var x = Math.round(i * W / GAMMAS.length);
                var w = Math.round((i + 1) * W / GAMMAS.length) - x;
                var s = Math.round(Math.min(w, h) * 0.5);
                ctx.fillStyle = rgb(Math.round(255 * Math.pow(0.5, 1 / g)), m);
                ctx.fillRect(x + ((w - s) >> 1), y + ((h - s) >> 1), s, s);
            });
        });
    }

    // browser clips what display cant show
    function tiles() {
        var grid = el('div', 'display_tiles');
        [[1, 0, 0], [0, 1, 0], [0, 0, 1], [0, 1, 1], [1, 0, 1], [1, 1, 0]].forEach(function (c) {
            var outer = el('div'), mid = el('div'), inner = el('div');
            var bg = c.map(function (v) { return v * 255; });
            outer.style.background = 'color(srgb ' + c.join(' ') + ')';
            mid.style.background = 'color(display-p3 ' + c.join(' ') + ')';
            inner.style.background = 'color(rec2020 ' + c.join(' ') + ')';
            tag(outer, 'srgb', bg);
            tag(mid, 'p3', bg);
            tag(inner, 'rec2020', bg);
            mid.append(inner);
            outer.append(mid);
            grid.append(outer);
        });
        view.append(grid);
    }

    // same hues: top is srgb, bottom p3
    function split() {
        var ctx = canvas('display-p3');
        var mid = H >> 1;
        for (var x = 0; x < W; x++) {
            var c = hue(x / W);
            ctx.fillStyle = 'rgb(' + c.join(',') + ')';
            ctx.fillRect(x, 0, 1, mid);
            ctx.fillStyle = 'color(display-p3 ' + c.map(function (v) { return v / 255; }).join(' ') + ')';
            ctx.fillRect(x, mid, 1, H - mid);
        }
        tag(view, 'srgb', hue(0));
        tag(view, 'p3', hue(0), 'calc(50% + 7px)');
    }

    // hue across, white top, black bottom
    function field(space) {
        return function () {
            var ctx = canvas(space);
            var img = ctx.createImageData(W, H), d = img.data, i = 0;
            var cols = [];
            for (var x = 0; x < W; x++) cols.push(hue(x / W));
            for (var y = 0; y < H; y++) {
                var t = y / (H - 1) * 2;  // 0 white, 1 pure, 2 black
                var add = t < 1 ? 255 * (1 - t) : 0;
                var mul = t < 1 ? t : 2 - t;
                for (x = 0; x < W; x++) {
                    var c = cols[x];
                    d[i++] = c[0] * mul + add;
                    d[i++] = c[1] * mul + add;
                    d[i++] = c[2] * mul + add;
                    d[i++] = 255;
                }
            }
            ctx.putImageData(img, 0, 0);
        };
    }

    // https://www.xrite.com good old colorchecker classic in approx srgb
    var CHECKER = [
        ['735244', 'dark skin'], ['c29682', 'light skin'], ['627a9d', 'blue sky'],
        ['576c43', 'foliage'], ['8580b1', 'blue flower'], ['67bdaa', 'bluish green'],
        ['d67e2c', 'orange'], ['505ba6', 'purplish blue'], ['c15a63', 'moderate red'],
        ['5e3c6c', 'purple'], ['9dbc40', 'yellow green'], ['e0a32e', 'orange yellow'],
        ['383d96', 'blue'], ['469449', 'green'], ['af363c', 'red'],
        ['e7c71f', 'yellow'], ['bb5695', 'magenta'], ['0885a1', 'cyan'],
        ['f3f3f2', 'white'], ['c8c8c8', 'neutral 8'], ['a0a0a0', 'neutral 6.5'],
        ['7a7a79', 'neutral 5'], ['555555', 'neutral 3.5'], ['343434', 'black']];

    function checker() {
        var grid = el('div', 'display_checker');
        CHECKER.forEach(function (c) {
            var patch = el('div');
            patch.style.background = '#' + c[0];
            tag(patch, c[1], [0, 2, 4].map(function (i) { return parseInt(c[0].substr(i, 2), 16); }));
            grid.append(patch);
        });
        view.append(grid);
    }

    // whole px per frame, no judder (the word for timing-error motion blur, seriously, google it)
    function motion() {
        var ctx = canvas();
        var bgs = [48, 128, 208];
        var laneH = H / bgs.length;
        var s = Math.round(laneH * 0.4);
        var x = 0, last = 0, deltas = [];
        ctx.font = px(13) + 'px monospace';

        function tick(t) {
            if (last) deltas.push(t - last);
            if (deltas.length > 120) deltas.shift();
            last = t;
            if (deltas.length > 10) hz = rate(deltas);
            var step = Math.max(1, Math.round(SPEEDS[speed] * dpr() / (hz || 60)));
            if (!paused) x = (x + step) % (W + s);

            bgs.forEach(function (bg, i) {
                var y = Math.round(i * laneH), h = Math.round((i + 1) * laneH) - y;
                var oy = y + ((h - s) >> 1);
                ctx.fillStyle = gray(bg);
                ctx.fillRect(0, y, W, h);
                ctx.fillStyle = '#fff';
                ctx.fillRect(x - s, oy, s, s >> 1);
                ctx.fillStyle = '#000';
                ctx.fillRect(x - s, oy + (s >> 1), s, s - (s >> 1));
            });
            ctx.fillStyle = gray(160);
            ctx.fillText((hz || 0).toFixed(1) + ' Hz | ' + step + ' px/frame | ' + SPEEDS[speed] + ' px/s'
                + (paused ? ' | paused' : ''), px(12), px(24));
            anim = requestAnimationFrame(tick);
        }
        anim = requestAnimationFrame(tick);
    }

    var SAMPLE = 'The quick brown fox jumps over the lazy dog. 0123456789 Il1| O0 rn m {}[] '; // beloved sample text
    var FONTS = ['system-ui, sans-serif', 'Georgia, serif', 'ui-monospace, Consolas, monospace'];

    function textFrame() {
        var box = el('div', 'display_text');
        for (var side = 0; side < 2; side++) {
            var panel = el('div');
            FONTS.forEach(function (font) {
                [10, 12, 14, 18].forEach(function (size) {
                    var p = el('p');
                    p.style.font = size + 'px ' + font;
                    p.textContent = size + ' ' + SAMPLE;
                    panel.append(p);
                });
            });
            box.append(panel);
        }
        view.append(box);
    }

    var K = '#000', L = '#fff';
    var GRIDS = [
        ['checker', [[K, L], [L, K]]],
        ['v lines', [[K, L]]],
        ['h lines', [[K], [L]]],
        ['checker 2px', [[K, K, L, L], [K, K, L, L], [L, L, K, K], [L, L, K, K]]],
        ['red / cyan', [['#f00', '#0ff']]],
        ['green / magenta', [['#0f0', '#f0f']]]
    ];

    function pixelGrid() {
        var ctx = canvas();
        var top = header(ctx, GRIDS.map(function (g) { return g[0]; }));
        GRIDS.forEach(function (g, i) {
            var x = Math.round(i * W / GRIDS.length), w = Math.round((i + 1) * W / GRIDS.length) - x;
            ctx.fillStyle = pattern(ctx, g[1]);
            ctx.fillRect(x, top, w, H - top);
        });
    }

    // 4:2:0 turns this mushy
    var CHROMA = [['#f00', '#00f'], ['#00f', '#f00'], ['#0f0', '#f0f'], ['#f0f', '#0f0'],
                  ['#ff0', '#00f'], ['#0ff', '#f00'], ['#f00', '#000'], ['#00f', '#000']];

    function chroma() {
        var grid = el('div', 'display_chroma');
        CHROMA.forEach(function (c) {
            var cell = el('div');
            cell.style.color = c[0];
            cell.style.background = c[1];
            cell.textContent = SAMPLE + SAMPLE + SAMPLE;
            grid.append(cell);
        });
        view.append(grid);
    }

    // extended tone mapping test, above 1.0 goes past sdr white
    function hdr() {
        var row = el('div', 'display_hdr'), note = el('div', 'display_caption');
        view.append(row, note);
        var display = matchMedia('(dynamic-range: high)').matches ? 'yes' : 'no';
        if (!navigator.gpu) {
            note.textContent = 'display hdr: ' + display + ' | no webgpu';
            return;
        }
        gpu = gpu || navigator.gpu.requestAdapter().then(function (adapter) {
            if (!adapter) throw new Error('no gpu adapter');
            return adapter.requestDevice();
        });
        gpu.then(function (device) {
            var extended = true;
            [1, 2, 4, 8, 16].forEach(function (lin) {
                var cell = el('div'), cv = el('canvas'), tag = el('span');
                cv.width = cv.height = 4;
                tag.textContent = lin === 1 ? 'sdr white' : lin + 'x';
                cell.append(cv, tag);
                row.append(cell);
                var ctx = cv.getContext('webgpu');
                ctx.configure({ device: device, format: 'rgba16float', alphaMode: 'opaque',
                                toneMapping: { mode: 'extended' } });
                var cfg = ctx.getConfiguration ? ctx.getConfiguration() : null;
                if (cfg && (cfg.toneMapping || {}).mode !== 'extended') extended = false;
                var v = 1.055 * Math.pow(lin, 1 / 2.4) - 0.055;  // srgb encode
                var enc = device.createCommandEncoder();
                enc.beginRenderPass({ colorAttachments: [{
                    view: ctx.getCurrentTexture().createView(),
                    loadOp: 'clear', storeOp: 'store',
                    clearValue: { r: v, g: v, b: v, a: 1 }
                }] }).end();
                device.queue.submit([enc.finish()]);
            });
            note.textContent = 'display hdr: ' + display + ' | extended canvas: ' + (extended ? 'yes' : 'no');
        }).catch(function (err) {
            gpu = null;
            note.textContent = 'webgpu failed: ' + (err.message || err);
        });
    }

    // browser drawn test to emulate real sites
    var WEB = [
        bg('dark page', 'linear-gradient(#0d1117, #1c2230)'),
        bg('black to 12% gray', 'linear-gradient(to right, #000, #1f1f1f)'),
        bg('black to white', 'linear-gradient(to right, #000, #fff)'),
        bg('vignette', 'radial-gradient(circle at 50% 45%, #3a3a3a, #0a0a0a 70%)'),
        bg('sky', 'linear-gradient(#0b1a3a, #2d5d9f 45%, #9cc3e6 80%, #e8eef2)'),
        bg('sunset', 'linear-gradient(#150a2e, #5a1f5c 35%, #d2566b 65%, #f7b267)'),
        bg('hue wheel', 'conic-gradient(#f00, #ff0, #0f0, #0ff, #00f, #f0f, #f00)')
    ];

    // -------------------------------------------------------------------- tests
    var TESTS = [
        { name: 'pixels', hint: 'dead pixels, burn-in and ips glow', frames:
            [bg('black', '#000'), bg('white', '#fff')].concat(colors(), grays([2, 5, 10, 20, 30, 50, 75])) },
        { name: 'gradients', hint: 'banding', frames: [
            { name: 'ramps', draw: bands(range(0, 255), RGBW) },
            { name: 'gray', draw: bands(range(0, 255), WHITE) },
            { name: 'dark 0-31', draw: bands(range(0, 31), WHITE, true) },
            { name: 'bright 224-255', draw: bands(range(224, 255), WHITE, true) },
            { name: '32 steps', draw: bands(range(0, 31).map(function (i) {
                return Math.round(i * 255 / 31);
            }), WHITE, true) }] },
        { name: 'web gradients', hint: 'banding with css gradients', frames: WEB },
        { name: 'levels', hint: 'black crush, white clip and gamma', frames: [
            { name: 'black 1-24', draw: squares(0, range(1, 24), 90) },
            { name: 'white 231-254', draw: squares(255, range(231, 254), 150) },
            { name: 'gamma, squint. vanishing patch = yours', draw: gamma }] },
        { name: 'color', hint: 'gamut comparison', frames: [
            { name: 'gamut squares, visible inner = wide gamut', draw: tiles },
            { name: P3_CANVAS ? 'rainbow srgb vs p3' : 'rainbow srgb vs p3 | no p3 canvas', draw: split },
            { name: 'rainbow srgb', draw: field('srgb') },
            { name: P3_CANVAS ? 'rainbow p3' : 'rainbow p3 | no p3 canvas', draw: field('display-p3') },
            { name: 'colorchecker', draw: checker }] },
        { name: 'motion', hint: 'ghosting and refresh rate', frames: [
            { name: 'ufo', draw: motion }] },
        { name: 'text', hint: 'sharpness, scaling and chroma', frames: [
            { name: 'text', draw: textFrame },
            { name: 'pixel grid, moire = scaling', draw: pixelGrid },
            { name: 'chroma, mushy = 4:2:0', draw: chroma }] },
        { name: 'hdr', hint: 'brighter than white possible', frames: [
            { name: 'brighter = hdr works', draw: hdr }] }
    ];

    // -------------------------------------------------------------------- stage
    function show() {
        cancelAnimationFrame(anim);
        view.replaceChildren();
        view.style.background = '';
        var f = test.frames[frame];
        labelText.textContent = '[' + (TESTS.indexOf(test) + 1) + '] ' + test.name + ' | '
            + (frame + 1) + '/' + test.frames.length + ' ' + f.name;
        poke();
        if (W && H) f.draw();
    }

    function step(d) {
        var n = test.frames.length;
        frame = (frame + d + n) % n;
        show();
    }

    function open(i) {
        test = TESTS[i];
        frame = 0;
        paused = false;
        if (document.activeElement) document.activeElement.blur();
        stage.hidden = false;
        if (!document.fullscreenElement && stage.requestFullscreen) {
            stage.requestFullscreen().catch(function () { });
        }
        if (navigator.wakeLock && !lock) {
            navigator.wakeLock.request('screen').then(function (l) { lock = l; }, function () { });
        }
        show();
    }

    function close() {
        cancelAnimationFrame(anim);
        test = null;
        stage.hidden = true;
        view.replaceChildren();
        if (document.fullscreenElement) document.exitFullscreen().catch(function () { });
        if (lock) lock.release();
        lock = null;
    }

    // used to poke stage out of idle status (no mouse movement). resets timer each poke
    function poke() {
        stage.classList.remove('idle');
        clearTimeout(idle);
        idle = setTimeout(function () { stage.classList.add('idle'); }, 2000);
    }

    // exact device px. safari for example only gives css px :(
    var sizer = new ResizeObserver(function (entries) {
        var e = entries[0];
        var box = e.devicePixelContentBoxSize && e.devicePixelContentBoxSize[0];
        W = box ? box.inlineSize : Math.round(e.contentRect.width * dpr());
        H = box ? box.blockSize : Math.round(e.contentRect.height * dpr());
        if (test) show();
    });
    try {
        sizer.observe(view, { box: 'device-pixel-content-box' });
    } catch (err) {
        sizer.observe(view);
    }

    // esc out of fullscreen = done
    document.addEventListener('fullscreenchange', function () {
        if (!document.fullscreenElement && test) close();
    });

    // click, tap, swipe: next screen. when in motion next speed
    function advance(d) {
        if (test.name === 'motion') speed = (speed + d + SPEEDS.length) % SPEEDS.length;
        else step(d);
    }

    stage.addEventListener('mousemove', poke);
    stage.addEventListener('click', function () { advance(1); });
    stage.addEventListener('contextmenu', function (e) {
        e.preventDefault();
        if (!touch) advance(-1);  // android long press lands here too lol
    });

    // mouse never fires these. swipe left/right step, down closes
    // never though i'd be working with touch events this way lmao
    var touch = null;
    stage.addEventListener('touchstart', function (e) {
        var t = e.touches[0];
        touch = e.touches.length === 1 ? { x: t.clientX, y: t.clientY, at: e.timeStamp } : null;
        poke();
    }, { passive: true });
    stage.addEventListener('touchcancel', function () { touch = null; });
    stage.addEventListener('touchend', function (e) {
        if (!touch || !test || e.target.closest('button')) return;
        var t = e.changedTouches[0];
        var dx = t.clientX - touch.x, dy = t.clientY - touch.y, held = e.timeStamp - touch.at;
        touch = null;
        e.preventDefault();  // handled here... stop synthetic click
        if (Math.max(Math.abs(dx), Math.abs(dy)) < 30) {
            if (held < 500) advance(1);
        }
        else if (Math.abs(dx) > Math.abs(dy)) advance(dx < 0 ? 1 : -1);
        else if (dy > 0) close();
    }, { passive: false });
    document.getElementById('display_close').addEventListener('click', function (e) {
        e.stopPropagation();
        close();
    });

    document.addEventListener('keydown', function (e) {
        if (e.ctrlKey || e.metaKey || e.altKey) return;
        var n = '123456789'.indexOf(e.key);
        if (n >= 0 && n < TESTS.length) open(n);
        else if (!test) return;
        else if (e.key === 'ArrowRight' || e.key === 'PageDown') step(1);
        else if (e.key === 'ArrowLeft' || e.key === 'PageUp') step(-1);
        else if (e.key === ' ') {
            if (test.name === 'motion') paused = !paused;
            else step(1);
        }
        else if (e.key === 'ArrowUp') speed = Math.min(SPEEDS.length - 1, speed + 1);
        else if (e.key === 'ArrowDown') speed = Math.max(0, speed - 1);
        else if (e.key === 'h') {
            pinned = !pinned;
            stage.classList.toggle('pinned', pinned);
        }
        else if (e.key === 'Escape' || e.key === 'Backspace' || e.key === 'q') close();
        else return;
        e.preventDefault();
    });

    // --------------------------------------------------------------------- info
    function fill(sectionId, values) {
        var section = document.getElementById(sectionId);
        var old = section.querySelectorAll('.ip_row');
        for (var i = 0; i < old.length; i++) old[i].remove();

        Object.keys(values).forEach(function (key) {
            var row = el('div', 'ip_row'), k = el('span', 'ip_k'), v = el('span', 'ip_v');
            var value = values[key];
            k.textContent = key;
            if (value === true || value === false) {
                v.className += value ? ' ip_yes' : ' ip_no';
                value = String(value);
            }
            v.textContent = value;
            row.append(k, v);
            section.append(row);
        });
    }

    function gamut() {
        // pros to anyone having a rec2020 compatible monitor - i dont
        var hit = ['rec2020', 'p3', 'srgb'].filter(function (g) {
            return matchMedia('(color-gamut: ' + g + ')').matches;
        });
        return hit[0] || 'unknown';
    }

    var payload = {};

    function info() {
        var d = dpr();
        var res = Math.round(screen.width * d) + ' x ' + Math.round(screen.height * d);
        // ... is used as skeleton, json button does hopefully not wrap when hz lands
        var head = res + ' @ ' + (hz ? nominal(hz) : '...') + ' Hz';
        var facts = {
            screen: screen.width + ' x ' + screen.height + ' css px',
            device_pixels: res,
            pixel_ratio: d,
            window: innerWidth + ' x ' + innerHeight,
            refresh: hz ? hz.toFixed(2) + ' Hz' : 'measuring...',
            color_depth: screen.colorDepth + ' bit',
            gamut: gamut(),
            hdr: matchMedia('(dynamic-range: high)').matches,
            p3_canvas: P3_CANVAS,
            webgpu: !!navigator.gpu
        };
        document.getElementById('display_res').textContent = head;
        fill('display_info', facts);
        payload = Object.assign({ display: head }, facts);
    }

    // requestAnimationFrame ticks at screen refresh
    function measure() {
        var last = 0, deltas = [];
        function tick(t) {
            if (last) deltas.push(t - last);
            last = t;
            if (deltas.length < 60) {
                requestAnimationFrame(tick);
            } else {
                hz = rate(deltas);
                info();
            }
        }
        requestAnimationFrame(tick);
    }

    // -------------------------------------------------------------------- copying
    function copy(value, icon) {
        navigator.clipboard.writeText(value).then(function () {
            icon.classList.remove('fa-copy');
            icon.classList.add('fa-check');

            // revert after 2 seconds
            setTimeout(function () {
                icon.classList.remove('fa-check');
                icon.classList.add('fa-copy');
            }, 2000);
        }).catch(function (err) {
            console.error('[Error]: copy failed.', err);
        });
    }

    document.getElementById('ip_copy_json').addEventListener('click', function () {
        copy(JSON.stringify(payload, null, 2), document.getElementById('ip_copy_json_icon'));
    });

    var list = document.getElementById('display_tests');
    TESTS.forEach(function (t, i) {
        var row = el('div', 'ip_row'), k = el('span', 'ip_k'), b = el('button'), v = el('span', 'ip_v');
        b.type = 'button';
        b.textContent = '[' + (i + 1) + '] ' + t.name;
        b.addEventListener('click', function () { open(i); });
        v.textContent = t.hint;
        k.append(b);
        row.append(k, v);
        list.append(row);
    });

    // moved to other screen = resize
    var settle = 0;
    window.addEventListener('resize', function () {
        clearTimeout(settle);
        settle = setTimeout(function () {
            info();
            measure();
        }, 500);
    });

    info();
    measure();
})();
