# SPDX-FileCopyrightText: 2026 Brad Barnett
#
# SPDX-License-Identifier: MIT

# deps: pygraphics
"""Draw the OmniPython mark at the size the screen needs.

The mark is Huey the chameleon's head above the name. Its shapes are kept
once, as circles and SVG paths, and drawn one of two ways. With ``svgio``
they become an SVG document that svgio draws with smooth edges. Without it,
the same paths are flattened to polygons and filled with pygraphics, so the
mark still appears on firmware that has no SVG renderer. The name is drawn
letter shapes, not a font; only the polygon method on a very small screen
writes it in the built-in font, where letter shapes would fill in. The mark
is centred, except on a square screen: that may be a round one, whose edge
would cut off the ends of the name, so the mark sits higher there.

Needs: a display. svgio is optional and picks the method: on MicroPython it
is in firmware built with ``--modules all``; on CPython it comes with
omnipython-desktop (``pip install resvg-py pillow``). Both methods are part
of the example, and the printed line says which one ran.

Run it:

    mpremote run logo.py

You should see the blue head with its lime jaw in the middle of a navy
screen, "OmniPython" under it in lime and white, and one line printed with
the size it drew and the method.

Tested on: MicroPython on an ESP32-P4 with a 160x128 ST7735 (svgio),
CircuitPython 11 on an ESP32-S3 with an 800x480 RGB panel (polygons),
MicroPython in a browser (svgio), Pyodide in a browser (polygons), and
CPython on Linux with SDL2 (svgio).
"""

from array import array

from board_config import display_drv
from displaydev import color565
import pygraphics

try:
    import svgio
except ImportError:
    svgio = None

# Change these to match your setup.
SHOW_NAME = True  # False draws the head alone
SMALLEST_LETTERS = 12  # pixels; polygons can't draw letters shorter than this
GROUND = 0x0B2A4A
FILL = 90  # per cent of the screen the mark may take
LIFT = 10  # per cent of a square screen's height to move the mark up

# The head, back to front. Each row is a colour, a line width (0 fills the
# shape) and the shape: a circle's centre and radius, or an SVG path.
HEAD = (
    (0x2767AC, 0, (150, -190, 28)),
    (0x3F8FD6, 0, (150.76, -189.92, 24.08)),
    (0x7DBBF0, 0, (151.76, -189.83, 19.6)),
    (0x1A4A80, 0, (152.52, -189.76, 17.64)),
    (0xFFFFFF, 0, (152.52, -189.76, 15.68)),
    (0x0B2A4A, 0, (154.64, -189.54, 9.72)),
    (0xFFFFFF, 0, (151.14, -193.43, 2.92)),
    (
        0x3F8FD6, 0,
        "M52 -112C46.33 -123 41 -143 42 -160C43 -177 50.67 -200.67 58 -214C65.33 -227.33 76 "
        "-238.67 86 -240C96 -241.33 106.33 -232.33 118 -222C129.67 -211.67 145 -191 156 -178C167 "
        "-165 180.33 -154.33 184 -144C187.67 -133.67 187.33 -124.67 178 -116C168.67 -107.33 145 "
        "-95.67 128 -92C111 -88.33 88.67 -90.67 76 -94C63.33 -97.33 57.67 -101 52 -112Z"
    ),
    (
        0x2767AC, 0,
        "M50 -124C46.67 -130.67 40.67 -147 42 -162C43.33 -177 50.67 -201 58 -214C65.33 -227 83.33 "
        "-241.33 86 -240C88.67 -238.67 77.67 -219.33 74 -206C70.33 -192.67 66 -174 64 -160C62 -146 "
        "64.33 -128 62 -122C59.67 -116 53.33 -117.33 50 -124Z"
    ),
    (
        0xC4DC4C, 0,
        "M90 -116C98.67 -118.67 119 -109 134 -111C149 -113 172 -126.83 180 -128C188 -129.17 183.67 "
        "-122 182 -118C180.33 -114 179 -108.5 170 -104C161 -99.5 142.67 -92.5 128 -91C113.33 -89.5 "
        "88.33 -90.83 82 -95C75.67 -99.17 81.33 -113.33 90 -116Z"
    ),
    (0x7DBBF0, 5, "M90 -232Q104 -220 112 -204"),
    (0x1A4A80, 4.5, "M181 -130Q138 -106 92 -119Q84 -122 84 -131"),
    (0x1A4A80, 0, (170, -148, 2.6)),
    (0x2767AC, 0, (110, -164, 39)),
    (0x3F8FD6, 0, (111.05, -163.88, 33.54)),
    (0x7DBBF0, 0, (112.46, -163.77, 27.3)),
    (0x1A4A80, 0, (113.51, -163.67, 24.57)),
    (0xFFFFFF, 0, (113.51, -163.67, 21.84)),
    (0x0B2A4A, 0, (116.46, -163.36, 13.54)),
    (0xFFFFFF, 0, (111.58, -168.78, 4.06)),
)

# "OmniPython" in two colours. Each row is where the word starts, its
# colour, and its letters as one SVG path in the font's own units.
NAME = (
    (
        6, 0xC4DC4C,
        "M398 -11Q294 -11 215 35Q137 80 93 162Q50 244 50 353Q50 436 75 502Q99 569 145 617Q191 664 "
        "256 690Q320 716 398 716Q504 716 582 671Q660 626 703 545Q747 463 747 354Q747 271 722 "
        "204Q697 137 651 89Q605 41 541 15Q477 -11 398 -11ZM398 121Q457 121 499 149Q540 176 563 "
        "228Q585 281 585 353Q585 463 536 523Q487 584 398 584Q340 584 298 557Q256 530 234 478Q212 "
        "426 212 353Q212 244 261 182Q310 121 398 121ZM932 -9Q895 -9 876 11Q856 31 856 68V423Q856 "
        "460 876 480Q895 499 930 499Q966 499 985 480Q1004 460 1004 423V359L993 399Q1013 445 1055 "
        "473Q1097 501 1154 501Q1211 501 1249 474Q1287 447 1303 391H1289Q1311 442 1357 472Q1402 501 "
        "1461 501Q1518 501 1554 479Q1591 456 1609 410Q1627 365 1627 295V68Q1627 31 1608 11Q1588 -9 "
        "1552 -9Q1515 -9 1496 11Q1476 31 1476 68V290Q1476 339 1461 362Q1445 384 1408 384Q1365 384 "
        "1341 354Q1317 324 1317 269V68Q1317 31 1298 11Q1278 -9 1242 -9Q1206 -9 1186 11Q1166 31 "
        "1166 68V290Q1166 339 1150 362Q1135 384 1098 384Q1055 384 1031 354Q1007 324 1007 "
        "269V68Q1007 -9 932 -9ZM1819 -9Q1782 -9 1763 11Q1743 31 1743 68V423Q1743 460 1763 480Q1782 "
        "499 1817 499Q1853 499 1872 480Q1891 460 1891 423V366L1880 399Q1903 448 1948 475Q1994 501 "
        "2052 501Q2111 501 2149 479Q2187 456 2206 410Q2225 365 2225 295V68Q2225 31 2205 11Q2186 -9 "
        "2149 -9Q2113 -9 2093 11Q2074 31 2074 68V288Q2074 339 2055 362Q2037 384 1999 384Q1951 384 "
        "1923 354Q1894 324 1894 274V68Q1894 -9 1819 -9ZM2414 -8Q2377 -8 2358 14Q2338 35 2338 "
        "74V416Q2338 456 2358 477Q2377 499 2414 499Q2450 499 2470 477Q2489 456 2489 416V74Q2489 35 "
        "2470 14Q2451 -8 2414 -8ZM2414 581Q2372 581 2350 600Q2327 620 2327 656Q2327 693 2350 "
        "712Q2372 732 2414 732Q2456 732 2478 712Q2500 693 2500 656Q2500 620 2478 600Q2456 581 2414 "
        "581Z"
    ),
    (
        147.36, 0xE8F0F8,
        "M149 -9Q111 -9 91 12Q71 33 71 71V626Q71 665 91 685Q112 705 150 705H393Q511 705 575 "
        "645Q639 586 639 480Q639 374 575 314Q511 254 393 254H226V71Q226 33 207 12Q187 -9 149 "
        "-9ZM226 374H367Q427 374 459 401Q490 428 490 480Q490 532 459 558Q427 584 367 584H226ZM848 "
        "-189Q822 -189 805 -175Q788 -161 785 -139Q782 -116 793 -91L860 57V-5L683 401Q673 427 676 "
        "450Q680 472 699 486Q717 499 750 499Q777 499 794 487Q810 474 824 439L942 139H910L1032 "
        "440Q1046 474 1063 486Q1081 499 1111 499Q1137 499 1152 486Q1168 472 1171 450Q1175 428 1163 "
        "402L928 -131Q913 -165 894 -177Q876 -189 848 -189ZM1480 -11Q1411 -11 1364 12Q1318 35 1296 "
        "79Q1273 123 1273 190V378H1231Q1203 378 1187 393Q1172 408 1172 434Q1172 462 1187 476Q1203 "
        "491 1231 491H1273V567Q1273 605 1293 624Q1313 644 1349 644Q1386 644 1405 624Q1424 605 1424 "
        "567V491H1519Q1547 491 1562 476Q1577 462 1577 434Q1577 408 1562 393Q1547 378 1519 "
        "378H1424V196Q1424 154 1444 133Q1463 112 1506 112Q1521 112 1534 115Q1547 118 1558 119Q1572 "
        "120 1581 110Q1590 101 1590 69Q1590 45 1582 27Q1574 9 1554 1Q1541 -4 1518 -7Q1496 -11 1480 "
        "-11ZM1719 -9Q1682 -9 1663 11Q1643 31 1643 68V637Q1643 675 1663 694Q1682 714 1719 714Q1755 "
        "714 1775 694Q1794 675 1794 637V399H1780Q1803 448 1848 475Q1894 501 1952 501Q2011 501 2049 "
        "479Q2087 456 2106 410Q2125 365 2125 295V68Q2125 31 2105 11Q2086 -9 2049 -9Q2013 -9 1993 "
        "11Q1974 31 1974 68V288Q1974 339 1955 362Q1937 384 1899 384Q1851 384 1823 354Q1794 324 "
        "1794 274V68Q1794 -9 1719 -9ZM2474 -11Q2395 -11 2337 20Q2278 51 2246 109Q2214 167 2214 "
        "246Q2214 305 2232 352Q2250 399 2285 433Q2319 466 2367 484Q2415 501 2474 501Q2553 501 2612 "
        "470Q2670 439 2703 382Q2735 325 2735 246Q2735 186 2717 139Q2698 92 2664 58Q2630 24 2581 "
        "7Q2533 -11 2474 -11ZM2474 102Q2507 102 2531 118Q2555 134 2569 165Q2583 197 2583 246Q2583 "
        "319 2553 354Q2523 388 2474 388Q2442 388 2418 373Q2393 358 2379 326Q2366 295 2366 246Q2366 "
        "173 2396 138Q2426 102 2474 102ZM2903 -9Q2866 -9 2847 11Q2827 31 2827 68V423Q2827 460 2847 "
        "480Q2866 499 2901 499Q2937 499 2956 480Q2975 460 2975 423V366L2964 399Q2987 448 3032 "
        "475Q3078 501 3136 501Q3195 501 3233 479Q3271 456 3290 410Q3309 365 3309 295V68Q3309 31 "
        "3289 11Q3270 -9 3233 -9Q3197 -9 3177 11Q3158 31 3158 68V288Q3158 339 3139 362Q3121 384 "
        "3083 384Q3035 384 3007 354Q2978 324 2978 274V68Q2978 -9 2903 -9Z"
    ),
)
NAME_SCALE = 0.05548  # font units to the mark's units
BASELINE = 262
CAPITAL = 705  # the height of a capital letter, in font units


def screen_colour(colour):
    """A 0xRRGGBB colour as the display wants it."""
    return color565(colour >> 16, (colour >> 8) & 255, colour & 255)


def svg_group(shapes, scale_x, scale_y, move_x, move_y):
    """The shapes as SVG text, scaled and then moved into the mark's box."""
    parts = ['<g transform="translate(%s %s) scale(%s %s)">' % (move_x, move_y, scale_x, scale_y)]
    for colour, line, shape in shapes:
        if line:
            paint = 'fill="none" stroke="#%06x" stroke-width="%s" stroke-linecap="round"' % (colour, line)
        else:
            paint = 'fill="#%06x"' % colour
        if isinstance(shape, tuple):
            parts.append('<circle cx="%s" cy="%s" r="%s" %s/>' % (shape[0], shape[1], shape[2], paint))
        else:
            parts.append('<path d="%s" %s/>' % (shape, paint))
    parts.append("</g>")
    return "".join(parts)


def path_steps(path):
    """Each step of an SVG path: its letter and the numbers after it."""
    for letter in "MLHVQCZ":
        path = path.replace(letter, " %s " % letter)
    letter, numbers = None, []
    for word in path.replace("-", " -").split():
        if word in "MLHVQCZ":
            if letter:
                yield letter, numbers
            letter, numbers = word, []
        else:
            numbers.append(float(word))
    yield letter, numbers


def path_outlines(path, chord):
    """The path's outlines as lists of points, its curves cut into pieces about *chord* long."""
    outlines = []
    x = y = 0
    for letter, n in path_steps(path):
        if letter == "M":
            x, y = n
            points = [(x, y)]
            outlines.append(points)
        elif letter in "LHV":
            x, y = (n[0], y) if letter == "H" else (x, n[0]) if letter == "V" else n
            points.append((x, y))
        elif letter in "QC":
            if letter == "Q":
                # A curve with one pull point is the same curve with two.
                x1, y1 = x + (n[0] - x) * 2 / 3, y + (n[1] - y) * 2 / 3
                x3, y3 = n[2], n[3]
                x2, y2 = x3 + (n[0] - x3) * 2 / 3, y3 + (n[1] - y3) * 2 / 3
            else:
                x1, y1, x2, y2, x3, y3 = n
            reach = abs(x1 - x) + abs(y1 - y) + abs(x2 - x1) + abs(y2 - y1) + abs(x3 - x2) + abs(y3 - y2)
            pieces = max(2, int(reach / chord))
            for piece in range(1, pieces + 1):
                t = piece / pieces
                u = 1 - t
                a, b, c, d = u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t
                points.append((a * x + b * x1 + c * x2 + d * x3, a * y + b * y1 + c * y2 + d * y3))
            x, y = x3, y3
    return outlines


def turns(points):
    """Positive or negative by which way round an outline runs: a letter's holes run against it."""
    total = 0
    for i in range(len(points)):
        total += points[i - 1][0] * points[i][1] - points[i][0] * points[i - 1][1]
    return total


def draw_polygons(shapes, scale_x, scale_y, move_x, move_y):
    """Fill the shapes on the display with pygraphics polygons and circles."""
    size = abs(scale_x)
    for colour, line, shape in shapes:
        colour = screen_colour(colour)
        if isinstance(shape, tuple):
            pygraphics.circle(display_drv, round(move_x + shape[0] * scale_x), round(move_y + shape[1] * scale_y), max(1, round(shape[2] * size)), colour, True)
            continue
        if line:
            # A line is a row of dots, close enough together to touch.
            dot = max(1, round(line * size / 2))
            for points in path_outlines(shape, dot / size):
                for x, y in points:
                    pygraphics.circle(display_drv, round(move_x + x * scale_x), round(move_y + y * scale_y), dot, colour, True)
            continue
        outer = None
        for points in path_outlines(shape, 3 / size):
            # pygraphics fills a polygon of up to 256 corners.
            while len(points) > 256:
                points = points[::2]
            corners = array("h")
            for x, y in points:
                corners.append(round(move_x + x * scale_x))
                corners.append(round(move_y + y * scale_y))
            # The first outline of a letter is its outside. One that runs
            # the other way is a hole, filled with the ground again.
            way = turns(points) > 0
            if outer is None:
                outer = way
            pygraphics.poly(display_drv, 0, 0, corners, colour if way == outer else ground, True)


# The mark's parts in its own box: each is shapes, a scale and a place.
if SHOW_NAME:
    # The head at four fifths of its size, over the name, in a 340 by 280 box.
    box_width, box_height = 340, 280
    parts = [(HEAD, 1.2, 1.2, 33.2, 297.2)]
    for start, colour, letters in NAME:
        parts.append((((colour, 0, letters),), NAME_SCALE, -NAME_SCALE, start, BASELINE))
else:
    box_width, box_height = 256, 256
    parts = [(HEAD, 1.5, 1.5, -43, 379)]

width, height = display_drv.width, display_drv.height
ground = screen_colour(GROUND)
pygraphics.fill(display_drv, ground)

# The widest the mark can be and still fit both ways.
mark_width = min(width, height * box_width // box_height) * FILL // 100
mark_height = (mark_width * box_height + box_width // 2) // box_width

# The driver can't say whether a square screen is round, so every square one
# gets the height that keeps the name inside a circle.
lift = height * LIFT // 100 if SHOW_NAME and width == height else 0

if svgio:
    # Join the parts into one SVG document and ask for it that many pixels wide.
    mark = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d">' % (box_width, box_height)
    for part in parts:
        mark += svg_group(*part)
    decoder = svgio.SvgDecoder()
    mark_width, mark_height = decoder.open((mark + "</svg>").encode(), width=mark_width)

    # Draw it over a tile of the ground colour, so its edges blend into the
    # ground, then copy the tile to the middle of the screen.
    tile = pygraphics.FrameBuffer(bytearray(mark_width * mark_height * 2), mark_width, mark_height, pygraphics.RGB565)
    tile.fill(ground)
    decoder.decode(tile.buffer)
    pygraphics.blit_rect(display_drv, tile.buffer, (width - mark_width) // 2, (height - mark_height) // 2 - lift, mark_width, mark_height)
    method = "svgio"
else:
    # Scale each part from the mark's box to the screen and fill its shapes.
    scale = mark_width / box_width
    left, top = (width - mark_width) // 2, (height - mark_height) // 2 - lift
    small = SHOW_NAME and CAPITAL * NAME_SCALE * scale < SMALLEST_LETTERS
    for shapes, scale_x, scale_y, move_x, move_y in parts[:1] if small else parts:
        draw_polygons(shapes, scale_x * scale, scale_y * scale, left + move_x * scale, top + move_y * scale)
    if small:
        # Letter shapes this small fill in, so write the name in the built-in font.
        x, y = width // 2 - 40, top + round(BASELINE * scale) - 8
        for word, (start, colour, letters) in zip(("Omni", "Python"), NAME):
            pygraphics.text(display_drv, word, x, y, screen_colour(colour))
            x += 8 * len(word)
    method = "polygons"

display_drv.show()
print("%dx%d mark on a %dx%d screen, drawn with %s" % (mark_width, mark_height, width, height, method))
