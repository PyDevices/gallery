"""RokuAudioSink: the WAV it serves the TV, and the clock that paces it."""
import array
import os
import socket
import struct
import sys
import time
import unittest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "lib"))

from utils.roku_companion import RokuAudioSink


class _TV:
    host = "127.0.0.1"

    def __init__(self):
        self.launched = []

    def _launch(self, args):
        self.launched.append(args)


class _Format:
    rate, channels, bits, signed = 24000, 1, 16, True


class RokuAudioSinkTest(unittest.TestCase):
    def setUp(self):
        self.tv = _TV()
        self.sink = RokuAudioSink(self.tv, port=0, format=_Format(), my_ip="127.0.0.1")
        self.port = self.sink._sock.getsockname()[1]

    def tearDown(self):
        self.sink.close()

    def test_wav_has_a_length(self):
        # the TV's player waits forever on a WAV with no length
        c = socket.create_connection(("127.0.0.1", self.port), timeout=3)
        c.sendall(b"GET /stream.wav HTTP/1.0\r\n\r\n")
        data = b""
        while b"\r\n\r\n" not in data or len(data.split(b"\r\n\r\n", 1)[1]) < 44:
            data += c.recv(4096)
        c.close()
        head, wav = data.split(b"\r\n\r\n", 1)
        length = int(head.split(b"Content-Length: ")[1].split(b"\r\n")[0])
        riff, data_len = struct.unpack("<I", wav[4:8])[0], struct.unpack("<I", wav[40:44])[0]
        self.assertEqual(length, data_len + 44)
        self.assertEqual(riff, data_len + 36)
        self.assertEqual(data_len, 48000 * 3600)
        self.assertEqual(struct.unpack("<I", wav[24:28])[0], 24000)

    def test_writes_are_paced_by_the_clock(self):
        self.sink.LEAD = 0
        t = time.monotonic()
        for _ in range(15):                               # 300 ms as 20 ms arrays
            self.sink.write(array.array("h", [0] * 480))
        took = time.monotonic() - t
        self.assertEqual(self.tv.launched[0]["mode"], "audio")
        self.assertGreater(took, 0.25)                    # an array counts in bytes, not items
        self.assertLess(took, 0.6)


if __name__ == "__main__":
    unittest.main()
