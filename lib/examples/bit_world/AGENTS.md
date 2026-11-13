# AGENTS.md

- Adding, packaging and checking an example: [docs/guides/add-a-gallery-example.md](../../../docs/guides/add-a-gallery-example.md). The repository's own tips are in the [top-level AGENTS.md](../../../AGENTS.md).
- Every sprite, palette and synth patch here is a `.py` module, because a mip manifest carries no image files. Keep it that way, or the example drops out of the web gallery.
- `bit_world.py` sets an 800x480 window only when `PYDEVICES_WIDTH` is unset, so `tools/screenshot.py --resolution` and your own environment still win.
- `BIT_WORLD_ACT=0`, `1` or `2` starts in the Workshop, Sky Ruins or Cyber-Deck act, which helps for screenshots.
- `bit_sound.py` retries `audio_out.play()` on input and on each music step until it succeeds, because a browser refuses audio until the first click or key press.
- Tick callbacks take the timer argument (`def step(self, timer=None)`). Without it you get a black frame and a single traceback.
- On a board whose panel gives out two scan-out buffers (`display_drv.share_framebuffer` with two entries from `framebuffers()`), the example draws straight into the back buffer and repaints only what moved: each act's `draw_changes` must give the same pixels as its `draw`. After changing an act, run `tools/bit_world_repaint_check.py` (its docstring says how); it compares the two frame by frame.
- Never slice a panel's buffer from Python (`buf[a:b] = ...`): on an ESP32-S3 each row costs milliseconds. Copy rectangles with `FrameBuffer.blit`, as `restore_rects` does.

