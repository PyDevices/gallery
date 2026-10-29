"""Run a PyDevices example on a Roku TV, with the TV's remote as its keyboard.

Put this folder first on the path and run the example, e.g. testris.py.
"""

from utils.roku_companion import RokuAudioSink, RokuCompanion, RokuDisplay, roku_host

# PyDevices 0.7.7 and later: tell AutoDisplay this display is wanted, so an app
# that calls AutoDisplay(...) under this config gets it. Earlier releases have
# no registry, and the display built below is all there is.
try:
    import backends
except ImportError:
    pass
else:
    backends.require("display", "roku", module="utils.roku_companion")

WIDTH = 480
HEIGHT = 270

# Connect to the Roku TV
tv = RokuCompanion(roku_host())

display_drv = RokuDisplay(tv, width=WIDTH, height=HEIGHT, port=8090)

# appdev.App(board_config) reads input from here: the remote's buttons.
get_events = display_drv.get_events

# Other stubs that PyDevices examples sometimes expect from board_config
has_touch = False
touch_drv = None
audio_drv = None
is_rotated = False

# An app's sound on the TV's speakers too. Off by default: the Companion
# channel shows sound or the picture, not both, so the picture gives way to
# "Streaming Audio...", and the sound runs 3.5 to 5.5 seconds behind the app.
# For sound with the picture, use ../miracast/board_config.py.
SOUND_ON_TV = False

if SOUND_ON_TV:
    import audiodev.auto

    def roku_pcm_out(format=None, **kwargs):
        return RokuAudioSink(tv, format=format)

    audiodev.auto.pcm_out = roku_pcm_out
