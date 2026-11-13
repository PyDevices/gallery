# SPDX-FileCopyrightText: 2026 Brad Barnett
#
# SPDX-License-Identifier: MIT

"""Provide the color palette, layout scaler, and math helpers for Bit World.

Defines the 32-color Cozy Sci-Fi and Solarpunk RGB565 palette, portable random
number and integer trigonometry helpers, a responsive layout scaler for
landscape screens from 480x320 to 800x480, and dithered transition routines.

Needs: pygraphics.

Run it:

    import bit_palette

Tested on: unix MicroPython 1.30 (preview), CircuitPython 10.3, and CPython 3.12.
"""

from array import array
from random import getrandbits, seed
from pygraphics import RGB565, FrameBuffer

# Change these to match your setup.
REF_WIDTH = 800  # Reference landscape design width in pixels
REF_HEIGHT = 480  # Reference landscape design height in pixels
KEY = 0x0020  # Transparent color key; rgb565() shifts any matching color by +1


# Convert 8-bit red, green, and blue channels into a 16-bit RGB565 integer.
def rgb565(r, g, b):
    c = ((int(r) & 0xF8) << 8) | ((int(g) & 0xFC) << 3) | (int(b) >> 3)
    return c + 1 if c == KEY else c


# Interpolate linearly between two RGB tuples and return an RGB565 color.
def lerp565(rgb_a, rgb_b, t):
    if t <= 0.0:
        return rgb565(rgb_a[0], rgb_a[1], rgb_a[2])
    if t >= 1.0:
        return rgb565(rgb_b[0], rgb_b[1], rgb_b[2])
    r = rgb_a[0] + (rgb_b[0] - rgb_a[0]) * t
    g = rgb_a[1] + (rgb_b[1] - rgb_a[1]) * t
    b = rgb_a[2] + (rgb_b[2] - rgb_a[2]) * t
    return rgb565(r, g, b)


# Deep space, chassis shadow, and metallic slate tones.
VOID_RGB = (6, 8, 18)
ABYSS_RGB = (11, 16, 34)
NIGHT_RGB = (18, 26, 52)
DEEP_SLATE_RGB = (28, 40, 72)
SLATE_RGB = (46, 64, 104)
STEEL_RGB = (78, 102, 148)
MIST_RGB = (132, 160, 204)
SILVER_RGB = (192, 212, 238)

VOID = rgb565(*VOID_RGB)
ABYSS = rgb565(*ABYSS_RGB)
NIGHT = rgb565(*NIGHT_RGB)
DEEP_SLATE = rgb565(*DEEP_SLATE_RGB)
SLATE = rgb565(*SLATE_RGB)
STEEL = rgb565(*STEEL_RGB)
MIST = rgb565(*MIST_RGB)
SILVER = rgb565(*SILVER_RGB)

# Maker-lab warm brass, copper, amber, gold, and cream highlights.
DARK_WOOD = rgb565(32, 20, 16)
OAK = rgb565(58, 36, 26)
BRONZE = rgb565(98, 60, 32)
COPPER = rgb565(156, 88, 42)
AMBER = rgb565(224, 136, 44)
GOLD = rgb565(250, 192, 64)
SUN_YELLOW = rgb565(255, 234, 120)
CREAM = rgb565(248, 242, 224)
WHITE = rgb565(255, 255, 255)

# Bioluminescent cyan and hologram teal tones.
DEEP_TEAL = rgb565(8, 52, 68)
TEAL = rgb565(16, 108, 128)
CYAN = rgb565(32, 184, 212)
AQUA_GLOW = rgb565(92, 238, 248)
ICE_CYAN = rgb565(188, 252, 255)

# Solarpunk flora and mossy ruin greens.
DARK_MOSS = rgb565(14, 48, 36)
FOREST = rgb565(24, 88, 56)
MOSS = rgb565(48, 142, 78)
EMERALD = rgb565(84, 204, 108)
LIME_GLOW = rgb565(158, 244, 132)

# Plasma, crystal, and sunset accent colors.
PLUM = rgb565(48, 20, 68)
VIOLET = rgb565(104, 48, 148)
MAGENTA = rgb565(188, 64, 176)
NEON_PINK = rgb565(248, 108, 198)
CRIMSON = rgb565(196, 42, 68)
CORAL = rgb565(248, 96, 84)
ORANGE = rgb565(252, 142, 56)

# Flat 75-entry uint16 lookup table mapping byte (b - 46) for '.'..'x' to RGB565.
PALETTE_LUT = array(
    "H",
    (
        KEY, KEY,  # '.' (46), '/' (47)
        VOID, ABYSS, NIGHT, DEEP_SLATE, SLATE, STEEL, MIST, SILVER, WHITE, CREAM,  # '0'..'9'
        KEY, KEY, KEY, KEY, KEY, KEY, KEY,  # ':'..'@'
        KEY, KEY, KEY, KEY, KEY, KEY, KEY, KEY, KEY, KEY, KEY, KEY, KEY,  # 'A'..'M'
        KEY, KEY, KEY, KEY, KEY, KEY, KEY, KEY, KEY, KEY, KEY, KEY, KEY,  # 'N'..'Z'
        KEY, KEY, KEY, KEY, KEY, KEY,  # '['..'`'
        DARK_WOOD, OAK, BRONZE, COPPER, AMBER, GOLD, SUN_YELLOW,  # 'a'..'g'
        DEEP_TEAL, TEAL, CYAN, AQUA_GLOW, ICE_CYAN,  # 'h'..'l'
        DARK_MOSS, FOREST, MOSS, EMERALD, LIME_GLOW,  # 'm'..'q'
        PLUM, VIOLET, MAGENTA, NEON_PINK, CRIMSON, CORAL, ORANGE,  # 'r'..'x'
    ),
)

# Precomputed 256-entry sine table (-1024..1024) as a single constant buffer.
SIN256 = array(
    "h",
    b"\x00\x00\x19\x00\x32\x00\x4b\x00\x64\x00\x7d\x00\x96\x00\xaf\x00\xc7\x00\xe0\x00\xf8\x00\x11\x01\x29\x01\x41\x01\x58\x01\x70\x01\x87\x01\x9e\x01\xb5\x01\xcc\x01\xe2\x01\xf8\x01\x0e\x02\x23\x02\x38\x02\x4d\x02\x61\x02\x75\x02\x89\x02\x9c\x02\xaf\x02\xc2\x02"
    b"\xd4\x02\xe5\x02\xf6\x02\x07\x03\x17\x03\x27\x03\x36\x03\x45\x03\x53\x03\x61\x03\x6e\x03\x7a\x03\x87\x03\x92\x03\x9d\x03\xa8\x03\xb2\x03\xbb\x03\xc4\x03\xcc\x03\xd3\x03\xda\x03\xe1\x03\xe7\x03\xec\x03\xf0\x03\xf4\x03\xf8\x03\xfb\x03\xfd\x03\xfe\x03\xff\x03"
    b"\x00\x04\xff\x03\xfe\x03\xfd\x03\xfb\x03\xf8\x03\xf4\x03\xf0\x03\xec\x03\xe7\x03\xe1\x03\xda\x03\xd3\x03\xcc\x03\xc4\x03\xbb\x03\xb2\x03\xa8\x03\x9d\x03\x92\x03\x87\x03\x7a\x03\x6e\x03\x61\x03\x53\x03\x45\x03\x36\x03\x27\x03\x17\x03\x07\x03\xf6\x02\xe5\x02"
    b"\xd4\x02\xc2\x02\xaf\x02\x9c\x02\x89\x02\x75\x02\x61\x02\x4d\x02\x38\x02\x23\x02\x0e\x02\xf8\x01\xe2\x01\xcc\x01\xb5\x01\x9e\x01\x87\x01\x70\x01\x58\x01\x41\x01\x29\x01\x11\x01\xf8\x00\xe0\x00\xc7\x00\xaf\x00\x96\x00\x7d\x00\x64\x00\x4b\x00\x32\x00\x19\x00"
    b"\x00\x00\xe7\xff\xce\xff\xb5\xff\x9c\xff\x83\xff\x6a\xff\x51\xff\x39\xff\x20\xff\x08\xff\xef\xfe\xd7\xfe\xbf\xfe\xa8\xfe\x90\xfe\x79\xfe\x62\xfe\x4b\xfe\x34\xfe\x1e\xfe\x08\xfe\xf2\xfd\xdd\xfd\xc8\xfd\xb3\xfd\x9f\xfd\x8b\xfd\x77\xfd\x64\xfd\x51\xfd\x3e\xfd"
    b"\x2c\xfd\x1b\xfd\x0a\xfd\xf9\xfc\xe9\xfc\xd9\xfc\xca\xfc\xbb\xfc\xad\xfc\x9f\xfc\x92\xfc\x86\xfc\x79\xfc\x6e\xfc\x63\xfc\x58\xfc\x4e\xfc\x45\xfc\x3c\xfc\x34\xfc\x2d\xfc\x26\xfc\x1f\xfc\x19\xfc\x14\xfc\x10\xfc\x0c\xfc\x08\xfc\x05\xfc\x03\xfc\x02\xfc\x01\xfc"
    b"\x00\xfc\x01\xfc\x02\xfc\x03\xfc\x05\xfc\x08\xfc\x0c\xfc\x10\xfc\x14\xfc\x19\xfc\x1f\xfc\x26\xfc\x2d\xfc\x34\xfc\x3c\xfc\x45\xfc\x4e\xfc\x58\xfc\x63\xfc\x6e\xfc\x79\xfc\x86\xfc\x92\xfc\x9f\xfc\xad\xfc\xbb\xfc\xca\xfc\xd9\xfc\xe9\xfc\xf9\xfc\x0a\xfd\x1b\xfd"
    b"\x2c\xfd\x3e\xfd\x51\xfd\x64\xfd\x77\xfd\x8b\xfd\x9f\xfd\xb3\xfd\xc8\xfd\xdd\xfd\xf2\xfd\x08\xfe\x1e\xfe\x34\xfe\x4b\xfe\x62\xfe\x79\xfe\x90\xfe\xa8\xfe\xbf\xfe\xd7\xfe\xef\xfe\x08\xff\x20\xff\x39\xff\x51\xff\x6a\xff\x83\xff\x9c\xff\xb5\xff\xce\xff\xe7\xff",
)


# Look up the fast integer sine (-1024..1024) for a 0..255 phase index.
def isin(idx):
    return SIN256[idx & 0xFF]


# Look up the fast integer cosine (-1024..1024) for a 0..255 phase index.
def icos(idx):
    return SIN256[(idx + 64) & 0xFF]


# Generate a random integer in [lo, hi] using only getrandbits for port safety.
def rng_int(lo, hi):
    span = hi - lo + 1
    if span <= 1:
        return lo
    bits = 0
    n = span - 1
    while n:
        bits += 1
        n >>= 1
    return lo + (getrandbits(bits) % span)


# Seed the random number generator deterministically if supported.
def init_rng(val=42):
    try:
        seed(val)
    except Exception:
        pass


class Layout:
    """Scale coordinates and pixel-art metrics from 480x320 up to 800x480."""

    def __init__(self, width, height):
        self.w = width
        self.h = height
        self.sw = width / REF_WIDTH
        self.sh = height / REF_HEIGHT
        self.s = min(self.sw, self.sh)
        self.compact = width < 600 or height < 380
        # Choose an integer pixel-art magnification factor (2x on 480x320, 3x on 800x480).
        self.px = 2 if self.compact else 3
        self.tile_px = 2 if self.compact else 3
        self.bar_h = 28 if self.compact else 36
        self.scene_y = self.bar_h
        self.scene_h = height - self.bar_h
        self.pad = 6 if self.compact else 10

    # Scale a horizontal coordinate from the 800-wide reference design.
    def x(self, val):
        return int(val * self.sw)

    # Scale a vertical coordinate inside the full screen height.
    def y(self, val):
        return int(val * self.sh)

    # Scale a vertical coordinate inside the scene area below the stage bar.
    def sy(self, frac):
        return self.scene_y + int(frac * self.scene_h)

    # Scale a dimension uniformly using the smaller axis ratio.
    def u(self, val):
        return max(1, int(val * self.s))


# Paint a vertical RGB565 gradient into a FrameBuffer over the given rectangle.
def paint_gradient(fb, x, y, w, h, rgb_top, rgb_bot, step=2):
    if w <= 0 or h <= 0:
        return
    denom = max(1, h - 1)
    r0, g0, b0 = rgb_top
    dr = rgb_bot[0] - r0
    dg = rgb_bot[1] - g0
    db = rgb_bot[2] - b0
    s = max(1, step)
    for row in range(0, h, s):
        t = row / denom
        c = rgb565(r0 + dr * t, g0 + dg * t, b0 + db * t)
        bh = s if row + s <= h else h - row
        fb.fill_rect(x, y + row, w, bh, c)


# Draw a stylized pixel-art beveled panel with a corner highlight and border.
def draw_pixel_panel(fb, x, y, w, h, bg_col, border_col, hi_col=None, shadow_col=None):
    if w < 6 or h < 6:
        return
    if shadow_col is not None:
        fb.fill_rect(x + 3, y + 3, w, h, shadow_col)
    fb.fill_rect(x + 2, y + 2, w - 4, h - 4, bg_col)
    fb.hline(x + 2, y, w - 4, border_col)
    fb.hline(x + 2, y + h - 1, w - 4, border_col)
    fb.vline(x, y + 2, h - 4, border_col)
    fb.vline(x + w - 1, y + 2, h - 4, border_col)
    fb.pixel(x + 1, y + 1, border_col)
    fb.pixel(x + w - 2, y + 1, border_col)
    fb.pixel(x + 1, y + h - 2, border_col)
    fb.pixel(x + w - 2, y + h - 2, border_col)
    if hi_col is not None and w > 8:
        fb.hline(x + 3, y + 1, w - 6, hi_col)


# Draw a Bayer-inspired pixel curtain wipe across the scene during act transitions.
def draw_pixel_wipe(fb, x, y, w, h, progress, col_main=VOID, col_edge=CYAN):
    # Progress runs 0.0 -> 0.5 (closing) and 0.5 -> 1.0 (opening).
    if progress <= 0.0 or progress >= 1.0:
        return
    coverage = 1.0 - abs(progress * 2.0 - 1.0)
    cell = 16
    cols = (w + cell - 1) // cell
    for cx in range(cols):
        # Stagger columns slightly so the wipe sweeps left-to-right like a pixel wave.
        local = coverage * 1.25 - (cx / max(1, cols)) * 0.25
        if local <= 0.0:
            continue
        if local >= 1.0:
            fb.fill_rect(x + cx * cell, y, min(cell, w - cx * cell), h, col_main)
            continue
        fill_h = int(h * local)
        bx = x + cx * cell
        bw = min(cell, w - cx * cell)
        if progress < 0.5:
            fb.fill_rect(bx, y, bw, fill_h, col_main)
            if fill_h + 3 <= h:
                fb.fill_rect(bx, y + fill_h, bw, 3, col_edge)
        else:
            top_y = y + h - fill_h
            fb.fill_rect(bx, top_y, bw, fill_h, col_main)
            if top_y >= y + 3:
                fb.fill_rect(bx, top_y - 3, bw, 3, col_edge)


# Build a reusable RGB565 FrameBuffer tuple (bytearray, FrameBuffer).
def make_fb(w, h, fill_color=None):
    buf = bytearray(w * h * 2)
    fb = FrameBuffer(buf, w, h, RGB565)
    if fill_color is not None:
        fb.fill(fill_color)
    return buf, fb


class PanelState:
    """What one display buffer holds: which act, where its moving parts were, what it drew."""

    def __init__(self):
        self.act = -1
        self.rects = []
        self.sig = {}
        self.bar = None

    # True, and remember it, when value differs from what this buffer last drew for key.
    def changed(self, key, value):
        if self.sig.get(key) == value:
            return False
        self.sig[key] = value
        return True


# Copy rectangles of the pre-rendered background back over a frame. Each one is a
# FrameBuffer.blit from a (buffer, width, height, format, stride) view into the background,
# or a blit_rect when it spans whole rows; both copy in C, while slicing the rows in Python
# is far slower on a board.
# Rectangles are (x, y, w, h) and are clipped to the w x h frame.
def restore_rects(fb, src, rects, w, h):
    view = memoryview(src)
    seen = set()
    for rect in rects:
        if rect in seen:
            continue
        seen.add(rect)
        x, y, rw, rh = rect
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(w, x + rw)
        y1 = min(h, y + rh)
        if x1 <= x0 or y1 <= y0:
            continue
        if x0 == 0 and x1 == w:
            # Whole rows are one contiguous run of the background.
            fb.blit_rect(view[y0 * w * 2 : y1 * w * 2], 0, y0, w, y1 - y0)
        else:
            fb.blit((view[(y0 * w + x0) * 2 :], x1 - x0, y1 - y0, RGB565, w), x0, y0)
