# SPDX-FileCopyrightText: 2026 Brad Barnett
#
# SPDX-License-Identifier: MIT
"""Watch a medialink camera on a TV, with its sound.

This finds a medialink camera on the network by name and casts what it
sees and hears to a TV over Miracast: a Roku TV with Screen mirroring on,
or a Windows PC's Wireless Display app. The TV is the screen and the
speaker, so the board running this needs no display of its own. Every few
seconds it prints how many pictures it showed and how the sound is going.

The camera side is pydevices' medialink surveillance camera example, run
with CAMERA = True on a board with a camera, or on a computer with a
folder of JPEG files. Set its RATE to 24000 to match this one: on a board
the cast carries what the board's speaker plays, and reads it at 24 or
48 kHz. Set its FPS to 5 as well. Sound comes first: an ESP32-P4 decodes
and shows a 640x480 picture in about 80 ms, so it keeps up with 5 a second
and still has time for the sound, where at 10 a second it shows about 6
and drops packets. The cast itself runs at FPS, 10 frames a second, since
it sends a frame only when the picture changes; capping it at 30, 15 or
10 made no difference to the sound.

Needs: on a board, an ESP32-P4 with firmware that carries castif, h264enc
and the audio pump, and Wi-Fi; on a computer, CPython with ffmpeg on the
path. Both need pydevices' medialink and audiodev, and jpegio (built into
the firmware, or Pillow on CPython). The Roku TV needs Screen mirroring
on; Windows needs its Wireless Display app open, on another computer than
the one running this.

Run it on the board, beside the cast example's files:

    import cast.medialink_tv

or on a computer:

    python lib/examples/cast/medialink_tv.py

Tested on: CPython 3.12 on Linux and Windows to a Roku TV, and a Waveshare
ESP32-P4 panel on MicroPython 1.30 preview to a Roku TV and to Windows
Wireless Display, with a computer's folder of JPEG files as the camera.
"""

import sys

import medialink
import multimer
from audiodev import AudioFormat
from cast_display import CastDisplay

# Change these to match your setup.
TV = "roku:192.168.1.129"  # "roku:ADDRESS" for a Roku TV, "windows:ADDRESS" for Wireless Display
CAMERA_NAME = "porch-camera"  # the camera side's name on the network
CAMERA_ADDRESS = None  # or ("192.168.1.20", PORT) to skip the search
PORT = 47800
WIDTH, HEIGHT = 640, 480  # the cast's picture; the TV scales it to fit
FPS = 10  # the cast's frames a second, at most; it sends only when a picture changes
RATE = 24000  # sound samples a second: 24000 or 48000, the same as the camera's
SPEAKER_VOLUME = 0  # a board's own speaker, 0 to 100; the TV has its own volume

# Start the cast. It joins the TV in the background and rejoins by itself
# if the TV goes away.
kind, address = TV.split(":", 1)
if sys.implementation.name != "cpython":
    from _common import wifi_up

    wifi_up()
display = CastDisplay(address, WIDTH, HEIGHT, kind=kind, name="Porch camera", fps=FPS,
                      audio=True, audio_format=(RATE, 2))

# The speaker whose sound goes out with the picture. On a board it is the
# board's own speaker too, at SPEAKER_VOLUME.
audio = AudioFormat(RATE, 1, 16)
speaker = display.pcm_out(audio, speaker_volume=SPEAKER_VOLUME)

# Open the link, with pictures and sound coming in.
link = medialink.Link(medialink.UDPTransport(PORT), retries=2)
video = medialink.Video(link)
screen = medialink.Screen(display)
intercom = medialink.Intercom(link, None, speaker)
finder = medialink.MDNS()
print("Casting to %s, looking for %r" % (TV, CAMERA_NAME))


def look_for_camera():
    """Find the camera by name and say hello to it."""
    found = [(CAMERA_NAME, CAMERA_ADDRESS)] if CAMERA_ADDRESS else finder.find(CAMERA_NAME, timeout=1)
    for _name, where in found:
        try:
            link.connect(where)
            print("Watching %r at %s" % (CAMERA_NAME, where))
        except medialink.PeerUnreachable:
            pass


# Show each picture on the TV and play the sound, until stopped.
looked = reported = multimer.ticks_ms() - 3000
counted = 0
try:
    while True:
        now = multimer.ticks_ms()
        if not link.alive and multimer.ticks_diff(now, looked) > 3000:
            look_for_camera()
            looked = multimer.ticks_ms()
        frame = video.receive()
        if frame is not None:
            screen.show(frame.payload)
            display.show()
        intercom.service()

        # Every five seconds, say how it is going.
        if multimer.ticks_diff(now, reported) >= 5000:
            total = video.stats["received"]
            rate = (total - counted) * 1000 / multimer.ticks_diff(now, reported)
            cast = display.stats()
            print("%d pictures shown, %.1f a second; sound %s ms late, %d underruns; cast %.0f fps, %d sessions"
                  % (total, rate, intercom.stats["latency_ms"], intercom.stats["underruns"], cast["fps"],
                     cast["sessions"]))
            counted, reported = total, now
        multimer.sleep_ms(1)
finally:
    intercom.close()
    link.close()
    finder.deinit()
    display.close()
