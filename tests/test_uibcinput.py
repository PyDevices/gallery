"""uibcinput: a touchscreen's and a remote's HID reports, read by their
report descriptors, become touches and keys."""
import os
import sys
import types
import unittest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "lib", "examples", "cast"))
sys.modules.setdefault("keys", types.ModuleType("keys"))   # the table in uibcinput stands in

import uibcinput

K_UP, K_RETURN, K_AUDIOPLAY, K_VOLUMEUP, K_AC_BACK = 1073741906, 13, 1073742085, 1073741952, 1073742094

_FINGER = bytes.fromhex(
    "0922"          # Usage (Finger)
    "a102"          # Collection (Logical)
    "0942 0947"     # Usage (Tip Switch), Usage (Confidence)
    "1500 2501 7501 9502 8102"      # 0..1, 1 bit x2, Input (Data,Var,Abs)
    "9506 8103"     # 6 bits padding, Input (Const)
    "0951 7508 9501 8102"           # Contact Identifier, 8 bits
    "0501 26ff7f"    # Usage Page (Desktop), Logical Max 32767 (lmin still 0)
    "7510 9501 0930 8102"           # X, 16 bits
    "0931 8102"     # Y, 16 bits
    "050d"          # back to Usage Page (Digitizer)
    "c0".replace(" ", ""))
# Windows' kind: report 0x13, two fingers per report, then the contact count
MULTITOUCH = bytes.fromhex("050d 0904 a101 8513".replace(" ", "")) + _FINGER + _FINGER + bytes.fromhex(
    "0954 2508 7508 9501 8102 c0".replace(" ", ""))
# a consumer-control remote: report 0x2A, one 16-bit array slot of usages 0..0x3FF
REMOTE = bytes.fromhex("050c 0901 a101 852a 1500 26ff03 1900 2aff03 7510 9501 8100 c0".replace(" ", ""))


def touch(*fingers, count=None):
    body = bytearray([0x13])
    for tip, cid, x, y in fingers:
        body += bytes([tip | (tip << 1), cid]) + x.to_bytes(2, "little") + y.to_bytes(2, "little")
    while len(body) < 1 + 2 * 6:
        body += bytes(6)
    body.append(len(fingers) if count is None else count)
    return bytes(body)


class DescriptorTest(unittest.TestCase):
    def test_multitouch_layout(self):
        reports, colls = uibcinput.parse_descriptor(MULTITOUCH)
        fields = reports[0x13]
        xs = [f for f in fields if (f.page, f.usage) == (1, 0x30)]
        self.assertEqual([f.bit for f in xs], [8 + 16, 8 + 64])
        self.assertEqual((xs[0].size, xs[0].lmin, xs[0].lmax), (16, 0, 32767))
        self.assertEqual(colls[xs[0].coll], (0x0D, 0x22))
        count = [f for f in fields if (f.page, f.usage) == (0x0D, 0x54)][0]
        self.assertEqual(count.bit, 8 + 96)

    def test_remote_layout(self):
        reports, _ = uibcinput.parse_descriptor(REMOTE)
        f = reports[0x2A][0]
        self.assertTrue(f.array)
        self.assertEqual((f.page, f.usage, f.usage_max, f.size), (0x0C, 0, 0x3FF, 16))


class TouchTest(unittest.TestCase):
    def setUp(self):
        self.u = uibcinput.UibcInput(720, 720)
        self.u.feed("hid_multi_touch_descriptor", MULTITOUCH)

    def test_a_finger_lands_where_it_touched(self):
        self.u.feed("hid_multi_touch", touch((1, 7, 16384, 8192)))
        self.assertEqual(self.u.read_points(), ((360, 180),))
        self.u.feed("hid_multi_touch", touch((0, 7, 16384, 8192)))
        self.assertEqual(self.u.read_points(), ())

    def test_two_fingers_and_a_hybrid_report(self):
        self.u.feed("hid_multi_touch", touch((1, 1, 0, 0), (1, 2, 32767, 32767)))
        self.assertEqual(sorted(self.u.read_points()), [(0, 0), (719, 719)])
        # a second report for the same frame, count 0: nothing changes
        self.u.feed("hid_multi_touch", touch((0, 1, 0, 0), count=0))
        self.assertEqual(len(self.u.read_points()), 2)
        self.u.feed("hid_multi_touch", touch((0, 1, 0, 0)))
        self.assertEqual(self.u.read_points(), ((719, 719),))

    def test_the_panel_comes_first(self):
        self.u.local_touch = lambda: ((5, 5),)
        self.u.feed("hid_multi_touch", touch((1, 1, 100, 100)))
        self.assertEqual(self.u.read_points(), ((5, 5),))

    def test_no_descriptor_no_touch(self):
        u = uibcinput.UibcInput(720, 720)
        u.feed("hid_multi_touch", touch((1, 1, 100, 100)))
        self.assertEqual(u.read_points(), ())


class RemoteTest(unittest.TestCase):
    def setUp(self):
        self.u = uibcinput.UibcInput(720, 720)
        self.u.feed("hid_remote_descriptor", REMOTE)

    def press(self, usage):
        self.u.feed("hid_remote", bytes([0x2A]) + usage.to_bytes(2, "little"))
        return self.u.read_keys()

    def test_buttons_are_keys(self):
        self.assertEqual(self.press(0x42), {K_UP})
        self.assertEqual(self.press(0x41), {K_RETURN})
        self.assertEqual(self.press(0xCD), {K_AUDIOPLAY})
        self.assertEqual(self.press(0xE9), {K_VOLUMEUP})
        self.assertEqual(self.press(0x224), {K_AC_BACK})
        self.assertEqual(self.press(0), set())          # released

    def test_unknown_button_is_ignored(self):
        self.assertEqual(self.press(0x3FE), set())

    def test_keyboard_and_remote_together(self):
        self.u.feed("hid_keyboard", bytes([0x29, 0, 0, 0x04, 0, 0, 0, 0, 0]))
        self.assertEqual(self.press(0x42), {97, K_UP})


if __name__ == "__main__":
    unittest.main()
