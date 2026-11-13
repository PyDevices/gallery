# AGENTS.md

- Adding, packaging and checking an example: [docs/guides/add-a-gallery-example.md](../../../docs/guides/add-a-gallery-example.md). The repository's own tips are in the [top-level AGENTS.md](../../../AGENTS.md).
- Every sprite, palette and synth patch here is a `.py` module, because a mip manifest carries no image files. Keep it that way, or the example drops out of the web gallery.
- `bit_world.py` sets an 800x480 window only when `PYDEVICES_WIDTH` is unset, so `tools/screenshot.py --resolution` and your own environment still win.
- `BIT_WORLD_ACT=0`, `1` or `2` starts in the Workshop, Sky Ruins or Cyber-Deck act, which helps for screenshots.
- `bit_sound.py` retries `audio_out.play()` on input and on each music step until it succeeds, because a browser refuses audio until the first click or key press.
- Tick callbacks take the timer argument (`def step(self, timer=None)`). Without it you get a black frame and a single traceback.
