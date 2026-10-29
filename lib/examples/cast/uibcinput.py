"""The laptop's mouse, keyboard, touchscreen and remote, arriving over the
cast's back channel, as a pydevices input device: a cursor the board
integrates from the relative mouse reports, clicks as touches at the cursor,
fingers on a touchscreen as touches where they are, and HID keyboard and
remote-control reports as the set of pressed K_* codes. Merged into a board's
``touch_read`` and ``keypad_read`` so an app cannot tell them from the panel's
own touch and keys.

Touch and remote reports are laid out by the report descriptor the sender
sends first, so they are decoded by reading it (``parse_descriptor``).
"""
import keys

_HID_CHARS = {0x28: 13, 0x29: 27, 0x2A: 8, 0x2B: 9, 0x2C: 32, 0x2D: 45, 0x2E: 61, 0x2F: 91, 0x30: 93,
              0x31: 92, 0x33: 59, 0x34: 39, 0x35: 96, 0x36: 44, 0x37: 46, 0x38: 47}


def hid_keycode(usage):
    """keys.hid_keycode where the board's keys module has it; the same table otherwise."""
    f = getattr(keys, "hid_keycode", None)
    if f:
        return f(usage)
    if 0x04 <= usage <= 0x1D:
        return 97 + usage - 0x04
    if 0x1E <= usage <= 0x26:
        return 49 + usage - 0x1E
    if usage == 0x27:
        return 48
    if usage in _HID_CHARS:
        return _HID_CHARS[usage]
    if usage >= 0x39:
        return usage | 0x40000000
    return None


# HID usage pages and the usages read here
_DESKTOP = 0x01
_KEYBOARD = 0x07
_DIGITIZER = 0x0D
_CONSUMER = 0x0C
_X, _Y = (_DESKTOP, 0x30), (_DESKTOP, 0x31)
_TIP = (_DIGITIZER, 0x42)
_CONTACT_ID = (_DIGITIZER, 0x51)
_CONTACT_COUNT = (_DIGITIZER, 0x54)
_FINGER = (_DIGITIZER, 0x22)

# a remote control's buttons as the K_* codes an app already reads
_REMOTE_KEYS = {
    (_CONSUMER, 0x40): 1073741942,   # Menu: K_MENU
    (_CONSUMER, 0x41): 13,           # Menu Pick: K_RETURN
    (_CONSUMER, 0x42): 1073741906,   # Menu Up: K_UP
    (_CONSUMER, 0x43): 1073741905,   # Menu Down: K_DOWN
    (_CONSUMER, 0x44): 1073741904,   # Menu Left: K_LEFT
    (_CONSUMER, 0x45): 1073741903,   # Menu Right: K_RIGHT
    (_CONSUMER, 0x46): 27,           # Menu Escape: K_ESCAPE
    (_CONSUMER, 0xB0): 1073742085,   # Play: K_AUDIOPLAY
    (_CONSUMER, 0xB1): 1073742085,   # Pause
    (_CONSUMER, 0xCD): 1073742085,   # Play/Pause
    (_CONSUMER, 0xB5): 1073742082,   # Next: K_AUDIONEXT
    (_CONSUMER, 0xB6): 1073742083,   # Previous: K_AUDIOPREV
    (_CONSUMER, 0xB7): 1073742084,   # Stop: K_AUDIOSTOP
    (_CONSUMER, 0xE2): 1073741951,   # Mute: K_MUTE
    (_CONSUMER, 0xE9): 1073741952,   # Volume Up: K_VOLUMEUP
    (_CONSUMER, 0xEA): 1073741953,   # Volume Down: K_VOLUMEDOWN
    (_CONSUMER, 0x223): 1073742093,  # AC Home: K_AC_HOME
    (_CONSUMER, 0x224): 1073742094,  # AC Back: K_AC_BACK
    (_DESKTOP, 0x90): 1073741906,    # D-pad Up
    (_DESKTOP, 0x91): 1073741905,    # D-pad Down
    (_DESKTOP, 0x92): 1073741903,    # D-pad Right
    (_DESKTOP, 0x93): 1073741904,    # D-pad Left
}


class Field:
    """One input field of a HID report: where its bits are and what they mean.
    A variable field holds one usage's value; an array field holds the index
    of a usage that is on (a pressed button, say), counted from ``usage``."""

    def __init__(self, page, usage, bit, size, lmin, lmax, coll, array, usage_max=0):
        self.page, self.usage, self.bit, self.size = page, usage, bit, size
        self.lmin, self.lmax, self.coll, self.array = lmin, lmax, coll, array
        self.usage_max = usage_max

    def value(self, data):
        byte, shift = self.bit >> 3, self.bit & 7
        n = (shift + self.size + 7) >> 3
        raw = int.from_bytes(bytes(data[byte:byte + n]) + bytes(4), "little") >> shift
        v = raw & ((1 << self.size) - 1)
        if self.lmin < 0 and v & (1 << (self.size - 1)):
            v -= 1 << self.size
        return v


def _signed(b):
    v = int.from_bytes(b, "little") if b else 0
    if b and b[-1] & 0x80:
        v -= 1 << (8 * len(b))
    return v


def parse_descriptor(desc):
    """A HID report descriptor's input reports: {report ID: [Field, ...]}, and
    the usage of each collection, by the number a Field's ``coll`` holds.
    Only what reading input needs: no outputs, features or designators."""
    reports = {}
    colls = [None]          # collection number -> its (page, usage)
    stack = [0]
    g = {"page": 0, "lmin": 0, "lmax": 0, "size": 0, "count": 0, "id": 0}
    saved = []
    usages, umin, umax = [], None, None
    offsets = {}
    i = 0
    while i < len(desc):
        b = desc[i]
        if b == 0xFE:                               # long item
            i += 3 + (desc[i + 1] if i + 1 < len(desc) else 0)
            continue
        n = (0, 1, 2, 4)[b & 3]
        data = bytes(desc[i + 1:i + 1 + n])
        i += 1 + n
        kind, tag = (b >> 2) & 3, b >> 4
        u = int.from_bytes(data, "little") if data else 0
        if kind == 1:                               # global
            if tag == 0:
                g["page"] = u
            elif tag == 1:
                g["lmin"] = _signed(data)
            elif tag == 2:
                g["lmax"] = _signed(data) if g["lmin"] < 0 else u
            elif tag == 7:
                g["size"] = u
            elif tag == 8:
                g["id"] = u
            elif tag == 9:
                g["count"] = u
            elif tag == 10:
                saved.append(dict(g))
            elif tag == 11 and saved:
                g = saved.pop()
        elif kind == 2:                             # local
            full = (u >> 16, u & 0xFFFF) if n == 4 else (g["page"], u)
            if tag == 0:
                usages.append(full)
            elif tag == 1:
                umin = full
            elif tag == 2:
                umax = full
        elif kind == 0:                             # main
            if tag == 10:                           # collection
                colls.append(usages[0] if usages else None)
                stack.append(len(colls) - 1)
            elif tag == 12 and len(stack) > 1:      # end collection
                stack.pop()
            elif tag == 8:                          # input
                rid = g["id"]
                bit = offsets.get(rid, 8 if rid else 0)
                fields = reports.setdefault(rid, [])
                const = u & 1
                variable = u & 2
                for k in range(g["count"]):
                    if not const:
                        if variable:
                            if usages:
                                page, usage = usages[min(k, len(usages) - 1)]
                            elif umin is not None:
                                page, usage = umin[0], umin[1] + k
                            else:
                                page, usage = g["page"], 0
                            fields.append(Field(page, usage, bit, g["size"], g["lmin"], g["lmax"],
                                                stack[-1], False))
                        else:
                            first = umin if umin is not None else (usages[0] if usages else (g["page"], 0))
                            last = umax[1] if umax is not None else first[1] + g["lmax"] - g["lmin"]
                            fields.append(Field(first[0], first[1], bit, g["size"], g["lmin"], g["lmax"],
                                                stack[-1], True, last))
                    bit += g["size"]
                offsets[rid] = bit
            usages, umin, umax = [], None, None
    return reports, colls


class UibcInput:
    def __init__(self, width, height, local_touch=None, local_keys=None):
        self.w = width
        self.h = height
        self.cx = width // 2
        self.cy = height // 2
        self.buttons = 0
        self.keys = set()
        self.local_touch = local_touch
        self.local_keys = local_keys
        self.reports = 0
        self.moved = 0
        self.layouts = {}           # HID type -> parse_descriptor() of what the sender described
        self.fingers = {}           # contact id -> (x, y) of each finger down on a touchscreen
        self.remote_keys = set()

    def feed(self, kind, data):
        """One decoded UIBC report from micecast.Session's on_input."""
        if kind == "hid_mouse" and len(data) >= 4:
            # report ID 0x28: buttons, dx, dy, wheel, pan; the deltas are signed bytes
            dx = data[2] - 256 if data[2] > 127 else data[2]
            dy = data[3] - 256 if data[3] > 127 else data[3]
            if dx or dy:
                self.cx = min(max(self.cx + dx, 0), self.w - 1)
                self.cy = min(max(self.cy + dy, 0), self.h - 1)
                self.moved += 1
            self.buttons = data[1]
            self.reports += 1
        elif kind == "hid_keyboard" and len(data) >= 9:
            # report ID 0x29: modifiers, reserved, six usages
            pressed = set()
            for u in data[3:9]:
                if u:
                    code = hid_keycode(u)
                    if code is not None:
                        pressed.add(code)
            for i in range(8):
                if data[1] & (1 << i):
                    pressed.add(0x400000E0 + i)   # K_LCTRL .. K_RGUI, the HID modifier usages
            self.keys = pressed
            self.reports += 1
        elif kind.endswith("_descriptor"):
            self.layouts[kind[4:-11]] = parse_descriptor(data)
        elif kind == "hid_multi_touch" and "multi_touch" in self.layouts:
            self._touch(data)
        elif kind == "hid_remote" and "remote" in self.layouts:
            self._remote(data)

    def _layout(self, kind, data):
        reports, colls = self.layouts[kind]
        if not data:
            return None, colls
        return reports.get(data[0]) or reports.get(0), colls

    def _touch(self, data):
        # One report carries one or more fingers, each in its own Finger
        # collection: tip switch, contact id, X and Y. With "hybrid" reports
        # (Windows' way) the contact count says how many of them are real.
        fields, colls = self._layout("multi_touch", data)
        if not fields:
            return
        groups = {}
        order = []
        count = None
        for f in fields:
            key = (f.page, f.usage)
            if key == _CONTACT_COUNT:
                count = f.value(data)
            elif colls[f.coll] == _FINGER or key in (_TIP, _CONTACT_ID, _X, _Y):
                if f.coll not in groups:
                    groups[f.coll] = {}
                    order.append(f.coll)
                groups[f.coll][key] = f
        if count == 0:
            # a hybrid report's later part: nothing new
            self.reports += 1
            return
        for c in order[:count] if count else order:
            g = groups[c]
            if _X not in g or _Y not in g:
                continue
            cid = g[_CONTACT_ID].value(data) if _CONTACT_ID in g else c
            down = g[_TIP].value(data) if _TIP in g else 1
            if down:
                fx, fy = g[_X], g[_Y]
                x = (fx.value(data) - fx.lmin) * self.w // (fx.lmax - fx.lmin + 1)
                y = (fy.value(data) - fy.lmin) * self.h // (fy.lmax - fy.lmin + 1)
                self.fingers[cid] = (min(max(x, 0), self.w - 1), min(max(y, 0), self.h - 1))
            else:
                self.fingers.pop(cid, None)
        self.reports += 1

    def _remote(self, data):
        fields, _ = self._layout("remote", data)
        if not fields:
            return
        pressed = set()
        for f in fields:
            v = f.value(data)
            if f.array:
                if v < f.lmin or v > f.lmax:
                    continue
                usage = f.usage + v - f.lmin
                if usage == 0 or usage > f.usage_max:
                    continue
                key = (f.page, usage)
            else:
                if not v:
                    continue
                key = (f.page, f.usage)
            if key[0] == _KEYBOARD:
                code = hid_keycode(key[1])
            else:
                code = _REMOTE_KEYS.get(key)
            if code is not None:
                pressed.add(code)
        self.remote_keys = pressed
        self.reports += 1

    def read_points(self):
        """A touch_read: the panel's own touches first, else fingers on the
        laptop's touchscreen, else the cursor while the left button is held."""
        pts = self.local_touch() if self.local_touch else ()
        if pts:
            return pts
        if self.fingers:
            return tuple(self.fingers.values())
        return ((self.cx, self.cy),) if self.buttons & 1 else ()

    def read_keys(self):
        """A keypad_read: the panel's keys plus the laptop's."""
        local = set(self.local_keys() or ()) if self.local_keys else set()
        return local | self.keys | self.remote_keys

    def install(self, board_config):
        """Make the board read this device: touch_read and keypad_read now include it."""
        self.local_touch = getattr(board_config, "touch_read", None)
        self.local_keys = getattr(board_config, "keypad_read", None)
        board_config.touch_read = self.read_points
        board_config.keypad_read = self.read_keys
        return self
