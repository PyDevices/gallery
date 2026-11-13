# SPDX-FileCopyrightText: 2026 Brad Barnett
#
# SPDX-License-Identifier: MIT

"""Check that Bit World's partial repaint draws the same pixels as a full redraw.

Runs every act for a few hundred frames, drawing each one twice: once from scratch
into a reference frame, and once through draw_changes into one of two alternating
buffers that start out dirty, as a board's panel buffers do. Any differing pixel
is reported with its rows and columns.

Run it from the repository root, naming the Bit World folder on the module path:

    MICROPYPATH=".:lib:lib/examples/bit_world" micropython -X heapsize=96M \
        tools/bit_world_repaint_check.py [width height frames]
"""

import sys
import bit_palette as bp
from bit_palette import Layout, PanelState, make_fb, VOID, init_rng
from bit_sprites import SpriteBank
from bit_sound import SoundEngine
from act_pet import WorkshopAct
from act_game import SkyRuinsAct
from act_deck import CyberDeckAct
from pygraphics import Draw

W = int(sys.argv[1]) if len(sys.argv) > 1 else 800
H = int(sys.argv[2]) if len(sys.argv) > 2 else 480
FRAMES = int(sys.argv[3]) if len(sys.argv) > 3 else 300

class NoAudio:
    pass  # no audio_out, so the sound engine runs silent

lay = Layout(W, H)
sprites = SpriteBank(lay)
snd = SoundEngine(NoAudio, None)
acts = (WorkshopAct(lay, sprites, snd), SkyRuinsAct(lay, sprites, snd), CyberDeckAct(lay, sprites, snd))
ref_buf, ref_fb = make_fb(W, H, VOID)
ref_draw = Draw(ref_fb)
panels = []
for i in range(2):
    b, f = make_fb(W, H, 0x1234)  # start dirty on purpose
    panels.append((b, f, Draw(f), PanelState()))
row = W * 2
y0 = 0
bad = 0
full = 0
fast = 0
for ai, act in enumerate(acts):
    for st in (p[3] for p in panels):
        st.act = -1
    init_rng(7)
    for frame in range(FRAMES):
        auto = frame % 200 < 150
        if frame % 37 == 5:
            if ai == 0:
                act.trigger_action((frame // 37) % 5)
            elif ai == 1:
                act.jump(); act.fire()
            else:
                act.on_pointer_down(*(act.switch_rects[frame % 4][:2]))
                act.on_pointer_down(*(act.pad_rects[frame % 8][:2]))
        if ai == 0:
            act.update_pointer_look(100 + frame * 3 % 600, 100 + frame * 5 % 300)
        act.update(0.033, auto)
        snd.update(0.033, ai, acts[2].state)
        init_rng(frame)
        act.draw(ref_fb, ref_draw)
        b, f, d, st = panels[frame & 1]
        init_rng(frame)
        if frame % 90 == 60:
            st.act = -1  # as after a wipe
        if st.act == ai:
            act.draw_changes(f, d, st)
            fast += 1
        else:
            act.draw(f, d, st)
            st.act = ai
            full += 1
        if bytes(ref_buf[y0:]) != bytes(b[y0:]):
            diff = [i for i in range(y0, len(b)) if ref_buf[i] != b[i]]
            ys = sorted(set(i // row for i in diff))
            xs = sorted(set((i % row) // 2 for i in diff))
            print("MISMATCH act", ai, "frame", frame, "bytes", len(diff), "rows", ys[0], ys[-1], "cols", xs[0], xs[-1])
            bad += 1
            if bad > 5:
                raise SystemExit(1)
print("equiv", W, H, "bad", bad, "full", full, "fast", fast)
