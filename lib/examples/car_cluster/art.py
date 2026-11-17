# SPDX-FileCopyrightText: 2026 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""Vector art for the cluster, drawn once by svgio and shown as LVGL images.

LVGL's own radial gradients are off in the stock build, and its canvas draws
only flat arcs and lines. svgio reads SVG, so each piece of art here is a
small SVG document: gradient strokes that follow the dials' sweep, radial
gradients for the dial faces and their bloom, and smooth curves for the dash
hood. Each is drawn into one RGB565A8 buffer when the screen is built and
never again, so a frame costs LVGL one image blend and nothing more.
"""

import math

import lvgl as lv
import svgio

_HEAD = '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">'


def hexcolor(rgb):
    """``#rrggbb`` for a 0xRRGGBB colour."""
    return "#%06x" % rgb


class Picture:
    """An SVG drawn into an RGB565A8 buffer, and the LVGL image that shows it."""

    def __init__(self, parent, svg, width, height):
        decoder = svgio.SvgDecoder()
        w, h = decoder.open(svg.encode(), width=width)
        if (w, h) != (width, height):
            raise ValueError("art drew at %dx%d, not %dx%d" % (w, h, width, height))
        self._data = bytearray(w * h * 3)
        planes = memoryview(self._data)
        decoder.decode(planes[: w * h * 2], planes[w * h * 2 :])
        decoder.close()

        dsc = lv.image_dsc_t()
        dsc.header.magic = lv.IMAGE_HEADER_MAGIC
        dsc.header.cf = lv.COLOR_FORMAT.RGB565A8
        dsc.header.w = w
        dsc.header.h = h
        dsc.header.stride = w * 2
        dsc.data_size = w * h * 3
        dsc.data = self._data
        self._dsc = dsc

        self.image = lv.image(parent)
        self.image.set_src(dsc)
        self.image.set_size(w, h)
        self.image.set_pos(0, 0)
        self.image.remove_flag(lv.obj.FLAG.CLICKABLE)
        self.image.remove_flag(lv.obj.FLAG.SCROLLABLE)


def ring_svg(size, stops, gradient_at, track, start, sweep, width, radius, ticks):
    """The dial's art: track, colour sweep, bloom, hairline and tick ring.

    ``ticks`` is ``(minor, major, vmax)``. ``gradient_at(stops, t)`` gives the
    colour a fraction of the way along the sweep.
    """
    c = size / 2.0
    out = [_HEAD % (size, size, size, size), "<defs>"]

    # Each stretch of the sweep is a stroked arc with its own gradient from
    # its first point to its last, so the colour runs on without a step.
    parts = max(12, sweep // 20)
    arcs = []
    for i in range(parts):
        t0 = i / parts
        t1 = (i + 1) / parts
        a0 = math.radians(start + sweep * t0)
        # The stretches overlap by half a degree, except at the sweep's end.
        a1 = math.radians(start + sweep * t1 + (0.5 if i < parts - 1 else 0))
        x0, y0 = c + radius * math.cos(a0), c + radius * math.sin(a0)
        x1, y1 = c + radius * math.cos(a1), c + radius * math.sin(a1)
        out.append(
            '<linearGradient id="s%d" gradientUnits="userSpaceOnUse" x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f">'
            '<stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>'
            % (i, x0, y0, x1, y1, hexcolor(gradient_at(stops, t0)), hexcolor(gradient_at(stops, t1)))
        )
        arcs.append('<path d="M%.2f %.2fA%d %d 0 0 1 %.2f %.2f" stroke="url(#s%d)"/>' % (x0, y0, radius, radius, x1, y1, i))

    # A glow just inside the sweep that fades to nothing toward the middle.
    inner = radius - width // 2
    glow = hexcolor(stops[len(stops) // 2][1])
    out.append(
        '<radialGradient id="bloom" gradientUnits="userSpaceOnUse" cx="%.1f" cy="%.1f" r="%d">'
        '<stop offset="0.55" stop-color="%s" stop-opacity="0"/>'
        '<stop offset="%.3f" stop-color="%s" stop-opacity="0.16"/>'
        '<stop offset="1" stop-color="%s" stop-opacity="0"/></radialGradient>'
        % (c, c, inner, glow, 0.93, glow, glow)
    )
    out.append("</defs>")

    # The bloom, then the dim track under the sweep.
    out.append('<circle cx="%.1f" cy="%.1f" r="%d" fill="url(#bloom)"/>' % (c, c, inner))
    a0 = math.radians(start)
    a1 = math.radians(start + sweep)
    out.append(
        '<path d="M%.2f %.2fA%d %d 0 1 1 %.2f %.2f" fill="none" stroke="%s" stroke-width="%d"/>'
        % (
            c + radius * math.cos(a0),
            c + radius * math.sin(a0),
            radius,
            radius,
            c + radius * math.cos(a1),
            c + radius * math.sin(a1),
            hexcolor(track),
            width + 2,
        )
    )
    out.append('<g fill="none" stroke-width="%d">' % width)
    out.extend(arcs)
    out.append("</g>")

    # A hairline on the inside edge of the sweep.
    hr = radius - width // 2 - 1
    out.append(
        '<path d="M%.2f %.2fA%d %d 0 1 1 %.2f %.2f" fill="none" stroke="#ffffff" stroke-opacity="0.24" stroke-width="1"/>'
        % (c + hr * math.cos(a0), c + hr * math.sin(a0), hr, hr, c + hr * math.cos(a1), c + hr * math.sin(a1))
    )

    # The tick ring outside the sweep, each tick in the sweep's colour there.
    minor, major, vmax = ticks
    count = int(round(vmax / minor))
    per_major = max(1, int(round(major / minor)))
    r_out = size / 2.0 - 2
    for i in range(count + 1):
        t = i / count
        a = math.radians(start + sweep * t)
        is_major = i % per_major == 0
        length = max(8, size // 24) if is_major else max(4, size // 48)
        out.append(
            '<line x1="%.2f" y1="%.2f" x2="%.2f" y2="%.2f" stroke="%s" stroke-opacity="%.2f" stroke-width="%d" stroke-linecap="round"/>'
            % (
                c + math.cos(a) * r_out,
                c + math.sin(a) * r_out,
                c + math.cos(a) * (r_out - length),
                c + math.sin(a) * (r_out - length),
                hexcolor(gradient_at(stops, t)),
                0.9 if is_major else 0.43,
                3 if is_major else 2,
            )
        )
    out.append("</svg>")
    return "".join(out)


def face_svg(size, rim, lit, dark):
    """A dial face: a radial gradient lit from the upper left, and a thin rim."""
    c = size / 2.0
    return (
        _HEAD % (size, size, size, size)
        + '<defs><radialGradient id="f" cx="0.38" cy="0.3" r="0.85">'
        '<stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></radialGradient></defs>'
        '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="url(#f)" stroke="%s" stroke-opacity="0.24" stroke-width="1"/></svg>'
        % (hexcolor(lit), hexcolor(dark), c, c, c - 1, hexcolor(rim))
    )


def hood_svg(w, h, curves, color):
    """Faint curves like a dash hood: smooth quadratic arcs fading out toward the sides.

    Each curve is ``(crest_y, drop, opa, width)``: highest at the centre, and
    ``drop`` pixels lower at the edges. The opacity sits in the gradient's
    stops, which every svgio draws the same way.
    """
    out = [_HEAD % (w, h, w, h), "<defs>"]
    paths = []
    for i, (crest, drop, opa, width) in enumerate(curves):
        peak = min(1.0, opa / 255.0 * 3.2)
        out.append(
            '<linearGradient id="h%d" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="%d" y2="0">'
            '<stop offset="0" stop-color="%s" stop-opacity="%.3f"/>'
            '<stop offset="0.5" stop-color="%s" stop-opacity="%.3f"/>'
            '<stop offset="1" stop-color="%s" stop-opacity="%.3f"/></linearGradient>'
            % (i, w, color, peak * 0.5, color, peak, color, peak * 0.5)
        )
        paths.append(
            '<path d="M0 %.1fQ%.1f %.1f %d %.1f" fill="none" stroke="url(#h%d)" stroke-width="%d"/>'
            % (crest + drop, w / 2.0, crest - drop, w, crest + drop, i, width)
        )
    out.append("</defs>")
    out.extend(paths)
    out.append("</svg>")
    return "".join(out)
