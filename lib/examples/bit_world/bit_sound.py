# SPDX-FileCopyrightText: 2026 Brad Barnett
#
# SPDX-License-Identifier: MIT

"""Polyphonic synthio soundtrack, robot vocalizer, and SFX engine for Bit World.

Drives three distinct procedural musical motifs (Cozy Workshop Rhodes, Sky Ruins
16-bit Adventure, and Cyber-Deck Harmonic Matrix) alongside expressive robotic
chirps and reactive sound effects, while exporting real-time waveform and
spectrum energy for the on-screen visualizers.

Needs: audiodsp, synthio, bit_palette.

Run it:

    import bit_sound

Tested on: unix MicroPython 1.30 (preview), CircuitPython 10.3, and CPython 3.12.
"""

from array import array
from math import pi, sin
import synthio
from bit_palette import icos, isin, rng_int

# Change these to match your setup.
WAVE_LEN = 256  # Samples per single-cycle wavetable
WAVE_AMP = 24000  # Peak 16-bit signed amplitude per wavetable


# Build a warm Rhodes-like additive waveform (fundamental + 2nd + 3rd harmonics).
def _make_warm_wave():
    return array(
        "h",
        (
            int(
                (0.72 * sin(t) + 0.20 * sin(t * 2.0) + 0.08 * sin(t * 3.0))
                * WAVE_AMP
            )
            for t in (2.0 * pi * i / WAVE_LEN for i in range(WAVE_LEN))
        ),
    )


# Build a bright 25% pulse-like chiptune lead waveform with soft edges.
def _make_lead_wave():
    out = array("h")
    for i in range(WAVE_LEN):
        phase = i / WAVE_LEN
        raw = 0.75 if phase < 0.28 else -0.45
        smooth = raw + 0.25 * sin(2.0 * pi * phase * 2.0)
        out.append(int(max(-1.0, min(1.0, smooth)) * WAVE_AMP))
    return out


# Build a punchy triangle-plus-sub waveform for basslines and reactor hum.
def _make_bass_wave():
    out = array("h")
    for i in range(WAVE_LEN):
        phase = i / WAVE_LEN
        tri = 1.0 - 4.0 * abs(phase - 0.5)
        sub = sin(2.0 * pi * phase)
        out.append(int((0.65 * tri + 0.35 * sub) * WAVE_AMP))
    return out


# Build a glassy bell-like waveform for Bit's vocal chirps and crystal chimes.
def _make_chirp_wave():
    return array(
        "h",
        (
            int(
                (0.58 * sin(t) + 0.27 * sin(t * 3.0) + 0.15 * sin(t * 5.0))
                * WAVE_AMP
            )
            for t in (2.0 * pi * i / WAVE_LEN for i in range(WAVE_LEN))
        ),
    )


WAVE_WARM = _make_warm_wave()
WAVE_LEAD = _make_lead_wave()
WAVE_BASS = _make_bass_wave()
WAVE_CHIRP = _make_chirp_wave()

# Act 1 (Workshop): Cozy F-major-9 / D-minor-9 lo-fi progression (MIDI notes).
WORKSHOP_BASS = (53, 53, 57, 57, 50, 50, 48, 52)
WORKSHOP_MELODY = (
    65, 69, 72, 76, 74, 72, 69, 0,
    62, 65, 69, 74, 72, 69, 67, 0,
    65, 69, 72, 77, 76, 72, 69, 65,
    67, 72, 74, 76, 72, 69, 65, 0,
)

# Act 2 (Sky Ruins): Upbeat 16-bit adventure bass and heroic lead (MIDI notes).
GAME_BASS = (
    45, 57, 45, 57, 48, 60, 48, 60,
    53, 65, 53, 65, 50, 62, 52, 64,
)
GAME_MELODY = (
    69, 0, 72, 74, 76, 0, 79, 76,
    74, 72, 69, 72, 74, 0, 0, 0,
    69, 72, 76, 79, 81, 0, 79, 76,
    74, 76, 72, 69, 67, 0, 64, 0,
)

# Act 3 (Cyber-Deck): 8-step Dorian synth arpeggiator scale (MIDI notes).
DECK_SCALE = (62, 64, 65, 69, 72, 74, 76, 81)


class SoundEngine:
    """Manage synthio playback, 3-act procedural music, SFX, and visualizers."""

    def __init__(self, board_peripherals_mod, app=None):
        self.muted = False
        self.ready = False
        self._warned = False
        self.audio_out = None
        self.synth = None
        self._active_notes = []
        self._sfx_queue = []
        self._step_accum = 0.0
        self._step_index = 0
        self._phase = 0
        self.last_freq = 220.0
        self.voice_energy = 0
        self.scope_samples = [0] * 32
        self.spectrum_bins = [8] * 16
        self.spectrum_peaks = [16] * 16

        self.env_warm = synthio.Envelope(
            attack_time=0.015, decay_time=0.22, release_time=0.25, sustain_level=0.45
        )
        self.env_lead = synthio.Envelope(
            attack_time=0.005, decay_time=0.12, release_time=0.12, sustain_level=0.55
        )
        self.env_bass = synthio.Envelope(
            attack_time=0.008, decay_time=0.16, release_time=0.15, sustain_level=0.50
        )
        self.env_sfx = synthio.Envelope(
            attack_time=0.002, decay_time=0.09, release_time=0.08, sustain_level=0.35
        )

        try:
            self.audio_out = board_peripherals_mod.audio_out(latency="low")
            if app is not None and hasattr(self.audio_out, "attach"):
                self.audio_out.attach(app)
            self.synth = synthio.Synthesizer(
                sample_rate=self.audio_out.format.rate,
                channel_count=self.audio_out.format.channels,
                waveform=WAVE_WARM,
                envelope=self.env_warm,
            )
            self.try_unlock()
        except Exception as exc:
            if not self._warned:
                self._warned = True
                print("bit_world: audio hardware unavailable, running silent:", exc)

    # Attempt to start or unlock the audio transport (needed after first browser gesture).
    def try_unlock(self):
        if self.ready or self.audio_out is None or self.synth is None:
            return self.ready
        try:
            self.audio_out.play(self.synth)
            self.ready = True
            return True
        except Exception:
            self.ready = False
            return False

    # Toggle mute on or off and release any sounding notes when muted.
    def toggle_mute(self):
        self.muted = not self.muted
        if self.muted:
            self.silence()
        else:
            self.try_unlock()
            self.sfx_switch(True)
        return self.muted

    # Stop all active notes immediately.
    def silence(self):
        if self.synth is not None:
            try:
                self.synth.release_all()
            except Exception:
                pass
        self._active_notes.clear()
        self._sfx_queue.clear()

    # Spawn a timed synthio.Note with the specified frequency, waveform, and amplitude.
    def _spawn_note(self, freq, duration, waveform, envelope, amp=0.22):
        self.last_freq = freq
        self.voice_energy = min(100, self.voice_energy + int(amp * 180))
        if self.muted or not self.ready or self.synth is None:
            return
        try:
            note = synthio.Note(
                frequency=freq,
                waveform=waveform,
                envelope=envelope,
                amplitude=amp,
            )
            self.synth.press(note)
            self._active_notes.append([note, duration])
        except Exception:
            pass

    # Play a MIDI note number using the given waveform and envelope.
    def _spawn_midi(self, midi_note, duration, waveform, envelope, amp=0.20):
        if midi_note <= 0:
            return
        freq = synthio.midi_to_hz(midi_note)
        self._spawn_note(freq, duration, waveform, envelope, amp)

    # Queue an expressive multi-syllable robotic chirp for Bit.
    def chirp(self, mood="happy"):
        if mood == "love":
            seq = ((523, 0.06), (659, 0.06), (784, 0.08), (1046, 0.12))
        elif mood == "sing":
            seq = ((587, 0.08), (659, 0.08), (784, 0.10), (880, 0.12), (784, 0.12))
        elif mood == "scan":
            seq = ((880, 0.04), (440, 0.04), (988, 0.04), (587, 0.06), (1175, 0.08))
        elif mood == "coffee":
            seq = ((440, 0.05), (554, 0.05), (659, 0.05), (880, 0.07), (1108, 0.10))
        elif mood == "sleep":
            seq = ((523, 0.10), (392, 0.12), (330, 0.16))
        else:
            seq = ((587, 0.05), (784, 0.06), (988, 0.09))
        delay = 0.0
        for freq, dur in seq:
            self._sfx_queue.append([delay, freq, dur, WAVE_CHIRP, self.env_sfx, 0.24])
            delay += dur * 0.85

    # Trigger a rising jetpack boost / jump sound effect.
    def sfx_jump(self):
        self._sfx_queue.append([0.0, 260.0, 0.05, WAVE_LEAD, self.env_sfx, 0.22])
        self._sfx_queue.append([0.04, 390.0, 0.06, WAVE_LEAD, self.env_sfx, 0.22])
        self._sfx_queue.append([0.08, 540.0, 0.08, WAVE_CHIRP, self.env_sfx, 0.18])

    # Trigger a plasma bolt laser sound effect.
    def sfx_laser(self):
        self._sfx_queue.append([0.0, 1120.0, 0.035, WAVE_LEAD, self.env_sfx, 0.25])
        self._sfx_queue.append([0.03, 680.0, 0.045, WAVE_LEAD, self.env_sfx, 0.22])
        self._sfx_queue.append([0.06, 420.0, 0.05, WAVE_BASS, self.env_sfx, 0.18])

    # Trigger a sparkling crystal pickup chime.
    def sfx_crystal(self):
        self._sfx_queue.append([0.0, 987.7, 0.06, WAVE_CHIRP, self.env_sfx, 0.25])
        self._sfx_queue.append([0.05, 1318.5, 0.12, WAVE_CHIRP, self.env_warm, 0.25])

    # Trigger a punchy drone explosion sound effect.
    def sfx_boom(self):
        self._sfx_queue.append([0.0, 145.0, 0.08, WAVE_BASS, self.env_bass, 0.32])
        self._sfx_queue.append([0.04, 98.0, 0.12, WAVE_LEAD, self.env_bass, 0.28])
        self._sfx_queue.append([0.09, 68.0, 0.16, WAVE_BASS, self.env_bass, 0.26])

    # Trigger a crisp mechanical toggle switch click.
    def sfx_switch(self, state=True):
        f1 = 740.0 if state else 520.0
        f2 = 980.0 if state else 380.0
        self._sfx_queue.append([0.0, f1, 0.025, WAVE_CHIRP, self.env_sfx, 0.20])
        self._sfx_queue.append([0.02, f2, 0.035, WAVE_CHIRP, self.env_sfx, 0.18])

    # Trigger a harmonic tone when a Cyber-Deck sequencer pad is toggled.
    def sfx_pad(self, pad_idx, active=True):
        midi = DECK_SCALE[pad_idx & 7] + (12 if active else 0)
        self._spawn_midi(midi, 0.11, WAVE_CHIRP, self.env_lead, 0.24)

    # Advance active note releases, queued SFX, 3-act music sequencer, and visualizers.
    def update(self, dt, act_idx, deck_state=None):
        if dt <= 0.0:
            dt = 0.016
        elif dt > 0.12:
            dt = 0.12

        # Release any notes whose gate duration has expired.
        i = len(self._active_notes) - 1
        while i >= 0:
            entry = self._active_notes[i]
            entry[1] -= dt
            if entry[1] <= 0.0:
                if self.synth is not None:
                    try:
                        self.synth.release(entry[0])
                    except Exception:
                        pass
                self._active_notes.pop(i)
            i -= 1

        # Fire any delayed SFX syllables whose countdown has reached zero.
        j = len(self._sfx_queue) - 1
        while j >= 0:
            item = self._sfx_queue[j]
            item[0] -= dt
            if item[0] <= 0.0:
                _, freq, dur, wf, env, amp = self._sfx_queue.pop(j)
                self._spawn_note(freq, dur, wf, env, amp)
            j -= 1

        # Determine step tempo based on the active act and Cyber-Deck throttle.
        if act_idx == 0:
            step_period = 0.22
        elif act_idx == 1:
            step_period = 0.14
        else:
            throttle = 0.55 if deck_state is None else deck_state.get("throttle", 0.55)
            step_period = max(0.09, 0.22 - throttle * 0.11)

        self._step_accum += dt
        if self._step_accum >= step_period:
            self._step_accum -= step_period
            self._trigger_music_step(act_idx, deck_state)
            self._step_index = (self._step_index + 1) & 0xFF

        self._update_visualizers()

    # Trigger one rhythmic step of the current act's procedural soundtrack.
    def _trigger_music_step(self, act_idx, deck_state):
        if not self.ready and not self.muted:
            self.try_unlock()
        step = self._step_index
        if act_idx == 0:
            # Cozy Workshop: warm Rhodes bass on beats and bell melody on 16ths.
            if (step & 3) == 0:
                bass_note = WORKSHOP_BASS[(step >> 2) % len(WORKSHOP_BASS)]
                self._spawn_midi(bass_note, 0.36, WAVE_WARM, self.env_warm, 0.16)
            mel = WORKSHOP_MELODY[step % len(WORKSHOP_MELODY)]
            if mel:
                self._spawn_midi(mel, 0.18, WAVE_CHIRP, self.env_warm, 0.14)
        elif act_idx == 1:
            # Sky Ruins: driving chiptune bassline and heroic pulse lead.
            bass_note = GAME_BASS[step % len(GAME_BASS)]
            self._spawn_midi(bass_note, 0.11, WAVE_BASS, self.env_bass, 0.17)
            mel = GAME_MELODY[step % len(GAME_MELODY)]
            if mel:
                self._spawn_midi(mel, 0.12, WAVE_LEAD, self.env_lead, 0.16)
        else:
            # Cyber-Deck: arpeggiate across active harmonic pads + reactor bass pulse.
            pads = None if deck_state is None else deck_state.get("pads")
            boost = False if deck_state is None else deck_state.get("boost", False)
            overdrive = False if deck_state is None else deck_state.get("overdrive", False)
            slot = step & 7
            if (step & 1) == 0:
                root = 50 if not overdrive else 53
                self._spawn_midi(root + (12 if (step & 2) else 0), 0.13, WAVE_BASS, self.env_bass, 0.17)
            if pads is None or pads[slot]:
                note = DECK_SCALE[slot] + (12 if boost and (step & 1) else 0)
                wf = WAVE_LEAD if overdrive else WAVE_WARM
                self._spawn_midi(note, 0.12, wf, self.env_lead, 0.18)

    # Synthesize responsive oscilloscope and 16-band spectrum values for HUD widgets.
    def _update_visualizers(self):
        self._phase = (self._phase + 7) & 0xFF
        self.voice_energy = max(0, self.voice_energy - 6)
        active_count = len(self._active_notes)
        base_amp = 24 + min(68, active_count * 22 + (self.voice_energy >> 1))
        freq_ratio = max(1, min(6, int(self.last_freq / 160.0)))

        for i in range(32):
            p1 = (self._phase + i * freq_ratio * 4) & 0xFF
            p2 = (self._phase * 2 + i * 11) & 0xFF
            val = ((isin(p1) * 7 + icos(p2) * 3) * base_amp) >> 13
            self.scope_samples[i] = max(-95, min(95, val))

        center_bin = max(1, min(14, int((self.last_freq - 90.0) / 70.0)))
        for b in range(16):
            dist = abs(b - center_bin)
            harmonic = 28 if (b == (center_bin + 4) & 15) else 0
            target = max(6, base_amp - dist * 11 + harmonic + rng_int(-4, 6))
            if self.muted:
                target = 4
            cur = self.spectrum_bins[b]
            if target > cur:
                cur = min(100, cur + ((target - cur) >> 1) + 4)
            else:
                cur = max(4, cur - 5)
            self.spectrum_bins[b] = cur
            if cur >= self.spectrum_peaks[b]:
                self.spectrum_peaks[b] = cur
            else:
                self.spectrum_peaks[b] = max(cur, self.spectrum_peaks[b] - 2)

    # Close the audio transport cleanly on application exit.
    def close(self):
        self.silence()
        if self.audio_out is not None:
            if hasattr(self.audio_out, "detach"):
                try:
                    self.audio_out.detach()
                except Exception:
                    pass
            try:
                self.audio_out.close()
            except Exception:
                pass
