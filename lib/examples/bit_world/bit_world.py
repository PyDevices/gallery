# SPDX-FileCopyrightText: 2026 Brad Barnett
#
# SPDX-License-Identifier: MIT

# gallery: featured, newwindow
# deps: audiodsp, multimer, pygraphics
"""Bit World: three-act interactive pixel-art showcase for pygraphics and synthio.

Follows Bit, a hovering CRT-faced robot companion, across three live scenes
that demonstrate what you can build with pygraphics and synthio:

1. Workshop Companion: expressive desktop pet and smart-home assistant HUD.
2. Sky Ruins: four-layer parallax side-scrolling platformer and jetpack runner.
3. Cyber-Deck: solarpunk reactor HMI with radial gauges, oscilloscope, FFT
   spectrum analyzer, breaker switches, and an 8-pad live synth sequencer.

Plays hands-free in Attract Mode by default; click, tap, or press keys at any
time to take control or switch scenes.

Needs: audiodsp, multimer, pygraphics.

Run it:

    import examples.bit_world

Tested on: unix MicroPython 1.30 (preview), CircuitPython 10.3, CPython 3.12, Chromium via PyScript/MicroPython WASM, and an ESP32-S3 with an 800x480 RGB panel (MicroPython 1.30 preview).
"""

from boarddev import env_get, env_set

# Default to an 800x480 landscape showcase canvas when not overridden by the host.
if env_get("PYDEVICES_WIDTH") is None:
    env_set("PYDEVICES_WIDTH", 800)
    env_set("PYDEVICES_HEIGHT", 480)
if env_get("PYDEVICES_SCALE") is None:
    env_set("PYDEVICES_SCALE", 1.0)

import board_config
import appdev

app = appdev.App(board_config)
import board_peripherals
import keys
from multimer import ticks_diff, ticks_ms

try:
    from uctypes import addressof
except ImportError:
    addressof = None
from pygraphics import Draw, FrameBuffer, RGB565
from bit_palette import (
    ABYSS,
    AMBER,
    AQUA_GLOW,
    CORAL,
    CYAN,
    DEEP_SLATE,
    DEEP_TEAL,
    EMERALD,
    GOLD,
    ICE_CYAN,
    LIME_GLOW,
    MIST,
    NEON_PINK,
    NIGHT,
    SILVER,
    SLATE,
    STEEL,
    VOID,
    WHITE,
    Layout,
    PanelState,
    draw_pixel_panel,
    draw_pixel_wipe,
    init_rng,
    make_fb,
)
from bit_sprites import SpriteBank
from bit_sound import SoundEngine
from act_pet import WorkshopAct
from act_game import SkyRuinsAct
from act_deck import CyberDeckAct

# Change these to match your setup.
FRAME_MS = 33  # Target frame interval in milliseconds (~30 FPS)
PANEL_FRAME_MS = 10  # Frame interval when drawing straight into a board's panel buffers
ACT_DURATION = 16.0  # Seconds per scene in hands-free Attract Mode
WIPE_SPEED = 1.85  # Transition curtain speed (full wipe in ~0.54 seconds)

ACT_TITLES = ("1:WORKSHOP", "2:SKY RUINS", "3:CYBER DECK")
ACT_SHORT = ("1:PET", "2:GAME", "3:HMI")
ACT_ACCENTS = (AQUA_GLOW, LIME_GLOW, GOLD)

display_drv = board_config.display_drv
if display_drv.width < display_drv.height:
    display_drv.rotation = (display_drv.rotation + 90) % 360

WIDTH = display_drv.width
HEIGHT = display_drv.height


class BitWorldDirector:
    """Coordinate the 3 acts, stage bar UI, transitions, input, and audio."""

    def __init__(self):
        init_rng(42)
        self.lay = Layout(WIDTH, HEIGHT)
        # A board whose panel hands out two scan-out buffers is drawn into
        # directly; every other display gets one off-screen frame that is
        # copied across.
        self.panels = {}
        self.direct = self._share_panel_buffers()
        if not self.direct:
            self.screen_buf, self.screen_fb = make_fb(WIDTH, HEIGHT, VOID)
            self.screen_draw = Draw(self.screen_fb)

        self.sprites = SpriteBank(self.lay)
        self.sound = SoundEngine(board_peripherals, app)

        self.act_pet = WorkshopAct(self.lay, self.sprites, self.sound)
        self.act_game = SkyRuinsAct(self.lay, self.sprites, self.sound)
        self.act_deck = CyberDeckAct(self.lay, self.sprites, self.sound)
        self.acts = (self.act_pet, self.act_game, self.act_deck)

        start_act = env_get("BIT_WORLD_ACT")
        self.act_idx = int(start_act) % 3 if start_act is not None else 0
        self.next_act_idx = self.act_idx
        self.auto_mode = True
        self.act_timer = 0.0
        self.wipe_progress = 0.0
        self.pointer_down = False
        self.last_ms = ticks_ms()

        self._compute_bar_geometry()
        self.render_and_present(first_frame=True)

    # Decide whether to draw straight into the panel's two scan-out buffers.
    def _share_panel_buffers(self):
        drv = display_drv
        if addressof is None or not getattr(drv, "share_framebuffer", False):
            return False
        if drv.rotation or getattr(drv, "requires_byteswap", False):
            return False
        if not callable(getattr(drv, "framebuffers", None)):
            return False
        try:
            bufs = drv.framebuffers()
        except Exception:
            return False
        # One buffer would show every half-drawn frame, so it keeps the copy.
        if len(bufs) < 2 or bufs[1] is None or bufs[3] != WIDTH * 2:
            return False
        if len(bufs[0]) < WIDTH * HEIGHT * 2:
            return False
        app.pause_refresh()
        return True

    # The panel's back buffer wrapped for drawing: (FrameBuffer, Draw, PanelState).
    def _back_panel(self):
        buf = display_drv.framebuffers()[0]
        key = addressof(buf)
        panel = self.panels.get(key)
        if panel is None:
            fb = FrameBuffer(buf, WIDTH, HEIGHT, RGB565)
            panel = (fb, Draw(fb), PanelState())
            self.panels[key] = panel
        return panel

    # Compute top stage bar tab and button hit rectangles for the active screen width.
    def _compute_bar_geometry(self):
        w = self.lay.w
        bh = self.lay.bar_h
        pad = self.lay.pad
        btn_y = 3 if self.lay.compact else 4
        btn_h = bh - btn_y * 2

        # Reserve space on the left for the brand badge when width >= 600.
        self.brand_w = 0 if self.lay.compact else 108
        right_w = (62 if self.lay.compact else 82) * 2 + pad
        tabs_x0 = pad + self.brand_w
        tabs_avail = w - tabs_x0 - right_w - pad * 2
        gap = 4 if self.lay.compact else 6
        tab_w = (tabs_avail - gap * 2) // 3

        self.tab_rects = []
        for i in range(3):
            tx = tabs_x0 + i * (tab_w + gap)
            self.tab_rects.append((tx, btn_y, tab_w, btn_h))

        mode_w = 58 if self.lay.compact else 78
        snd_w = 58 if self.lay.compact else 78
        snd_x = w - pad - snd_w
        mode_x = snd_x - gap - mode_w
        self.rect_mode = (mode_x, btn_y, mode_w, btn_h)
        self.rect_sound = (snd_x, btn_y, snd_w, btn_h)

    # Initiate a Bayer pixel-curtain wipe transition to target_idx.
    def start_transition(self, target_idx):
        target_idx = target_idx % len(self.acts)
        if target_idx == self.act_idx and self.wipe_progress == 0.0:
            self.act_timer = 0.0
            return
        self.next_act_idx = target_idx
        if self.wipe_progress == 0.0:
            self.wipe_progress = 0.02
        self.sound.sfx_switch(True)

    # Advance active scene simulation, transitions, and procedural soundtrack.
    def step(self, _timer=None):
        if app.quit_requested:
            return
        now = ticks_ms()
        dt = ticks_diff(now, self.last_ms) / 1000.0
        self.last_ms = now
        if dt <= 0.0:
            dt = 0.016
        elif dt > 0.10:
            dt = 0.10

        # Advance attract-mode scene cycle timer when no wipe is active.
        if self.auto_mode and self.wipe_progress == 0.0:
            self.act_timer += dt
            if self.act_timer >= ACT_DURATION:
                self.act_timer = 0.0
                self.start_transition((self.act_idx + 1) % len(self.acts))

        # Advance the pixel curtain wipe and swap acts at midpoint (0.5).
        if self.wipe_progress > 0.0:
            prev = self.wipe_progress
            self.wipe_progress += dt * WIPE_SPEED
            if prev < 0.5 <= self.wipe_progress:
                self.act_idx = self.next_act_idx
                self.act_timer = 0.0
            if self.wipe_progress >= 1.0:
                self.wipe_progress = 0.0

        self.acts[self.act_idx].update(dt, self.auto_mode)
        self.sound.update(dt, self.act_idx, self.act_deck.state)
        self.render_and_present(first_frame=False)

    # Render the active act, transition curtain, and top stage bar, then blit to display.
    def render_and_present(self, first_frame=False):
        act = self.acts[self.act_idx]
        if self.direct:
            fb, draw, state = self._back_panel()
            if state.act == self.act_idx and self.wipe_progress == 0.0:
                # This buffer already shows the act: repaint what changed.
                act.draw_changes(fb, draw, state)
            else:
                act.draw(fb, draw, state)
                state.bar = None  # the full redraw painted over the stage bar
                # A buffer that gets a curtain wipe no longer shows its act.
                state.act = self.act_idx if self.wipe_progress == 0.0 else -1
        else:
            fb = self.screen_fb
            act.draw(fb, self.screen_draw)

        if self.wipe_progress > 0.0:
            accent = ACT_ACCENTS[self.next_act_idx]
            draw_pixel_wipe(
                fb,
                0,
                self.lay.scene_y,
                self.lay.w,
                self.lay.scene_h,
                self.wipe_progress,
                VOID,
                accent,
            )

        if self.direct:
            # The stage bar only changes when a tab, a toggle or the progress line does.
            bar = (self.act_idx, self.auto_mode, self.sound.muted, self._bar_progress())
            if state.bar != bar or self.wipe_progress > 0.0:
                self._draw_stage_bar(fb)
                state.bar = bar if self.wipe_progress == 0.0 else None
        else:
            self._draw_stage_bar(fb)
        if self.direct:
            # Promote the finished frame; the next frame waits for the flip.
            if hasattr(display_drv, "show_nowait"):
                display_drv.show_nowait()
            else:
                display_drv.show()
            return
        display_drv.blit_rect(self.screen_buf, 0, 0, WIDTH, HEIGHT)
        if first_frame:
            display_drv.show()

    # Width in pixels of the attract-mode progress line on the active tab.
    def _bar_progress(self):
        if not self.auto_mode:
            return 0
        tab_w = self.tab_rects[self.act_idx][2]
        return int((tab_w - 6) * min(1.0, self.act_timer / ACT_DURATION))

    # Draw the top navigation bar with act tabs, attract-mode progress, and toggles.
    def _draw_stage_bar(self, fb):
        w = self.lay.w
        bh = self.lay.bar_h
        fb.fill_rect(0, 0, w, bh, VOID)
        fb.hline(0, bh - 1, w, STEEL)

        if not self.lay.compact:
            fb.text16("BIT WORLD", self.lay.pad, (bh - 16) >> 1, GOLD)

        # Render the 3 scene selector tabs.
        titles = ACT_SHORT if self.lay.compact else ACT_TITLES
        for i, (tx, ty, tw, th) in enumerate(self.tab_rects):
            active = i == self.act_idx
            accent = ACT_ACCENTS[i]
            bg = DEEP_TEAL if active else NIGHT
            border = accent if active else SLATE
            draw_pixel_panel(fb, tx, ty, tw, th, bg, border, WHITE if active else None)
            lbl = titles[i]
            lx = tx + ((tw - len(lbl) * 8) >> 1)
            ly = ty + ((th - 8) >> 1) - (1 if active and self.auto_mode else 0)
            fb.text(lbl, lx, ly, WHITE if active else SILVER)

            # Draw a live progress bar along the bottom of the active tab in AUTO mode.
            if active and self.auto_mode:
                prog_w = int((tw - 6) * min(1.0, self.act_timer / ACT_DURATION))
                if prog_w > 0:
                    fb.hline(tx + 3, ty + th - 3, prog_w, accent)

        # Render the AUTO / MANUAL mode button.
        mx, my, mw, mh = self.rect_mode
        m_col = LIME_GLOW if self.auto_mode else AMBER
        draw_pixel_panel(fb, mx, my, mw, mh, NIGHT, m_col)
        m_txt = "AUTO" if self.auto_mode else ("MAN" if self.lay.compact else "MANUAL")
        fb.text(m_txt, mx + ((mw - len(m_txt) * 8) >> 1), my + ((mh - 8) >> 1), m_col)

        # Render the SOUND / MUTE status button.
        sx, sy, sw, sh = self.rect_sound
        s_on = not self.sound.muted
        s_col = AQUA_GLOW if s_on else CORAL
        draw_pixel_panel(fb, sx, sy, sw, sh, NIGHT, s_col)
        if self.lay.compact:
            s_txt = "SND" if s_on else "MUTE"
        else:
            s_txt = "SND:ON" if s_on else "MUTED"
        fb.text(s_txt, sx + ((sw - len(s_txt) * 8) >> 1), sy + ((sh - 8) >> 1), s_col)

    # Route pointer press events to the top stage bar or active scene.
    def on_pointer_down(self, x, y):
        self.pointer_down = True
        self.sound.try_unlock()

        # Check top stage bar buttons first.
        if y < self.lay.bar_h:
            for i, (tx, ty, tw, th) in enumerate(self.tab_rects):
                if tx <= x < tx + tw and ty <= y < ty + th:
                    self.start_transition(i)
                    return
            mx, my, mw, mh = self.rect_mode
            if mx <= x < mx + mw and my <= y < my + mh:
                self.auto_mode = not self.auto_mode
                self.act_timer = 0.0
                self.sound.sfx_switch(self.auto_mode)
                return
            sx, sy, sw, sh = self.rect_sound
            if sx <= x < sx + sw and sy <= y < sy + sh:
                self.sound.toggle_mute()
                return
            return

        # Clicking inside the scene engages manual control for the current act.
        self.auto_mode = False
        self.act_timer = 0.0
        self.acts[self.act_idx].on_pointer_down(x, y)

    # Route pointer motion events (for Bit eye tracking and Cyber-Deck fader drag).
    def on_pointer_move(self, x, y):
        if self.act_idx == 0:
            self.act_pet.update_pointer_look(x, y)
        elif self.act_idx == 2 and self.pointer_down and y >= self.lay.bar_h:
            self.act_deck.on_pointer_down(x, y, is_drag=True)

    # Record pointer release.
    def on_pointer_up(self):
        self.pointer_down = False

    # Route keyboard shortcuts across all 3 acts.
    def on_key_down(self, key):
        self.sound.try_unlock()
        if key == keys.K_1:
            self.start_transition(0)
        elif key == keys.K_2:
            self.start_transition(1)
        elif key == keys.K_3:
            self.start_transition(2)
        elif key in (keys.K_a, keys.K_TAB):
            self.auto_mode = not self.auto_mode
            self.act_timer = 0.0
            self.sound.sfx_switch(self.auto_mode)
        elif key == keys.K_m:
            self.sound.toggle_mute()
        elif key in (keys.K_SPACE, keys.K_UP, keys.K_w):
            self.auto_mode = False
            if self.act_idx == 0:
                self.act_pet.trigger_action((self.act_pet.active_btn + 1) % 5)
            elif self.act_idx == 1:
                self.act_game.jump()
            else:
                self.act_deck.switches[0] = not self.act_deck.switches[0]
                self.act_deck._sync_state()
                self.sound.sfx_switch(self.act_deck.switches[0])
        elif key in (keys.K_f, keys.K_RETURN, keys.K_RIGHT):
            self.auto_mode = False
            if self.act_idx == 0:
                self.act_pet.trigger_action(2)
            elif self.act_idx == 1:
                self.act_game.fire()
            else:
                self.act_deck.switches[3] = not self.act_deck.switches[3]
                self.act_deck._sync_state()
                self.sound.sfx_switch(self.act_deck.switches[3])


director = BitWorldDirector()


# Periodic timer callback to unlock browser audio after the user's first gesture.
def _retry_audio(_timer=None):
    if not director.sound.ready:
        director.sound.try_unlock()


# Handle mouse button press and release events.
def _on_mouse_button(e):
    if app.quit_requested:
        return
    if e.type == app.events.MOUSEBUTTONDOWN:
        director.on_pointer_down(e.pos[0], e.pos[1])
    else:
        director.on_pointer_up()


# Handle mouse motion events.
def _on_mouse_motion(e):
    if app.quit_requested:
        return
    director.on_pointer_move(e.pos[0], e.pos[1])


# Handle keyboard press events.
def _on_key(e):
    if app.quit_requested:
        return
    if e.type == app.events.KEYDOWN:
        director.on_key_down(e.key)


# Cleanly shut down audio and display drivers when the app exits.
def _on_quit(_e=None):
    director.sound.close()
    display_drv.quit()


# A board that draws straight into its panel buffers cannot keep up with FRAME_MS, and a
# timer whose frames overrun its period only fires on every second or third slot, so it
# gets a short period and runs frames back to back.
frame_timer = app.every(PANEL_FRAME_MS if director.direct else FRAME_MS, director.step)
# After a frame that runs longer than its period, multimer idles the timer for as long as
# the frame took (up to yield_cap ms), which halves the frame rate of a slow board.
# Idle only briefly: other timers and the REPL still get their turn between frames.
if hasattr(frame_timer, "yield_cap"):
    frame_timer.yield_cap = 8
app.every(250, _retry_audio)
app.on([app.events.MOUSEBUTTONDOWN, app.events.MOUSEBUTTONUP], _on_mouse_button)
app.on(app.events.MOUSEMOTION, _on_mouse_motion)
app.on(app.events.KEYDOWN, _on_key)
app.on(app.events.QUIT, _on_quit)
