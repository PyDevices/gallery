# pycast.py -- castif's cast on CPython: ffmpeg encodes the H.264, Python muxes
# the MPEG-TS and sends the RTP, for micecast's session. So CastDisplay (and any
# app on ../miracast/board_config.py) runs from python and python.exe, to a Roku
# or Windows' Wireless Display, with no ESP32-P4.
#
# The bytes on the wire are castif's: TsMux is tsmux_core.c line for line (the
# PAT and PMT, the access-unit delimiter in the PES header, the PCR 400 ms
# ahead of the PTS in each frame's first packet), and the RTP is castif's, 7 TS
# packets to a datagram, payload type 33, from the server port the session
# advertised. That matters: Windows' receiver checks the stream strictly, and
# castif's is a stream it is known to accept.
#
# Sound, when the caster has a CastAudio: castif's LPCM track, 48 kHz stereo
# in 10 ms blocks on the video's clock. It is filled by an app writing PCM
# (CastAudioOut, which audiodev hands an app as its speaker) or by a second
# ffmpeg reading any input ffmpeg can open (FfmpegAudioInput: a file, a URL,
# a microphone). Without one the PMT lists the video only.
import collections
import shutil
import socket
import subprocess
import threading
import time

PID_PMT = 0x1000
PID_VIDEO = 0x100
PID_AUDIO = 0x101
PCR_LEAD = 36000            # 400 ms in 90 kHz ticks
RATE = 48000                # the cast's LPCM: 48 kHz stereo, 16-bit
BLOCK_BYTES = 1920          # one 10 ms block
BLOCK_S = 0.01
REJOIN = 9000               # a gap past 100 ms re-anchors the track (castif's)


def _crc32_mpeg(data):
    c = 0xFFFFFFFF
    for b in data:
        c ^= b << 24
        for _ in range(8):
            c = ((c << 1) ^ 0x04C11DB7) & 0xFFFFFFFF if c & 0x80000000 else (c << 1) & 0xFFFFFFFF
    return c


def _section(table_id, ident, body):
    length = 5 + len(body) + 4
    sec = bytes([table_id, 0xB0 | ((length >> 8) & 0x0F), length & 0xFF, ident >> 8, ident & 0xFF, 0xC1, 0, 0]) + body
    return sec + _crc32_mpeg(sec).to_bytes(4, "big")


def _pts_field(pts):
    return bytes([0x21 | ((pts >> 29) & 0x0E), (pts >> 22) & 0xFF, 0x01 | ((pts >> 14) & 0xFE),
                  (pts >> 7) & 0xFF, 0x01 | ((pts << 1) & 0xFE)])


class TsMux:
    """tsmux_core.c: each call returns the 188-byte packets. ``lpcm=True``
    adds castif's LPCM stream to the PMT."""

    def __init__(self, lpcm=False):
        self.cc = {0: 0, PID_PMT: 0, PID_VIDEO: 0, PID_AUDIO: 0}
        pat = _section(0x00, 1, bytes([0, 1, 0xE0 | (PID_PMT >> 8), PID_PMT & 0xFF]))
        es = bytes([0xE0 | (PID_VIDEO >> 8), PID_VIDEO & 0xFF, 0xF0, 0x00,
                    0x1B, 0xE0 | (PID_VIDEO >> 8), PID_VIDEO & 0xFF, 0xF0, 0x00])
        if lpcm:
            # HDMV LPCM, with the registration descriptor castif sends
            es += bytes([0x83, 0xE0 | (PID_AUDIO >> 8), PID_AUDIO & 0xFF, 0xF0, 0x04, 0x83, 0x02, 0x46, 0x2F])
        pmt = _section(0x02, 1, es)
        self.pat_body = (b"\x00" + pat).ljust(184, b"\xff")
        self.pmt_body = (b"\x00" + pmt).ljust(184, b"\xff")

    def _head(self, pid, pusi, afc):
        cc = self.cc[pid]
        self.cc[pid] = (cc + 1) & 15
        return bytes([0x47, (0x40 if pusi else 0) | (pid >> 8), pid & 0xFF, (afc << 4) | cc])

    def tables(self):
        return [self._head(0, True, 1) + self.pat_body, self._head(PID_PMT, True, 1) + self.pmt_body]

    def video(self, au, pts, key):
        pts &= 0xFFFFFFFF
        pes = bytes([0, 0, 1, 0xE0, 0, 0, 0x80, 0x80, 5]) + _pts_field(pts) + bytes([0, 0, 0, 1, 9, 0xF0]) + au
        pcr = (pts - PCR_LEAD) & 0xFFFFFFFF
        pcr_af = bytes([0x50 if key else 0x10, (pcr >> 25) & 0xFF, (pcr >> 17) & 0xFF,
                        (pcr >> 9) & 0xFF, (pcr >> 1) & 0xFF, ((pcr & 1) << 7) | 0x7E, 0])
        out = []
        pos, total, first = 0, len(pes), True
        while pos < total:
            remaining = total - pos
            if first:
                room = 176
                if remaining < room:
                    pad = room - remaining
                    pkt = self._head(PID_VIDEO, True, 3) + bytes([7 + pad]) + pcr_af + b"\xff" * pad
                    room = remaining
                else:
                    pkt = self._head(PID_VIDEO, True, 3) + bytes([7]) + pcr_af
            else:
                room = 184
                if remaining < room:
                    pad = room - remaining
                    af = bytes([pad - 1]) + ((b"\x00" + b"\xff" * (pad - 2)) if pad >= 2 else b"")
                    pkt = self._head(PID_VIDEO, False, 3) + af
                    room = remaining
                else:
                    pkt = self._head(PID_VIDEO, False, 1)
            pkt += pes[pos:pos + room]
            pos += room
            out.append(pkt)
            first = False
        return out

    def lpcm(self, pcm, pts):
        """One block of 48 kHz stereo s16 little-endian PCM as an LPCM PES:
        tsmux_lpcm, byte-swapped to the big-endian samples LPCM carries."""
        pts &= 0xFFFFFFFF
        n = len(pcm) + 4
        head = bytes([0, 0, 1, 0xBD, ((n + 8) >> 8) & 0xFF, (n + 8) & 0xFF, 0x80, 0x80, 5]) + _pts_field(pts) + \
            bytes([0xA0, 6, 0, 0x11])           # LPCM audio header: 48 kHz, 16-bit, stereo
        swapped = bytearray(len(pcm))
        swapped[0::2] = pcm[1::2]
        swapped[1::2] = pcm[0::2]
        pes = head + swapped
        out = []
        pos, total, first = 0, len(pes), True
        while pos < total:
            remaining = total - pos
            if remaining < 184:
                pad = 184 - remaining
                af = bytes([pad - 1]) + ((b"\x00" + b"\xff" * (pad - 2)) if pad >= 2 else b"")
                pkt = self._head(PID_AUDIO, first, 3) + af + pes[pos:]
                pos = total
            else:
                pkt = self._head(PID_AUDIO, first, 1) + pes[pos:pos + 184]
                pos += 184
            out.append(pkt)
            first = False
        return out


class CastAudio:
    """The cast's sound track: 10 ms blocks of 48 kHz stereo s16 PCM, each
    stamped with the time.monotonic() at which its first sample should be
    heard. Producers ``feed`` it; the streamer takes one block every 10 ms
    and muxes it as LPCM, the way castif's task drains its ring."""

    def __init__(self, capacity=64):
        self.capacity = capacity        # 640 ms, castif's ring
        self.blocks = collections.deque()
        self.lock = threading.Lock()
        self.carry = b""
        self.carry_t = None
        self.fed = 0
        self.full = 0                   # oldest blocks let go because the ring was full

    def feed(self, pcm, stamp=None):
        """Add PCM (48 kHz stereo s16le, any length). ``stamp`` is when its
        first sample is due (default: now)."""
        if stamp is None:
            stamp = time.monotonic()
        with self.lock:
            if self.carry:
                stamp -= len(self.carry) / (RATE * 4)
                pcm = self.carry + bytes(pcm)
            pos = 0
            while pos + BLOCK_BYTES <= len(pcm):
                if len(self.blocks) >= self.capacity:
                    # nobody is draining (no session yet) or the producer ran
                    # ahead: keep the newest sound, as the pump's tap does
                    self.blocks.popleft()
                    self.full += 1
                self.blocks.append((bytes(pcm[pos:pos + BLOCK_BYTES]), stamp + pos / (RATE * 4)))
                self.fed += 1
                pos += BLOCK_BYTES
            self.carry = bytes(pcm[pos:])

    def take(self):
        with self.lock:
            return self.blocks.popleft() if self.blocks else None

    def waiting(self):
        return len(self.blocks)


def _resampler(rate, channels):
    """A function turning s16le PCM at (rate, channels) into 48 kHz stereo,
    by linear interpolation, carrying its position across calls."""
    import array

    if rate == RATE and channels == 2:
        return bytes
    step = rate / RATE
    state = {"pos": 0.0, "prev": [0] * channels}

    def convert(b):
        src = array.array("h")
        src.frombytes(bytes(b))
        frames = len(src) // channels
        if not frames:
            return b""
        prev = state["prev"]
        out = array.array("h")
        pos = state["pos"]          # in input frames; below 0 interpolates from the last call's frame
        while pos <= frames - 1:
            i = int(pos // 1)
            f = pos - i
            for c in range(channels):
                a = prev[c] if i < 0 else src[i * channels + c]
                v = a if f == 0 else int(a + (src[(i + 1) * channels + c] - a) * f)
                out.append(v)
                if channels == 1:
                    out.append(v)
            pos += step
        state["prev"] = [src[(frames - 1) * channels + c] for c in range(channels)]
        state["pos"] = pos - frames
        return out.tobytes()

    return convert


try:
    from audiodev import AudioFormat as _AudioFormat
    from audiodev import PCMOutput as _PCMOutput
except ImportError:                     # no PyDevices: a plain object with the same methods
    _AudioFormat = None

    class _PCMOutput:
        def __init__(self, format, **kwargs):
            self.format = format
            self.is_open = False

        def open(self):
            self.is_open = True
            return self

        def write(self, buf):
            self.open()
            done = 0
            view = memoryview(buf)
            while done < len(view):
                done += self._write(view[done:])
            return len(buf)

        def close(self):
            self.is_open = False


class _Format:
    def __init__(self, rate, channels, bits=16):
        self.rate, self.channels, self.bits = rate, channels, bits
        self.signed = True
        self.frame_size = channels * bits // 8


class CastAudioOut(_PCMOutput):
    """A speaker whose sound goes out on the cast: an audiodev PCMOutput, so
    an app (or ``audiodev``'s ``audio_out`` player) writes to it as to any
    sound card. Writes are paced by the wall clock, a little ahead of it, the
    way a sound card's buffer paces them; any 16-bit rate and channel count is
    converted to the cast's 48 kHz stereo."""

    def __init__(self, audio, format=None, lead_ms=80, **kwargs):
        if format is None:
            format = _AudioFormat(RATE, 2, 16) if _AudioFormat else _Format(RATE, 2)
        if getattr(format, "bits", 16) != 16:
            raise ValueError("the cast takes 16-bit PCM")
        super().__init__(format)
        self.audio = audio
        self.lead = lead_ms / 1000
        self.bps = format.rate * format.channels * 2
        self._convert = _resampler(format.rate, format.channels)
        self.t0 = None              # when the first byte written is due
        self.written = 0            # bytes accepted since t0
        self.gaps = 0               # times the writer fell behind and the clock restarted

    def _due(self, now):
        return self.t0 + self.written / self.bps - now     # seconds of sound queued ahead

    def _write(self, buf):
        frame = self.format.channels * 2
        while True:
            now = time.monotonic()
            if self.t0 is None or self._due(now) < -0.1:
                if self.t0 is not None:
                    self.gaps += 1      # the writer stalled: the sink hears a gap, then resumes
                self.t0, self.written = now, 0
            room = int((self.lead - self._due(now)) * self.bps) // frame * frame
            if room >= frame:
                break
            time.sleep(min(0.01, -room / self.bps + 0.002))
        n = min(len(buf), room)
        n -= n % frame
        stamp = self.t0 + self.written / self.bps
        self.audio.feed(self._convert(buf[:n]), stamp)
        self.written += n
        return n

    def queued_size(self):
        if self.t0 is None:
            return 0
        return max(0, int(self._due(time.monotonic()) * self.bps))

    def service(self):
        pass

    def is_active(self):
        return self.queued_size() > 0

    def close(self):
        self.t0 = None
        try:
            super().close()
        except Exception:
            pass


class FfmpegAudioInput:
    """The cast's sound from anything ffmpeg can read: ``source`` is a file
    or URL (played in real time, looped with ``loop=True``), or a list of
    ffmpeg input arguments, such as ``["-f", "dshow", "-i", "audio=Microphone"]``
    on Windows or ``["-f", "pulse", "-i", "default"]`` on Linux. A second
    ffmpeg decodes it to the cast's PCM, stamped by its own sample count from
    the first arrival: ffmpeg reads a file in a burst before settling to real
    time, so arrival times would label the burst late."""

    def __init__(self, audio, source, loop=False, ffmpeg=None):
        self.audio = audio
        if isinstance(source, str):
            args = ["-re"] + (["-stream_loop", "-1"] if loop else []) + ["-i", source]
        else:
            args = list(source)
        cmd = [ffmpeg or _ffmpeg(), "-loglevel", "error", "-nostdin"] + args + [
            "-vn", "-f", "s16le", "-ar", str(RATE), "-ac", "2", "-"]
        self.proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stdin=subprocess.DEVNULL)
        self.bytes = 0
        self.restarts = 0           # times the input fell behind real time and the clock restarted
        self.running = True
        threading.Thread(target=self._read, daemon=True).start()

    def _read(self):
        out = self.proc.stdout
        bps = RATE * 4
        t0 = None
        n = 0                       # bytes since t0
        while self.running:
            d = out.read1(BLOCK_BYTES * 4) if hasattr(out, "read1") else out.read(BLOCK_BYTES)
            if not d:
                break
            self.bytes += len(d)
            now = time.monotonic()
            if t0 is None or now - (t0 + (n + len(d)) / bps) > 0.2:
                if t0 is not None:
                    self.restarts += 1  # a stall: what comes next is due now
                t0, n = now - len(d) / bps, 0
            self.audio.feed(d, t0 + n / bps)
            n += len(d)

    def close(self):
        self.running = False
        try:
            self.proc.kill()
            self.proc.wait(3)
        except Exception:
            pass


def _ffmpeg():
    """ffmpeg: the FFMPEG environment variable's, or the one on the PATH."""
    import os

    ff = os.environ.get("FFMPEG") or shutil.which("ffmpeg")
    if ff is None:
        raise RuntimeError("CastDisplay on a desktop needs ffmpeg on the PATH (https://ffmpeg.org)")
    return ff


class FfmpegCaster:
    """castif.Cast's part of the interface CastDisplay uses: the picture's
    size, the stream's, and its counters."""

    def __init__(self, width, height, canvas=None, fps=30, bitrate=3_000_000, audio=None,
                 audio_source=None, audio_loop=False):
        self.ffmpeg = _ffmpeg()
        self.w, self.h = width, height
        self.cw, self.ch = canvas or (width, height)
        self.fps, self.bitrate = fps, bitrate
        self.audio = audio          # a CastAudio, or None for a silent cast
        # what a second ffmpeg reads into it, started with each session so a
        # file plays from its start when the sink is listening
        self.audio_source, self.audio_loop = audio_source, audio_loop
        if audio_source is not None and audio is None:
            self.audio = CastAudio()
        self.frames = self.sent = self.stalls = 0
        self.audio_muxed = self.audio_inserted = self.audio_dropped = 0
        self.audio_rejoins = self.audio_underruns = 0
        self.audio_drift_ms = 0
        self._t0 = None             # the first frame sent: the rate counts from there

    def mark_dirty(self):
        pass                # every tick is encoded; there is no skip to defeat

    def stats(self):
        el = time.monotonic() - self._t0 if self._t0 is not None else 0
        st = {"frames": self.frames, "fps": int(1000 * self.frames / el) if el else 0,
              "sent": self.sent, "stalls": self.stalls}
        if self.audio is not None:
            st.update(audio_fed=self.audio.fed, audio_muxed=self.audio_muxed,
                      audio_level=self.audio.waiting(), audio_underruns=self.audio_underruns,
                      audio_drift_ms=self.audio_drift_ms, audio_inserted=self.audio_inserted,
                      audio_dropped=self.audio_dropped, audio_rejoins=self.audio_rejoins,
                      audio_full=self.audio.full)
        return st

    def close(self):
        pass


class FfmpegStreamer:
    """micecast's streamer interface (pump, done, idle_poll, force_idr, close)
    over ffmpeg: a feeder thread hands it the framebuffer at the frame rate, a
    reader thread muxes each access unit it returns and sends it."""

    def __init__(self, caster, fb, dst_ip, dst_port, server_port, seconds, log):
        self.c, self.fb, self.log = caster, fb, log
        self.seconds = seconds
        self.done = False
        self.idle_poll = True
        self.mux = TsMux(lpcm=caster.audio is not None)
        self.audio = caster.audio
        self.send_lock = threading.Lock()   # the picture and the sound share the mux and the RTP sequence
        self._last_pts = 90000
        self.dst = (dst_ip, dst_port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", server_port))
        self.seq = 0
        self.pts = []               # capture times, one per frame given to ffmpeg
        self.lock = threading.Lock()
        c = caster
        vf = []
        if (c.cw, c.ch) != (c.w, c.h):
            vf = ["-vf", "pad=%d:%d:%d:%d:black" % (c.cw, c.ch, ((c.cw - c.w) // 2) & ~1, ((c.ch - c.h) // 2) & ~1)]
        cmd = [c.ffmpeg, "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb565le",
               "-s", "%dx%d" % (c.w, c.h), "-r", str(c.fps), "-i", "-"] + vf + [
               "-c:v", "libx264", "-preset", "ultrafast", "-tune", "zerolatency",
               "-profile:v", "baseline", "-pix_fmt", "yuv420p", "-bf", "0",
               "-g", str(c.fps), "-keyint_min", str(c.fps), "-sc_threshold", "0",
               "-b:v", str(c.bitrate), "-maxrate", str(c.bitrate), "-bufsize", str(c.bitrate // 2),
               "-x264-params", "aud=1:repeat-headers=1", "-f", "h264", "-"]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self.t0 = time.monotonic()
        self.running = True
        threading.Thread(target=self._feed, daemon=True).start()
        threading.Thread(target=self._read, daemon=True).start()
        self.audio_in = None
        if self.audio is not None:
            if c.audio_source is not None:
                self.audio_in = FfmpegAudioInput(self.audio, c.audio_source, loop=c.audio_loop, ffmpeg=c.ffmpeg)
            threading.Thread(target=self._sound, daemon=True).start()
        log("ffmpeg cast -> %s:%d from :%d" % (dst_ip, dst_port, server_port))

    def _pts(self):
        return 90000 + int((time.monotonic() - self.t0) * 90000)

    def _feed(self):
        period = 1.0 / self.c.fps
        nxt = time.monotonic()
        while self.running:
            frame = bytes(self.fb)
            with self.lock:
                self.pts.append(self._pts())
            try:
                self.proc.stdin.write(frame)
                self.proc.stdin.flush()
            except (BrokenPipeError, OSError, ValueError):
                break
            nxt += period
            time.sleep(max(0.0, nxt - time.monotonic()))

    def _sound(self):
        """castif's pace_audio and drain_one: one block every 10 ms of wall
        clock, about 60 ms behind the feed; the track's PTS runs on
        contiguously from the newest block's stamp, re-anchors after a gap,
        and drops or pads one block when it drifts past sync_ms from the
        stamps (a microphone's clock is not this computer's)."""
        c, a = self.c, self.audio
        apts = None
        drift = 0.0
        ref = None
        since = 0
        sync = 40 * 90
        nxt = None
        silence = bytes(BLOCK_BYTES)
        while self.running:
            now = time.monotonic()
            if a.waiting() == 0:
                if apts is not None and self._pts() - apts > 18000:
                    c.audio_underruns += 1
                    apts = None             # the producer stopped: start afresh when it comes back
                nxt = None
                time.sleep(0.005)
                continue
            if nxt is None:
                nxt = now + 0.06
            if now - nxt > 0.3:
                nxt = now                   # a long gap: don't burst-chase
            if now < nxt:
                time.sleep(min(0.005, nxt - now))
                continue
            blk = a.take()
            if blk is None:
                continue
            pcm, stamp = blk
            if apts is None and stamp < now - 0.1:
                c.audio_dropped += 1        # written before the session could play it
                continue
            s90 = 90000 + int((stamp - self.t0) * 90000)
            if apts is None:
                apts = s90 - 900 * a.waiting()     # the newest waiting block carries its own stamp
                drift, ref, since = 0.0, None, 0
            d = s90 - apts
            if d - (ref or 0) > REJOIN:
                apts, d, drift, ref, since = s90, 0, 0.0, None, 0
                c.audio_rejoins += 1
            drift += (d - drift) / 64
            c.audio_drift_ms = int(drift / 90)
            if ref is None:
                if since >= 300:
                    ref = drift
            else:
                off = drift - ref
                if off > sync:                      # the sound would play early: pad
                    self._mux_audio(silence, apts)
                    apts += 900
                    drift -= 900
                    c.audio_inserted += 1
                elif off < -sync:                   # it would play late: drop this one
                    drift += 900
                    c.audio_dropped += 1
                    nxt += BLOCK_S
                    continue
            self._mux_audio(pcm, apts)
            apts += 900
            since += 1
            c.audio_muxed += 1
            nxt += BLOCK_S

    def _mux_audio(self, pcm, pts):
        with self.send_lock:
            self._send(self.mux.lpcm(pcm, pts), (self._pts() - PCR_LEAD) & 0xFFFFFFFF)

    def _send(self, packets, ts90=None):
        if ts90 is None:
            ts90 = (self._last_pts - PCR_LEAD) & 0xFFFFFFFF
        for i in range(0, len(packets), 7):
            hdr = bytes([0x80, 33, (self.seq >> 8) & 0xFF, self.seq & 0xFF]) + ts90.to_bytes(4, "big") + b"P4CA"
            try:
                self.sock.sendto(hdr + b"".join(packets[i:i + 7]), self.dst)
                self.c.sent += 1
            except OSError:
                self.c.stalls += 1
            self.seq = (self.seq + 1) & 0xFFFF

    def _au(self, au):
        """One access unit from ffmpeg, starting with its delimiter."""
        # tsmux's PES header carries the delimiter: drop ffmpeg's
        if au.startswith(b"\x00\x00\x00\x01\x09"):
            au = au[6:]
        elif au.startswith(b"\x00\x00\x01\x09"):
            au = au[5:]
        key = False
        i = au.find(b"\x00\x00\x01")
        while i >= 0 and i + 3 < len(au):
            if au[i + 3] & 0x1F == 5:
                key = True
                break
            i = au.find(b"\x00\x00\x01", i + 3)
        with self.lock:
            pts = self.pts.pop(0) if self.pts else self._pts()
        with self.send_lock:
            self._last_pts = pts
            packets = (self.mux.tables() if key else []) + self.mux.video(au, pts, key)
            self._send(packets)
        if self.c._t0 is None:
            self.c._t0 = time.monotonic()
        self.c.frames += 1

    def _read(self):
        buf = b""
        marker = b"\x00\x00\x00\x01\x09"
        while self.running:
            d = self.proc.stdout.read1(65536) if hasattr(self.proc.stdout, "read1") else self.proc.stdout.read(4096)
            if not d:
                break
            buf += d
            # each delimiter after the first starts the next access unit
            while True:
                j = buf.find(marker, 1)
                if j < 0:
                    break
                self._au(buf[:j])
                buf = buf[j:]

    def pump(self, budget_us):
        now = time.monotonic()
        if now - getattr(self, "_beat", 0) > 3:
            self._beat = now
            s = self.c.stats()
            line = "pycast: %d frames, %.1f fps, %d sent, %d stalls" % (s["frames"], s["fps"] / 1000, s["sent"], s["stalls"])
            if self.audio is not None:
                line += " | audio fed %d muxed %d level %d underruns %d drift %d ms ins %d drop %d rejoin %d full %d" % (
                    s["audio_fed"], s["audio_muxed"], s["audio_level"], s["audio_underruns"], s["audio_drift_ms"],
                    s["audio_inserted"], s["audio_dropped"], s["audio_rejoins"], s["audio_full"])
            self.log(line)
        if now - self.t0 > self.seconds:
            self.done = True

    def force_idr(self):
        pass                # a keyframe comes every second regardless

    def close(self):
        self.running = False
        if self.audio_in is not None:
            self.audio_in.close()
        try:
            self.proc.stdin.close()
        except OSError:
            pass
        try:
            self.proc.wait(3)
        except Exception:
            self.proc.kill()
        self.sock.close()
