"""
88x31 webring button. Same lettering and animation as homepage banner

Colour is separable from geometry:

    pixel = C0*d0 + C1*d1 + C2*d2 + BG*(1 - d0 - d1 - d2)

d0/d1/d2 carry no colour, so quantising those instead of finished pixels gives
frame data that is valid for any gif. Output is built once and a gif only
rewrites its colour tables.
"""

import math
import random
import threading
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter

BUTTON_W, BUTTON_H = 88, 31
MARGIN_X = 2              # keep the lettering off the edge
SUPERSAMPLE = 8
COLORS = 64               # looks almost identical to 128+

BG = (0x16, 0x16, 0x18)   # --dark

CELL_ASPECT = 0.6 - 0.015     # monospace advance minus letter-spacing

# three stacked gradients, gd-0 on top, each fading to transparent at 70.71%
ANGLES = (217, 127, 336)
DEFAULT_HSL = ((138, 92, 55), (219, 53, 69), (252, 82, 56))
FADE_STOP = 0.7071

# the two glyphs
SHADE_ALPHA = {"█": 1.0, "░": 0.25}

REVEAL_MS = 1600
HOLD_MS = 1400
FRAME_MS = 50
REVEAL_SEED = 7           # dissolve rhythm is part of the artwork
SHARPEN = 80

# unsharp overshot... store planes in the middle half of the range
_HEADROOM_SCALE, _HEADROOM_OFFSET = 0.5, 64
_WEIGHT_SCALE = 1.0 / (255 * _HEADROOM_SCALE)

_lock = threading.Lock()
_template = None


def hsl_to_rgb(h, s, l):
    h, s, l = h / 360.0, s / 100.0, l / 100.0
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h * 6) % 2 - 1))
    m = l - c / 2
    r, g, b = [
        (c, x, 0), (x, c, 0), (0, c, x), (0, x, c), (x, 0, c), (c, 0, x)
    ][int(h * 6) % 6]
    return tuple(round((v + m) * 255) for v in (r, g, b))


def roll_colors():
    """Three colours in a nice range"""
    return tuple(
        hsl_to_rgb(random.randint(0, 360), random.randint(42, 98), random.randint(40, 90))
        for _ in range(3)
    )


def default_colors():
    return tuple(hsl_to_rgb(*hsl) for hsl in DEFAULT_HSL)


def _load_cells():
    """Inked cells of the banner as (x, y, alpha)"""
    rows = [r for r in (Path(__file__).parent / "banner.txt").read_text().split("\n")
            if r.strip()]
    width = max(len(r) for r in rows)
    cells = [(x, y, SHADE_ALPHA[ch])
             for y, row in enumerate(rows)
             for x, ch in enumerate(row.ljust(width))
             if ch in SHADE_ALPHA]
    return cells, width, len(rows)


def _gradient_alpha(w, h, angle_deg):
    """Alpha ramp of one CSS linear-gradient"""
    # CSS fades stops in alpha therefore only move it, never RGB.
    # lets colour be pulled out of geometry
    a = math.radians(angle_deg)
    dx, dy = math.sin(a), -math.cos(a)          # CSS 0deg points up
    length = abs(w * math.sin(a)) + abs(h * math.cos(a))
    cx, cy = w / 2.0, h / 2.0

    px = []
    for y in range(h):
        oy = (y + 0.5) - cy
        for x in range(w):
            t = ((x + 0.5 - cx) * dx + oy * dy) / length + 0.5
            if t <= 0:
                px.append(255)
            elif t >= FADE_STOP:
                px.append(0)
            else:
                px.append(round(255 * (1.0 - t / FADE_STOP)))

    img = Image.new("L", (w, h))
    img.putdata(px)
    return img


def _weight_planes(w, h):
    """Each layers share of the pixel after stacking."""
    # A0, A1*(1-A0), A2*(1-A0)*(1-A1). sum to the stacks own alpha
    a0, a1, a2 = (_gradient_alpha(w, h, angle) for angle in ANGLES)
    inv0, inv1 = ImageChops.invert(a0), ImageChops.invert(a1)
    return (
        a0,
        ImageChops.multiply(a1, inv0),
        ImageChops.multiply(ImageChops.multiply(a2, inv0), inv1),
    )


def _color_tables(data):
    """Offset and entry count of every colour table in a GIF, global + local"""
    if data[:3] != b"GIF":
        raise ValueError("not a GIF")

    def skip_blocks(i):
        while data[i]:
            i += data[i] + 1
        return i + 1

    tables = []
    packed = data[10]
    i = 13
    if packed & 0x80:
        count = 2 ** ((packed & 0x07) + 1)
        tables.append((i, count))
        i += 3 * count

    while i < len(data):
        block = data[i]
        if block == 0x21:                      # extension
            i = skip_blocks(i + 2)
        elif block == 0x2C:                    # image descriptor
            local = data[i + 9]
            i += 10
            if local & 0x80:
                count = 2 ** ((local & 0x07) + 1)
                tables.append((i, count))
                i += 3 * count
            i = skip_blocks(i + 1)             # LZW code size, then data blocks
        elif block == 0x3B:                    # trailer
            break
        else:
            raise ValueError(f"unexpected GIF block 0x{block:02x} at {i}")
    return tables


class _Template:
    """The parts of the GIF a colour roll cant change"""

    def __init__(self, data, tables, weights):
        self.data = bytes(data)
        self.tables = tables       # [(offset, [weight index per entry])]
        self.weights = weights     # [(w0, w1, w2, bg share)], deduplicated
        self.entries = sum(len(idx) for _, idx in tables)

    def render(self, colors):
        (r0, g0, b0), (r1, g1, b1), (r2, g2, b2) = colors
        br, bg_, bb = BG
        # all tables together hold at most COLORS distinct triples, so the
        # arithmetic runs once per triple and the rest is byte shuffling
        lut = [bytes((
            min(255, max(0, round(r0 * w0 + r1 * w1 + r2 * w2 + br * wbg))),
            min(255, max(0, round(g0 * w0 + g1 * w1 + g2 * w2 + bg_ * wbg))),
            min(255, max(0, round(b0 * w0 + b1 * w1 + b2 * w2 + bb * wbg))),
        )) for w0, w1, w2, wbg in self.weights]

        out = bytearray(self.data)
        for offset, indices in self.tables:
            out[offset:offset + 3 * len(indices)] = b"".join([lut[i] for i in indices])
        return bytes(out)


def _build_template():
    cells, cols, rows = _load_cells()

    grid_w = (BUTTON_W - 2 * MARGIN_X) * SUPERSAMPLE
    cell_w = grid_w / cols
    cell_h = cell_w / CELL_ASPECT
    grid_h = round(cell_h * rows)

    canvas_w, canvas_h = BUTTON_W * SUPERSAMPLE, BUTTON_H * SUPERSAMPLE
    gx, gy = MARGIN_X * SUPERSAMPLE, round((canvas_h - grid_h) / 2)

    planes = _weight_planes(grid_w, grid_h)
    headroom = [round(v * _HEADROOM_SCALE + _HEADROOM_OFFSET) for v in range(256)]
    sharpen = ImageFilter.UnsharpMask(1, SHARPEN, 0)

    rng = random.Random(REVEAL_SEED)
    delays = [rng.random() * REVEAL_MS for _ in cells]

    weight_frames, durations, previous = [], [], None
    for step in range(math.ceil((REVEAL_MS + HOLD_MS) / FRAME_MS)):
        now = step * FRAME_MS
        visible = [c for c, d in zip(cells, delays) if d <= now]
        if len(visible) == previous:
            durations[-1] += FRAME_MS
            continue
        previous = len(visible)

        mask = Image.new("L", (grid_w, grid_h), 0)
        for x, y, shade in visible:
            mask.paste(round(shade * 255),
                       (round(x * cell_w), round(y * cell_h),
                        round((x + 1) * cell_w), round((y + 1) * cell_h)))

        channels = []
        for plane in planes:
            full = Image.new("L", (canvas_w, canvas_h), 0)
            full.paste(ImageChops.multiply(plane, mask), (gx, gy))
            small = full.resize((BUTTON_W, BUTTON_H), Image.Resampling.BOX)
            channels.append(small.point(headroom).filter(sharpen))

        weight_frames.append(Image.merge("RGB", channels))
        durations.append(FRAME_MS)

    # quantising weights rather than colours is what keeps the frame data valid
    # for every roll, last frame covers the full range
    palette = weight_frames[-1].quantize(colors=COLORS,
                                         method=Image.Quantize.MEDIANCUT,
                                         dither=Image.Dither.NONE)
    indexed = [f.quantize(palette=palette, dither=Image.Dither.NONE)
               for f in weight_frames]

    buf = BytesIO()
    # optimize stores each frame as a diff bbox (for additive reveal)
    indexed[0].save(buf, format="GIF", save_all=True, append_images=indexed[1:],
                    duration=durations, loop=0, disposal=1, optimize=True)
    data = buf.getvalue()

    # Pil writes a local colour table per frame on top of the global one, so patch them all
    tables, weights, seen = [], [], {}
    for offset, count in _color_tables(data):
        indices = []
        for i in range(offset, offset + 3 * count, 3):
            raw = data[i:i + 3]
            at = seen.get(raw)
            if at is None:
                at = seen[raw] = len(weights)
                w0, w1, w2 = ((v - _HEADROOM_OFFSET) * _WEIGHT_SCALE for v in raw)
                weights.append((w0, w1, w2, 1.0 - w0 - w1 - w2))
            indices.append(at)
        tables.append((offset, indices))

    return _Template(data, tables, weights)


def template():
    """Built once per process, on first use."""
    global _template
    if _template is None:
        with _lock:
            if _template is None:
                _template = _build_template()
    return _template


def render(colors):
    """GIF bytes for one colour roll."""
    return template().render(colors)
