# SPDX-FileCopyrightText: 2026 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""A neon ring gauge: the two big dials of the cluster.

The ring is drawn once, as vector art (see ``art.py``): a dim track, the full
colour sweep of the gauge as stroked arcs whose gradients run on from one stop
to the next, a soft radial bloom inside it, a tick ring outside it and a
faint inner ring. The live value then needs only cheap moves each frame:

* a *cover* arc, the colour of the empty track, hides the sweep beyond the
  value, so the sweep appears to grow and shrink;
* a wide, blurred arc under the art glows along the lit part;
* a bright cap sits on the leading edge.

The arcs are used for what they are cheap at (an angle that changes every
frame) and the vector picture for what the arc widget can't do (a colour
gradient along the sweep, and radial gradients).
"""

import math

import lvgl as lv

from art import Picture, face_svg, ring_svg

_CIRCLE = getattr(lv, "RADIUS_CIRCLE", 0x7FFF)


def _color(rgb):
    return lv.color_hex(rgb)


def _mix(a, b, t):
    """Blend two 0xRRGGBB colours; ``t`` from 0 (a) to 1 (b)."""
    r = int(((a >> 16) & 0xFF) * (1 - t) + ((b >> 16) & 0xFF) * t)
    g = int(((a >> 8) & 0xFF) * (1 - t) + ((b >> 8) & 0xFF) * t)
    bl = int((a & 0xFF) * (1 - t) + (b & 0xFF) * t)
    return (r << 16) | (g << 8) | bl


def gradient_at(stops, t):
    """Colour at ``t`` (0..1) along a list of ``(position, 0xRRGGBB)`` stops."""
    if t <= stops[0][0]:
        return stops[0][1]
    for i in range(1, len(stops)):
        pos, col = stops[i]
        if t <= pos:
            p0, c0 = stops[i - 1]
            span = pos - p0
            return _mix(c0, col, (t - p0) / span if span > 0 else 1.0)
    return stops[-1][1]


def plain(obj):
    """An object that is only there to be looked at."""
    obj.set_style_pad_all(0, 0)
    obj.set_style_border_width(0, 0)
    obj.set_style_outline_width(0, 0)
    obj.set_style_bg_opa(lv.OPA.TRANSP, 0)
    obj.remove_flag(lv.obj.FLAG.CLICKABLE)
    obj.remove_flag(lv.obj.FLAG.SCROLLABLE)


def scaled_font(label, target_px):
    """The largest built-in Montserrat at or below ``target_px``, scaled up to it."""
    chosen = None
    for points in (48, 40, 32, 24, 16, 14):
        font = getattr(lv, "font_montserrat_%d" % points, None)
        if font is not None:
            chosen = (font, points)
            if points <= target_px:
                break
    if chosen is None:
        return
    font, points = chosen
    label.set_style_text_font(font, 0)
    scale = max(128, min(768, round(256 * target_px / points)))
    if scale != 256:
        label.set_style_transform_scale(scale, 0)


class Ring:
    """One dial. ``stops`` colours the sweep, ``vmax`` is the full-scale value."""

    def __init__(
        self,
        parent,
        size,
        stops,
        vmax,
        *,
        track=0x0E1E33,
        bg=0x05080F,
        glow=None,
        start=135,
        sweep=270,
        unit="",
        caption="",
        minor=None,
        major=None,
    ):
        self.size = size
        self.stops = stops
        self.vmax = float(vmax)
        self.start = start
        self.sweep = sweep
        self.value = 0.0
        self._shown = None
        self._glow_rgb = glow if glow is not None else stops[-1][1]

        self.width = max(10, size // 15)  # the sweep's thickness
        self.radius = size // 2 - max(12, size // 11)  # centre line of the sweep
        cx = cy = size // 2
        self.cx, self.cy = cx, cy

        self.obj = lv.obj(parent)
        self.obj.set_size(size, size)
        plain(self.obj)

        # Glow first, so everything else draws over it.
        self.glow = lv.arc(self.obj)
        self.glow.set_size(size, size)
        self.glow.center()
        self.glow.set_bg_angles(start, start + sweep)
        self.glow.set_range(0, 1000)
        self.glow.set_value(0)
        self.glow.remove_style(None, lv.PART.KNOB)
        plain(self.glow)
        pad = size // 2 - self.radius - self.width // 2
        self.glow.set_style_pad_all(pad, 0)
        self.glow.set_style_arc_opa(lv.OPA.TRANSP, lv.PART.MAIN)
        self.glow.set_style_arc_width(self.width + 16, lv.PART.INDICATOR)
        self.glow.set_style_arc_color(_color(self._glow_rgb), lv.PART.INDICATOR)
        self.glow.set_style_arc_opa(150, lv.PART.INDICATOR)
        self.glow.set_style_arc_rounded(True, lv.PART.INDICATOR)
        if hasattr(self.glow, "set_style_blur_radius"):
            self.glow.set_style_blur_radius(max(6, size // 22), 0)

        # The art: track, bloom, colour sweep, ticks, hairline, as one vector
        # picture drawn once. Ticks sit at round values: one every ``minor``
        # units, a longer one every ``major``. Left unset, the dial gets ten
        # major divisions.
        if minor is None:
            minor = self.vmax / 50.0
        if major is None:
            major = self.vmax / 10.0
        self.art = Picture(
            self.obj,
            ring_svg(size, stops, gradient_at, track, start, sweep, self.width, self.radius, (minor, major, self.vmax)),
            size,
            size,
        )

        # The cover: the empty part of the track, painted over the sweep.
        self.cover = lv.arc(self.obj)
        self.cover.set_size(size, size)
        self.cover.center()
        self.cover.set_bg_angles(start, start + sweep)
        self.cover.set_range(0, 1000)
        self.cover.set_value(0)
        self.cover.remove_style(None, lv.PART.KNOB)
        plain(self.cover)
        self.cover.set_style_pad_all(pad, 0)
        self.cover.set_style_arc_width(self.width + 2, lv.PART.MAIN)
        self.cover.set_style_arc_color(_color(track), lv.PART.MAIN)
        self.cover.set_style_arc_opa(lv.OPA.COVER, lv.PART.MAIN)
        self.cover.set_style_arc_rounded(False, lv.PART.MAIN)
        self.cover.set_style_arc_opa(lv.OPA.TRANSP, lv.PART.INDICATOR)

        # The dial face inside the sweep.
        face = size - 2 * (size // 2 - self.radius) - self.width - max(10, size // 14)
        self.face = lv.obj(self.obj)
        self.face.set_size(face, face)
        self.face.center()
        plain(self.face)
        self.face.set_style_radius(_CIRCLE, 0)
        self.face.set_style_bg_opa(lv.OPA.TRANSP, 0)
        self.face_art = Picture(self.face, face_svg(face, self.stops[0][1], 0x16264F, bg), face, face)

        # The cap on the leading edge of the sweep.
        cap = self.width + 6
        self.cap = lv.obj(self.obj)
        self.cap.set_size(cap, cap)
        plain(self.cap)
        self.cap.set_style_radius(_CIRCLE, 0)
        self.cap.set_style_bg_color(_color(0xFFFFFF), 0)
        self.cap.set_style_bg_opa(lv.OPA.COVER, 0)
        self.cap.set_style_shadow_color(_color(self._glow_rgb), 0)
        self.cap.set_style_shadow_width(cap * 2, 0)
        self.cap.set_style_shadow_spread(2, 0)
        self.cap.set_style_shadow_opa(220, 0)

        # The reading.
        self.unit = lv.label(self.face)
        self.unit.set_text(unit)
        self.unit.set_style_text_color(_color(0x7F93B5), 0)
        self.unit.set_style_text_font(lv.font_montserrat_14, 0)
        self.unit.align(lv.ALIGN.CENTER, 0, -face * 36 // 100)

        px = max(24, face * 44 // 100)
        self.number = lv.label(self.face)
        self.number.set_text("0")
        self.number.set_width(face)
        self.number.set_style_text_align(lv.TEXT_ALIGN.CENTER, 0)
        self.number.set_style_text_color(_color(0xFFFFFF), 0)
        self.number.set_style_text_letter_space(2, 0)
        scaled_font(self.number, px)
        self.number.set_style_transform_pivot_x(face // 2, 0)
        self.number.set_style_transform_pivot_y(px // 2, 0)
        self.number.align(lv.ALIGN.CENTER, 0, 0)

        self.caption = lv.label(self.obj)
        self.caption.set_text(caption)
        self.caption.set_style_text_color(_color(0xB8C4DC), 0)
        self.caption.set_style_text_font(lv.font_montserrat_16, 0)
        self.caption.align(lv.ALIGN.BOTTOM_MID, 0, -max(2, size // 40))

        self.set_value(0)

    # -- live ---------------------------------------------------------------

    def set_value(self, v):
        v = max(0.0, min(self.vmax, float(v)))
        self.value = v
        frac = v / self.vmax
        a_val = self.start + self.sweep * frac
        if frac >= 0.999:
            self.cover.add_flag(lv.obj.FLAG.HIDDEN)
        else:
            self.cover.remove_flag(lv.obj.FLAG.HIDDEN)
            self.cover.set_bg_angles(a_val, self.start + self.sweep)
        self.glow.set_value(int(1000 * frac))
        self.glow.set_style_arc_color(_color(gradient_at(self.stops, frac)), lv.PART.INDICATOR)
        a = math.radians(a_val)
        cap = self.cap.get_width() or (self.width + 6)
        self.cap.set_pos(
            int(self.cx + math.cos(a) * self.radius - cap / 2),
            int(self.cy + math.sin(a) * self.radius - cap / 2),
        )
        self.cap.set_style_shadow_color(_color(gradient_at(self.stops, frac)), 0)
        shown = int(v + 0.5)
        if shown != self._shown:
            self._shown = shown
            self.number.set_text("%d" % shown)

    def set_caption(self, text):
        self.caption.set_text(text)

    def set_pos(self, x, y):
        self.obj.set_pos(x, y)
