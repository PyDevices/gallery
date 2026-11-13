# SPDX-FileCopyrightText: 2026 Brad Barnett
#
# SPDX-License-Identifier: MIT

"""Act 2: Bioluminescent Sky Ruins (Parallax 2D Game Engine Showcase).

Demonstrates a 4-layer parallax scrolling action-platformer built entirely with
pygraphics FrameBuffer blits and primitives, featuring jetpack physics,
animated crystal pickups, patrol drones, plasma bolts, particle bursts, floating
score popups, and a seamless attract-mode autopilot.

Needs: pygraphics, bit_palette, bit_sprites.

Run it:

    import act_game

Tested on: unix MicroPython 1.30 (preview), CircuitPython 10.3, and CPython 3.12.
"""

from bit_palette import (
    ABYSS,
    ABYSS_RGB,
    AMBER,
    AQUA_GLOW,
    BRONZE,
    CORAL,
    CREAM,
    CYAN,
    DARK_MOSS,
    DEEP_SLATE,
    DEEP_TEAL,
    EMERALD,
    FOREST,
    GOLD,
    ICE_CYAN,
    LIME_GLOW,
    MAGENTA,
    MIST,
    MOSS,
    NEON_PINK,
    NIGHT,
    NIGHT_RGB,
    ORANGE,
    SILVER,
    SLATE,
    STEEL,
    SUN_YELLOW,
    TEAL,
    VOID,
    VOID_RGB,
    WHITE,
    draw_pixel_panel,
    isin,
    make_fb,
    paint_gradient,
    restore_rects,
    rng_int,
)


class SkyRuinsAct:
    """Render and simulate Act 2: Bioluminescent Sky Ruins 2D Action Game."""

    def __init__(self, layout, sprites, sound):
        self.lay = layout
        self.sprites = sprites
        self.sound = sound
        self.phase = 0
        self.scroll_x = 0.0
        self.scroll_speed = 135.0 if not layout.compact else 95.0

        w = layout.w
        sy = layout.scene_y
        sh = layout.scene_h
        self.ground_y = sy + sh - (42 if layout.compact else 56)
        self.hud_y = sy + 6
        self.hud_h = 22 if layout.compact else 26

        # Hero physics state.
        self.hero_x = int(w * 0.20)
        self.hero_y = float(self.ground_y - sprites.bit_game_r.h)
        self.hero_vy = 0.0
        self.on_ground = True
        self.jet_cooldown = 0.0
        self.fire_cooldown = 0.0

        # Arcade score, crystal count, combo multiplier, and screen shake.
        self.score = 1250
        self.crystals_collected = 12
        self.combo = 1
        self.combo_timer = 0.0
        self.shake_timer = 0.0

        # Touch/mouse virtual arcade button rectangles at bottom corners.
        btn_w = 104 if layout.compact else 136
        btn_h = 24 if layout.compact else 30
        btn_y = sy + sh - btn_h - 6
        self.btn_jump = (layout.pad, btn_y, btn_w, btn_h)
        self.btn_fire = (w - layout.pad - btn_w, btn_y, btn_w, btn_h)

        # World entities: platforms, crystals, drones, bolts, particles, popups.
        self.platforms = []
        self.crystals = []
        self.drones = []
        self.bolts = []
        self.particles = []
        self.popups = []
        self._seed_world()

        # Pre-render the sky gradient, ringed planet, and distant stars into sky_fb.
        self.sky_buf, self.sky_fb = make_fb(w, layout.h, VOID)
        self._build_sky_backdrop()

    # Populate initial platforms, crystals, and patrol drones across the screen.
    def _seed_world(self):
        w = self.lay.w
        step = int(w * 0.36)
        for i in range(4):
            px = int(w * 0.25) + i * step
            pw = 88 if self.lay.compact else 128
            py = self.ground_y - (52 if (i & 1) == 0 else 86)
            if self.lay.compact:
                py = self.ground_y - (40 if (i & 1) == 0 else 66)
            self.platforms.append([float(px), py, pw])
            self.crystals.append([float(px + (pw >> 1)), float(py - 24), True])
        for i in range(2):
            dx = int(w * 0.55) + i * int(w * 0.48)
            dy = self.ground_y - (38 if i == 0 else 74)
            self.drones.append([float(dx), float(dy), i * 64])

    # Pre-render the twilight sky gradient, starfield, and ringed solarpunk moon.
    def _build_sky_backdrop(self):
        fb = self.sky_fb
        lay = self.lay
        w = lay.w
        sy = lay.scene_y
        sky_h = self.ground_y - sy

        paint_gradient(fb, 0, sy, w, sky_h, VOID_RGB, NIGHT_RGB, step=3)
        paint_gradient(
            fb,
            0,
            sy + (sky_h >> 1),
            w,
            sky_h - (sky_h >> 1),
            NIGHT_RGB,
            (14, 58, 74),
            step=3,
        )

        # Draw fixed background stars.
        for i in range(36):
            sx = (i * 73 + 19) % w
            sy_star = sy + 28 + ((i * 41 + 11) % max(16, int(sky_h * 0.55)))
            col = WHITE if (i % 5) == 0 else (AQUA_GLOW if (i & 1) else STEEL)
            fb.pixel(sx, sy_star, col)

        # Draw a large ringed planet/moon in the upper right sky.
        px = int(w * 0.78)
        py = sy + int(sky_h * 0.28)
        pr = 22 if lay.compact else 32
        fb.ellipse(px, py, pr * 2, pr >> 2, TEAL, False)
        fb.ellipse(px, py, pr, pr, GOLD, True)
        fb.ellipse(px - (pr >> 2), py - (pr >> 3), pr - 3, pr - 3, SUN_YELLOW, True)
        fb.ellipse(px + (pr >> 2), py + 2, pr - 4, pr - 4, NIGHT, True)
        fb.ellipse(px, py, pr * 2 + 2, (pr >> 2) + 1, AQUA_GLOW, False)

    # Trigger a hero jump or mid-air jetpack thrust.
    def jump(self):
        hero_h = self.sprites.bit_game_r.h
        if self.on_ground:
            self.hero_vy = -7.6 if self.lay.compact else -9.4
            self.on_ground = False
            self.sound.sfx_jump()
            self._spawn_jet_particles(6)
        elif self.jet_cooldown <= 0.0 and self.hero_y > self.lay.scene_y + 42:
            self.hero_vy = max(-8.2, self.hero_vy - (5.2 if self.lay.compact else 6.4))
            self.jet_cooldown = 0.18
            self.sound.sfx_jump()
            self._spawn_jet_particles(5)

    # Fire a glowing plasma bolt from Bit's emitter.
    def fire(self):
        if self.fire_cooldown > 0.0 or len(self.bolts) >= 5:
            return
        self.fire_cooldown = 0.22
        hero = self.sprites.bit_game_r
        bx = float(self.hero_x + hero.w - 4)
        by = float(int(self.hero_y) + (hero.h >> 1) - (self.sprites.bolt.h >> 1))
        self.bolts.append([bx, by])
        self.sound.sfx_laser()

    # Spawn glowing thruster exhaust particles beneath Bit.
    def _spawn_jet_particles(self, count=4):
        hero = self.sprites.bit_game_r
        cx = self.hero_x + (hero.w >> 1)
        cy = int(self.hero_y) + hero.h - 4
        for _ in range(count):
            vx = -2.2 - rng_int(0, 15) * 0.1
            vy = 1.0 + rng_int(0, 15) * 0.15
            col = AQUA_GLOW if rng_int(0, 1) else GOLD
            self.particles.append([float(cx), float(cy), vx, vy, col, 0.45])

    # Spawn a radial pixel burst when a crystal is collected or a drone explodes.
    def _spawn_burst(self, cx, cy, colors, count=10):
        for i in range(count):
            ang = (i * 256) // count
            vx = (isin(ang + 64) * 4.2) / 1024.0
            vy = (isin(ang) * 4.2) / 1024.0 - 0.8
            col = colors[i % len(colors)]
            self.particles.append([float(cx), float(cy), vx, vy, col, 0.55])
        if len(self.particles) > 36:
            self.particles = self.particles[-36:]

    # Spawn a rising pixel text popup (e.g. "+100" or "BOOM +250").
    def _spawn_popup(self, x, y, text, col=GOLD):
        self.popups.append([float(x), float(y), text, col, 0.75])
        if len(self.popups) > 6:
            self.popups = self.popups[-6:]

    # Handle pointer down inside the Sky Ruins scene;Left side jumps, Right side fires.
    def on_pointer_down(self, x, y):
        jx, jy, jw, jh = self.btn_jump
        fx, fy, fw, fh = self.btn_fire
        if jx <= x < jx + jw and jy <= y < jy + jh:
            self.jump()
            return True
        if fx <= x < fx + fw and fy <= y < fy + fh:
            self.fire()
            return True
        if x < (self.lay.w >> 1):
            self.jump()
        else:
            self.fire()
        return True

    # Advance scrolling world, hero physics, collisions, and attract-mode AI.
    def update(self, dt, auto_mode=True):
        if dt <= 0.0:
            dt = 0.016
        elif dt > 0.08:
            dt = 0.08

        self.phase = (self.phase + 6) & 0xFF
        dx = self.scroll_speed * dt
        self.scroll_x += dx
        self.jet_cooldown = max(0.0, self.jet_cooldown - dt)
        self.fire_cooldown = max(0.0, self.fire_cooldown - dt)
        self.shake_timer = max(0.0, self.shake_timer - dt)

        if self.combo_timer > 0.0:
            self.combo_timer -= dt
            if self.combo_timer <= 0.0:
                self.combo = 1

        # Attract-mode AI autopilot: aim for crystals, jump gaps, and blast drones.
        if auto_mode:
            self._run_autopilot()

        # Hero vertical gravity and ground/platform landing.
        hero_w = self.sprites.bit_game_r.w
        hero_h = self.sprites.bit_game_r.h
        prev_bottom = self.hero_y + hero_h
        self.hero_y += self.hero_vy
        self.hero_vy += 0.46 if self.lay.compact else 0.56
        self.on_ground = False

        # Check landing on elevated rune platforms when descending.
        if self.hero_vy >= 0.0:
            new_bottom = self.hero_y + hero_h
            for plat in self.platforms:
                px, py, pw = plat
                if (
                    self.hero_x + hero_w - 6 > px
                    and self.hero_x + 6 < px + pw
                    and prev_bottom <= py + 8
                    and new_bottom >= py
                ):
                    self.hero_y = float(py - hero_h)
                    self.hero_vy = 0.0
                    self.on_ground = True
                    break

        # Check landing on main mossy ruin floor.
        if self.hero_y + hero_h >= self.ground_y:
            self.hero_y = float(self.ground_y - hero_h)
            self.hero_vy = 0.0
            self.on_ground = True

        # Emit subtle jetpack trail while airborne.
        if not self.on_ground and (self.phase & 12) == 0:
            self._spawn_jet_particles(1)

        # Scroll platforms and recycle off-screen ones on the right.
        w = self.lay.w
        for plat in self.platforms:
            plat[0] -= dx
            if plat[0] + plat[2] < -20:
                plat[0] = float(w + rng_int(20, 80))
                plat[1] = self.ground_y - rng_int(
                    38 if self.lay.compact else 50,
                    68 if self.lay.compact else 92,
                )
                self.crystals.append(
                    [plat[0] + (plat[2] >> 1), float(plat[1] - 24), True]
                )

        # Scroll crystals and test hero pickup collisions.
        crys_w = self.sprites.crystals[0].w
        crys_h = self.sprites.crystals[0].h
        i = len(self.crystals) - 1
        while i >= 0:
            c = self.crystals[i]
            c[0] -= dx
            if c[0] < -30 or not c[2]:
                self.crystals.pop(i)
            elif (
                abs(int(c[0]) - (self.hero_x + (hero_w >> 1))) < (hero_w >> 1) + (crys_w >> 1)
                and abs(int(c[1]) - (int(self.hero_y) + (hero_h >> 1))) < (hero_h >> 1) + (crys_h >> 1)
            ):
                c[2] = False
                pts = 100 * self.combo
                self.score += pts
                self.crystals_collected += 1
                self.combo = min(8, self.combo + 1)
                self.combo_timer = 3.2
                self.sound.sfx_crystal()
                self._spawn_burst(c[0], c[1], (AQUA_GLOW, ICE_CYAN, NEON_PINK, GOLD), 8)
                self._spawn_popup(c[0], c[1] - 8, f"+{pts}", AQUA_GLOW)
                self.crystals.pop(i)
            i -= 1

        # Scroll sentinel drones and test plasma bolt & hero collisions.
        drone_w = self.sprites.drones[0].w
        drone_h = self.sprites.drones[0].h
        for d in self.drones:
            d[0] -= dx * 1.18
            d[2] = (d[2] + 5) & 0xFF
            if d[0] < -40:
                d[0] = float(w + rng_int(40, 140))
                d[1] = float(
                    self.ground_y
                    - rng_int(32 if self.lay.compact else 40, 74 if self.lay.compact else 96)
                )

        # Advance plasma bolts and check drone hits.
        bi = len(self.bolts) - 1
        while bi >= 0:
            b = self.bolts[bi]
            b[0] += (290.0 if not self.lay.compact else 220.0) * dt
            hit = False
            for d in self.drones:
                dy_bob = d[1] + ((isin(d[2]) * 8) >> 10)
                if (
                    b[0] + self.sprites.bolt.w >= d[0]
                    and b[0] <= d[0] + drone_w
                    and b[1] + self.sprites.bolt.h >= dy_bob
                    and b[1] <= dy_bob + drone_h
                ):
                    hit = True
                    pts = 250 * self.combo
                    self.score += pts
                    self.combo = min(8, self.combo + 1)
                    self.combo_timer = 3.2
                    self.shake_timer = 0.14
                    self.sound.sfx_boom()
                    self._spawn_burst(
                        d[0] + (drone_w >> 1),
                        dy_bob + (drone_h >> 1),
                        (CORAL, ORANGE, GOLD, WHITE),
                        12,
                    )
                    self._spawn_popup(d[0], dy_bob - 6, f"BOOM +{pts}", GOLD)
                    d[0] = float(w + rng_int(60, 160))
                    break
            if hit or b[0] > w + 20:
                self.bolts.pop(bi)
            bi -= 1

        # Update particles and floating score popups.
        pi = len(self.particles) - 1
        while pi >= 0:
            p = self.particles[pi]
            p[0] += p[2]
            p[1] += p[3]
            p[5] -= dt
            if p[5] <= 0.0:
                self.particles.pop(pi)
            pi -= 1

        ui = len(self.popups) - 1
        while ui >= 0:
            pop = self.popups[ui]
            pop[1] -= 28.0 * dt
            pop[4] -= dt
            if pop[4] <= 0.0:
                self.popups.pop(ui)
            ui -= 1

    # Steer Bit automatically in attract mode to collect crystals and blast drones.
    def _run_autopilot(self):
        hero_h = self.sprites.bit_game_r.h
        hero_cy = self.hero_y + (hero_h >> 1)

        # Fire at any drone in front of Bit on a similar vertical band.
        for d in self.drones:
            dist_x = d[0] - self.hero_x
            if 24 < dist_x < self.lay.w * 0.68:
                if abs((d[1] + 12) - hero_cy) < 28:
                    self.fire()
                elif dist_x < 95 and d[1] > self.hero_y - 18:
                    self.jump()

        # Jump toward upcoming elevated crystals.
        for c in self.crystals:
            dist_x = c[0] - self.hero_x
            if 16 < dist_x < 110 and c[1] < self.hero_y - 10:
                self.jump()
                break

    # Render all 4 parallax layers, sprites, particles, and arcade HUD.
    def draw(self, fb, draw_obj=None, st=None):
        fb.blit(self.sky_fb, 0, 0)
        self._draw_scene(fb)
        if st is not None:
            st.sig = {}

    # Repaint the scene down to the foreground floor, which paints itself in full.
    def draw_changes(self, fb, draw_obj, st):
        lay = self.lay
        top = lay.scene_y
        restore_rects(
            fb,
            self.sky_buf,
            [(0, top, lay.w, self.ground_y + 3 - top)],
            lay.w,
            lay.h,
        )
        self._draw_scene(fb)

    # Paint every parallax layer, entity and HUD element over the sky.
    def _draw_scene(self, fb):
        shake_y = rng_int(-2, 2) if self.shake_timer > 0.0 else 0

        self._draw_sky_islands(fb, shake_y)
        self._draw_far_citadel(fb, shake_y)
        self._draw_mid_ruins(fb, shake_y)
        self._draw_foreground_ground(fb, shake_y)
        self._draw_platforms_and_entities(fb, shake_y)
        self._draw_hud(fb)

    # Draw Layer 0.5 (0.10x speed): Floating solarpunk sky islands with waterfalls.
    def _draw_sky_islands(self, fb, shake_y):
        w = self.lay.w
        span = 220 if self.lay.compact else 310
        offs = int(self.scroll_x * 0.10) % span
        x = -offs + 28
        idx = int(self.scroll_x * 0.10) // span
        while x < w + span:
            iy = self.lay.scene_y + (56 if self.lay.compact else 78) + ((idx * 19) % 28) + shake_y
            iw = 56 if self.lay.compact else 84
            # Mossy island cap and tapered floating rock spire below.
            fb.fill_rect(x, iy, iw, 6, MOSS)
            fb.hline(x + 2, iy, iw - 4, LIME_GLOW)
            fb.fill_rect(x + 6, iy + 6, iw - 12, 8, SLATE)
            fb.fill_rect(x + 16, iy + 14, iw - 32, 8, DEEP_SLATE)
            # Ancient obelisk and cascading bioluminescent waterfall.
            ox = x + (iw >> 1) - 4
            fb.fill_rect(ox, iy - 16, 8, 16, STEEL)
            fb.pixel(ox + 4, iy - 19, AQUA_GLOW)
            fall_h = 22 + ((idx * 7) % 12)
            fb.vline(ox + 2, iy + 6, fall_h, CYAN)
            fb.vline(ox + 3, iy + 6, fall_h, AQUA_GLOW)
            x += span
            idx += 1

    # Draw Layer 1 (0.22x speed): Distant silhouetted solarpunk spires and bio-domes.
    def _draw_far_citadel(self, fb, shake_y):
        w = self.lay.w
        base_y = self.ground_y + shake_y
        span = 140 if self.lay.compact else 190
        offs = int(self.scroll_x * 0.22) % span
        x = -offs
        idx = int(self.scroll_x * 0.22) // span
        while x < w + span:
            tower_h = (54 if self.lay.compact else 78) + ((idx * 29) % 38)
            tw = 28 if self.lay.compact else 38
            ty = base_y - tower_h
            fb.fill_rect(x + 12, ty, tw, tower_h, DEEP_SLATE)
            fb.ellipse(x + 12 + (tw >> 1), ty, tw >> 1, 10, DEEP_TEAL, True)
            fb.vline(x + 12 + (tw >> 1), ty - 16, 16, CYAN)
            # Lit spire windows.
            fb.fill_rect(x + 12 + (tw >> 1) - 2, ty + 8, 4, tower_h - 16, AQUA_GLOW)
            x += span
            idx += 1

    # Draw Layer 2 (0.50x speed): Midground mossy stone arches and glowing vines.
    def _draw_mid_ruins(self, fb, shake_y):
        w = self.lay.w
        base_y = self.ground_y + shake_y
        span = 110 if self.lay.compact else 156
        offs = int(self.scroll_x * 0.50) % span
        x = -offs
        idx = int(self.scroll_x * 0.50) // span
        arch_h = 46 if self.lay.compact else 68
        pillar_w = 16 if self.lay.compact else 22
        while x < w + span:
            ay = base_y - arch_h
            # Stone lintel and twin pillars.
            fb.fill_rect(x, ay, span - 14, 10, SLATE)
            fb.hline(x, ay, span - 14, MOSS)
            fb.fill_rect(x + 4, ay + 10, pillar_w, arch_h - 10, DEEP_SLATE)
            fb.fill_rect(x + span - 18 - pillar_w, ay + 10, pillar_w, arch_h - 10, DEEP_SLATE)
            # Hanging bioluminescent vines swaying gently in the breeze.
            sway = (isin(self.phase + idx * 37) * 3) >> 10
            vx1 = x + (span >> 1) - 8 + sway
            vh1 = 18 + ((idx * 13) % 16)
            fb.vline(vx1, ay + 10, vh1, EMERALD)
            fb.fill_rect(vx1 - 1, ay + 10 + vh1, 3, 3, LIME_GLOW)
            x += span
            idx += 1

    # Draw Layer 3 (1.00x speed): Foreground mossy ruin floor with glowing cyan runes.
    def _draw_foreground_ground(self, fb, shake_y):
        w = self.lay.w
        gy = self.ground_y + shake_y
        gh = (self.lay.scene_y + self.lay.scene_h) - gy
        if gh <= 0:
            return
        fb.fill_rect(0, gy, w, gh, ABYSS)
        fb.fill_rect(0, gy, w, 6, FOREST)
        fb.hline(0, gy, w, EMERALD)
        fb.hline(0, gy + 1, w, LIME_GLOW)

        tile_w = 40 if self.lay.compact else 56
        offs = int(self.scroll_x) % tile_w
        tx = -offs
        while tx < w:
            fb.vline(tx, gy + 6, gh - 6, NIGHT)
            fb.rect(tx + 8, gy + 12, tile_w - 16, 10, DEEP_TEAL)
            fb.hline(tx + 12, gy + 16, tile_w - 24, CYAN)
            tx += tile_w

    # Draw platforms, crystals, patrol drones, Bit, plasma bolts, and particles.
    def _draw_platforms_and_entities(self, fb, shake_y):
        # Elevated mossy rune platforms.
        for px, py, pw in self.platforms:
            ix = int(px)
            iy = int(py) + shake_y
            fb.fill_rect(ix, iy, pw, 12, SLATE)
            fb.fill_rect(ix + 2, iy + 2, pw - 4, 8, DEEP_SLATE)
            fb.hline(ix, iy, pw, LIME_GLOW)
            fb.hline(ix + 1, iy + 1, pw - 2, EMERALD)
            fb.hline(ix + 8, iy + 6, pw - 16, AQUA_GLOW)

        # Spinning 4-frame bioluminescent crystals with soft radial alpha glow.
        cframe = (self.phase >> 4) % len(self.sprites.crystals)
        csprite = self.sprites.crystals[cframe]
        for cx, cy, active in self.crystals:
            if active:
                bob = (isin(self.phase + int(cx)) * 4) >> 10
                ccx = int(cx)
                ccy = int(cy) + bob + shake_y
                self.sprites.draw_glow(fb, ccx, ccy, AQUA_GLOW, large=True)
                csprite.draw_center(fb, ccx, ccy)

        # Hovering sentinel patrol drones.
        dframe = (self.phase >> 3) % len(self.sprites.drones)
        dsprite = self.sprites.drones[dframe]
        for dx, dy, dphase in self.drones:
            bob = (isin(dphase) * 8) >> 10
            dsprite.draw(fb, int(dx), int(dy) + bob + shake_y)

        # Plasma bolts with alpha glow halo.
        for bx, by in self.bolts:
            ibx = int(bx)
            iby = int(by) + shake_y
            self.sprites.draw_glow(fb, ibx + (self.sprites.bolt.w >> 1), iby + 4, ICE_CYAN, large=False)
            self.sprites.bolt.draw(fb, ibx, iby)
            fb.hline(ibx - 10, iby + 4, 10, AQUA_GLOW)

        # Hero Bit sprite + jetpack flame when airborne.
        hy = int(self.hero_y) + shake_y
        self.sprites.bit_game_r.draw(fb, self.hero_x, hy)
        if not self.on_ground:
            flame = self.sprites.flames[(self.phase >> 2) % len(self.sprites.flames)]
            flame.draw(
                fb,
                self.hero_x + (self.sprites.bit_game_r.w >> 1) - (flame.w >> 1),
                hy + self.sprites.bit_game_r.h - 4,
            )

        # Particle bursts and thruster sparks.
        for p in self.particles:
            fb.fill_rect(int(p[0]), int(p[1]) + shake_y, 3, 3, p[4])

        # Floating score/combo text popups.
        for pop in self.popups:
            fb.text(pop[2], int(pop[0]), int(pop[1]) + shake_y, pop[3])

    # Render the top arcade score bar and bottom tactile JUMP / FIRE touch pads.
    def _draw_hud(self, fb):
        w = self.lay.w
        pad = self.lay.pad
        draw_pixel_panel(
            fb, pad, self.hud_y, w - pad * 2, self.hud_h, ABYSS, CYAN, ICE_CYAN
        )
        ty = self.hud_y + ((self.hud_h - 8) >> 1)
        fb.text(f"SCORE {self.score:06d}", pad + 10, ty, WHITE)
        fb.text(f"CRYSTALS:{self.crystals_collected:02d}", int(w * 0.36), ty, AQUA_GLOW)
        combo_col = GOLD if self.combo > 1 else SILVER
        fb.text(f"COMBO x{self.combo}", int(w * 0.62), ty, combo_col)
        if not self.lay.compact:
            fb.text("JET:RDY", w - pad - 68, ty, LIME_GLOW)

        # Tactile arcade touch controls at the bottom-left and bottom-right.
        jx, jy, jw, jh = self.btn_jump
        fx, fy, fw, fh = self.btn_fire
        draw_pixel_panel(fb, jx, jy, jw, jh, DEEP_TEAL, AQUA_GLOW, WHITE)
        draw_pixel_panel(fb, fx, fy, fw, fh, NIGHT, CORAL, GOLD)
        j_txt = "JUMP / JET" if not self.lay.compact else "JUMP"
        f_txt = "FIRE PLASMA" if not self.lay.compact else "FIRE"
        fb.text(j_txt, jx + ((jw - len(j_txt) * 8) >> 1), jy + ((jh - 8) >> 1), WHITE)
        fb.text(f_txt, fx + ((fw - len(f_txt) * 8) >> 1), fy + ((fh - 8) >> 1), GOLD)
