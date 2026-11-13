# SPDX-FileCopyrightText: 2026 Brad Barnett
#
# SPDX-License-Identifier: MIT

# deps: pygraphics
# gallery: no-pyodide
"""Draw SVG icons and a gauge at the size the screen needs.

Four icons are drawn in their own colours, blended over the background so
their edges stay smooth, then again as one-colour masks tinted with
``FrameBuffer.blit_alpha``. Below them a gauge with gradients fills the rest
of the screen. Every picture comes from SVG text in this file, drawn by
``svgio`` at a size worked out from the display, so the same file looks
right on a small panel and a large one.

Needs: a display, and svgio: on MicroPython, a firmware built with it
(``--modules all``); on CPython, pydevices-desktop's ``svgio`` and
``pip install resvg-py pillow``.

Run it:

    mpremote run svg_icons.py

Tested on: MicroPython in a browser (the WebAssembly port), an ESP32-S3 with an
800x480 RGB panel, and CPython on Linux with SDL2.
"""

from board_config import display_drv
from displaydev import color565
import pygraphics
import svgio

# Change these to match your setup.
BACKGROUND = color565(0xEC, 0xEF, 0xF1)
TINT = color565(0x37, 0x47, 0x4F)
MARGIN = 8

ICONS = (
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#1e88e5"'
    b' stroke-width="2" stroke-linecap="round"><path d="M2 8.8a15 15 0 0 1 20 0"/>'
    b'<path d="M5 12.6a10 10 0 0 1 14 0"/><path d="M8.5 16.4a5 5 0 0 1 7 0"/>'
    b'<circle cx="12" cy="20" r="1" fill="#1e88e5"/></svg>',
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">'
    b'<rect x="2" y="7" width="18" height="10" rx="2" fill="none" stroke="#424242" stroke-width="2"/>'
    b'<rect x="21" y="10" width="2" height="4" rx="1" fill="#424242"/>'
    b'<rect x="4" y="9" width="10" height="6" rx="1" fill="#43a047"/></svg>',
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><polygon fill="#6d4c41"'
    b' points="12,3 2,12 5,12 5,21 10,21 10,15 14,15 14,21 19,21 19,12 22,12"/></svg>',
    b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path fill="#fb8c00"'
    b' fill-rule="evenodd" d="M10.3 2h3.4l.5 2.6a8 8 0 0 1 2 1.2l2.5-.9 1.7 2.9-2 1.7a8 8 0 0 1'
    b' 0 2.4l2 1.7-1.7 2.9-2.5-.9a8 8 0 0 1-2 1.2l-.5 2.6h-3.4l-.5-2.6a8 8 0 0 1-2-1.2l-2.5.9'
    b'-1.7-2.9 2-1.7a8 8 0 0 1 0-2.4l-2-1.7 1.7-2.9 2.5.9a8 8 0 0 1 2-1.2zM12 8.5a3.5 3.5 0 1 0'
    b' 0 7 3.5 3.5 0 1 0 0-7z"/></svg>',
)

GAUGE = b"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 120">
<defs>
<linearGradient id="band" x1="0" y1="0" x2="1" y2="0">
<stop offset="0" stop-color="#43a047"/><stop offset="0.6" stop-color="#fdd835"/>
<stop offset="1" stop-color="#e53935"/></linearGradient>
<radialGradient id="hub" cx="0.5" cy="0.5" r="0.5">
<stop offset="0" stop-color="#eceff1"/><stop offset="1" stop-color="#607d8b"/></radialGradient>
</defs>
<rect width="200" height="120" rx="10" fill="#263238"/>
<path d="M25 105 A75 75 0 0 1 175 105" fill="none" stroke="url(#band)" stroke-width="12"/>
<path d="M40 105h8 M152 105h8 M100 40v8 M54 59l6 6 M146 59l-6 6" stroke="#eceff1" stroke-width="2"/>
<path d="M100 105 L145 66" stroke="#ff7043" stroke-width="4" stroke-linecap="round"/>
<circle cx="100" cy="105" r="9" fill="url(#hub)"/>
</svg>"""


def blended(decoder, svg, size):
    """An SVG drawn over the background, as an RGB565 buffer and its size."""
    w, h = decoder.open(svg, width=size)
    canvas = pygraphics.FrameBuffer(bytearray(w * h * 2), w, h, pygraphics.RGB565)
    canvas.fill(BACKGROUND)
    decoder.decode(canvas.buffer)
    return canvas.buffer, w, h


def main():
    width, height = display_drv.width, display_drv.height
    pygraphics.fill(display_drv, BACKGROUND)
    decoder = svgio.SvgDecoder()

    # Two rows of icons across the top, sized so four fit with margins.
    size = min((width - 5 * MARGIN) // 4, height // 6)
    for i, svg in enumerate(ICONS):
        x = MARGIN + i * (size + MARGIN)

        # In their own colours, blended over the background.
        buf, w, h = blended(decoder, svg, size)
        pygraphics.blit_rect(display_drv, buf, x, MARGIN, w, h)

        # As a mask, tinted with one colour over a background tile.
        w, h = decoder.open(svg, width=size)
        mask = bytearray(w * h)
        decoder.decode(None, mask)
        tile = pygraphics.FrameBuffer(bytearray(w * h * 2), w, h, pygraphics.RGB565)
        tile.fill(BACKGROUND)
        tile.blit_alpha(mask, 0, 0, w, h, TINT)
        pygraphics.blit_rect(display_drv, tile.buffer, x, 2 * MARGIN + size, w, h)

    # The gauge fills what's left, keeping its shape.
    top = 3 * MARGIN + 2 * size
    room_w, room_h = width - 2 * MARGIN, height - top - MARGIN
    gauge_w = min(room_w, room_h * 200 // 120)
    buf, w, h = blended(decoder, GAUGE, gauge_w)
    pygraphics.blit_rect(display_drv, buf, (width - w) // 2, top, w, h)


main()
display_drv.show()
