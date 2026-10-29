"""pycast's sound path on CPython: the LPCM mux against castif's C muxer,
the resampler, the block ring, and the paced speaker."""
import array
import os
import sys
import time
import unittest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "lib", "examples", "cast"))

import pycast

PCM = bytes((i * 7 + 3) & 0xFF for i in range(1920))
AU = bytes((i * 13 + 1) & 0xFF for i in range(1000))


def _bytes(x):
    return b"".join(x) if isinstance(x, (list, tuple)) else bytes(x)


class TsMuxTest(unittest.TestCase):
    def test_matches_castif(self):
        # tsmux_lpcm_golden.hex is castif's tsmux.Muxer(lpcm=True) on the same calls
        with open(os.path.join(HERE, "data", "tsmux_lpcm_golden.hex")) as f:
            golden = bytes.fromhex(f.read().strip())
        m = pycast.TsMux(lpcm=True)
        out = b"".join(_bytes(x) for x in (
            m.tables(), m.video(AU, 123456, True), m.lpcm(PCM, 123000),
            m.lpcm(PCM, 123900), m.video(AU[:100], 126456, False)))
        self.assertEqual(len(out) % 188, 0)
        self.assertEqual(out, golden)

    def test_video_only_pmt_has_no_audio(self):
        pmt = _bytes(pycast.TsMux().tables())[188:]
        self.assertNotIn(bytes((0x83, 0xE1, 0x01)), pmt)
        self.assertIn(bytes((0x83, 0xE1, 0x01)), _bytes(pycast.TsMux(lpcm=True).tables())[188:])


class ResamplerTest(unittest.TestCase):
    def test_passthrough(self):
        self.assertEqual(pycast._resampler(48000, 2)(PCM), PCM)

    def test_24k_mono_doubles_and_duplicates(self):
        conv = pycast._resampler(24000, 1)
        src = array.array("h", range(0, 4800, 10))     # 480 frames, 20 ms
        out = array.array("h")
        for i in range(0, len(src), 37):              # odd chunks: the position carries
            out.frombytes(conv(src[i:i + 37].tobytes()))
        self.assertAlmostEqual(len(out) // 2, 960, delta=2)
        self.assertTrue(all(out[i] == out[i + 1] for i in range(0, len(out), 2)))
        left = out[::2]
        self.assertTrue(all(b >= a for a, b in zip(left, left[1:])))     # a ramp stays a ramp
        self.assertTrue(all(b - a <= 10 for a, b in zip(left, left[1:])))


class CastAudioTest(unittest.TestCase):
    def test_blocks_carry_and_stamp(self):
        a = pycast.CastAudio()
        a.feed(PCM[:1000], 10.0)
        self.assertEqual(a.waiting(), 0)
        a.feed(PCM[1000:] + PCM, 10.0 + 1000 / 192000)
        self.assertEqual(a.waiting(), 2)
        blk, t = a.take()
        self.assertEqual(blk, PCM)
        self.assertAlmostEqual(t, 10.0)
        self.assertAlmostEqual(a.take()[1], 10.01)

    def test_full_ring_keeps_newest(self):
        a = pycast.CastAudio(capacity=4)
        for i in range(6):
            a.feed(PCM, float(i))
        self.assertEqual((a.waiting(), a.full, a.fed), (4, 2, 6))
        self.assertEqual(a.take()[1], 2.0)


class CastAudioOutTest(unittest.TestCase):
    def test_paced_by_the_clock(self):
        a = pycast.CastAudio(capacity=1000)
        out = pycast.CastAudioOut(a, pycast._Format(48000, 2), lead_ms=80)
        t = time.monotonic()
        out.write(bytes(192000 * 3 // 10))            # 300 ms of sound
        took = time.monotonic() - t
        self.assertGreater(took, 0.18)                 # 300 ms less the 80 ms lead
        self.assertLess(took, 0.6)
        self.assertEqual(a.fed, 30)
        stamps = [a.take()[1] for _ in range(30)]
        self.assertAlmostEqual(stamps[-1] - stamps[0], 0.29, places=3)
        self.assertEqual(out.gaps, 0)

    def test_rejects_8_bit(self):
        with self.assertRaises(ValueError):
            pycast.CastAudioOut(pycast.CastAudio(), pycast._Format(48000, 2, 8))


if __name__ == "__main__":
    unittest.main()
