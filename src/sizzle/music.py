"""The soundtrack: narration placed on the timeline over a score generated for this project.

Everything is synthesised from numpy, so a reel never needs a licensed track. Writes
`mix.wav` (voice + music) and `voice.wav` (voice alone, for when the platform's own
audio is used instead).

The score is *generated*, not chosen from a handful of presets. A seed — by default the
brand name — decides a style, a key, a mode, a chord progression, a drum kit and one
synthesis voice each for bass, lead and pad. Two projects do not get the same track, and
the same project gets the same track every time it renders.

Standalone like the narrator, so it can run in the small numpy/scipy environment rather
than forcing those into the app being advertised:

    python music.py <reel_dir> [bpm] [chords] [music_gain] [duck] [seed] [style]
"""

from __future__ import annotations

import json
import wave
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

SR = 48000


def hz(semitone: float) -> float:
    """Frequency of a semitone offset from A0."""
    return 27.5 * 2 ** (semitone / 12)


# Scale degrees, so harmony is built rather than listed.
MODES = {
    "aeolian": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "ionian": [0, 2, 4, 5, 7, 9, 11],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "harmonic": [0, 2, 3, 5, 7, 8, 11],
}
PROGRESSIONS = [
    [0, 5, 3, 4], [0, 3, 4, 4], [5, 3, 0, 4], [0, 4, 5, 3],
    [0, 6, 3, 4], [3, 4, 0, 0], [0, 2, 3, 5], [5, 0, 3, 4],
    [0, 5, 1, 4], [0, 3, 5, 4],
]
# Old [audio] chords names keep working, as (mode, progression).
LEGACY = {"minor-lift": ("aeolian", 0), "bright": ("ionian", 3), "tense": ("phrygian", 5),
          "warm": ("dorian", 1), "wide": ("mixolydian", 2), "night": ("harmonic", 4)}

# A style bundles choices that belong together, so the result stays musical instead of
# being a random pile of timbres. The seed picks the style, then varies inside it.
STYLES = {
    "neon":    dict(kit="synth", bass=["saw"], lead=["pluck", "bell"],
                    pad=["saws", "airy"], rev=0.16, drums=1.0, arp_oct=2, pad_gain=1.0, sat=0.15, mel=["pluck", "bell"], mel_lift=0),
    "eight":   dict(kit="808", bass=["sub"], lead=["bell", "pluck"],
                    pad=["airy"], rev=0.26, drums=1.0, arp_oct=2, pad_gain=0.8, sat=0.1, mel=["bell", "glass"], mel_lift=0),
    "lofi":    dict(kit="lofi", bass=["round", "sub"], lead=["marimba", "bell"],
                    pad=["tape"], rev=0.3, drums=0.8, arp_oct=1, pad_gain=1.2, sat=0.4, mel=["marimba", "bell"], mel_lift=0),
    "drive":   dict(kit="synth", bass=["square"], lead=["pulse"],
                    pad=["square"], rev=0.08, drums=1.15, arp_oct=4, pad_gain=0.8, sat=0.65, mel=["pulse", "square"], mel_lift=1),
    "organic": dict(kit="brush", bass=["string", "round"], lead=["marimba", "glass", "pluck"],
                    pad=["strings", "bowed"], rev=0.34, drums=0.7, arp_oct=1, pad_gain=1.1, sat=0.05, mel=["marimba", "glass"], mel_lift=0),
    "dub":     dict(kit="808", bass=["sub", "round"], lead=["bell", "glass"],
                    pad=["bowed", "tape"], rev=0.48, drums=0.6, arp_oct=1, pad_gain=1.3, sat=0.2, mel=["glass", "bell"], mel_lift=0),
    "still":   dict(kit="none", bass=["sub"], lead=["glass", "bell"],
                    pad=["bowed", "airy"], rev=0.42, drums=0.0, arp_oct=1, pad_gain=1.5, sat=0.0, mel=["glass", "bell"], mel_lift=0),
}

KICKS = [(0, 4), (0, 4, 7), (0, 3, 4), (0, 4, 6), (0, 2, 4), (0, 6)]
SNARES = [(2, 6), (6,), (2, 6, 7), (4,), (2, 5, 6)]
HATS = [(1, 3, 5, 7), (0, 2, 4, 6), (1, 2, 3, 5, 6, 7), (2, 6), tuple(range(8))]
ARPS = [(0, 1, 2, 1), (0, 2, 1, 2), (2, 1, 0, 1), (0, 1, 2, 0), (1, 2, 1, 0), (0, 2, 4, 2)]
BASSES = [(0, 1, 2, 3, 4, 5, 6, 7), (0, 2, 3, 4, 6, 7), (0, 3, 4, 7), (0, 1, 3, 4, 5, 7), (0, 4)]

# The melody. A rhythm says which eighths of the bar are struck; a contour says how far
# the motif walks from the chord's own degree. Together they make a phrase you could hum,
# which is what separates two songs from two beds in the same genre.
RHYTHMS = [(0, 2, 3, 6), (0, 3, 4, 6), (0, 1, 3, 6), (0, 2, 4, 5, 7),
           (0, 4), (2, 3, 6, 7), (0, 2, 5), (0, 1, 4, 6, 7)]
CONTOURS = [(0, 1, 2, 1), (0, 2, 1, -1), (0, -1, 1, 2), (2, 1, 0, -2),
            (0, 3, 2, 0), (0, 1, -1, 0), (0, 2, 4, 2), (4, 2, 1, 0)]


@dataclass
class Palette:
    """Everything the seed decided. Printed on every run so a score can be reproduced."""
    style: str
    root: int
    mode: str
    progression: list
    kit: str
    bass: str
    lead: str
    pad: str
    kick_at: tuple
    snare_at: tuple
    hat_at: tuple
    arp: tuple
    bass_at: tuple
    swing: float
    rev: float
    pad_hz: float
    drums: float
    arp_oct: int
    pad_gain: float
    sat: float
    mel: str
    mel_oct: int
    rhythm: tuple
    contour: tuple

    def line(self) -> str:
        return (f"score: {self.style} · {self.mode} on {'ACDEFGB'[self.root % 7]}{self.root} · "
                f"{self.kit} kit · {self.bass} bass · {self.lead} lead · {self.pad} pad · "
                f"{self.mel} melody {self.rhythm}{self.contour}")


def palette_for(seed: int, chord_set: str = "auto", style: str = "auto") -> Palette:
    pick = np.random.default_rng(seed)

    def one(seq):
        return seq[int(pick.integers(len(seq)))]

    name = style if style in STYLES else one(sorted(STYLES))
    s = STYLES[name]
    if chord_set in LEGACY:
        mode, prog = LEGACY[chord_set][0], PROGRESSIONS[LEGACY[chord_set][1]]
    elif chord_set in MODES:
        mode, prog = chord_set, one(PROGRESSIONS)
    else:
        mode, prog = one(sorted(MODES)), one(PROGRESSIONS)
    built = Palette(
        style=name, root=int(pick.integers(24, 34)), mode=mode, progression=prog,
        kit=s["kit"], bass=one(s["bass"]), lead=one(s["lead"]), pad=one(s["pad"]),
        kick_at=one(KICKS), snare_at=one(SNARES), hat_at=one(HATS),
        arp=one(ARPS), bass_at=one(BASSES),
        swing=float(pick.uniform(0, 0.035)), rev=s["rev"] * float(pick.uniform(0.7, 1.35)),
        pad_hz=float(pick.uniform(900, 2400)), drums=s["drums"] * float(pick.uniform(0.85, 1.15)),
        arp_oct=int(s["arp_oct"] * one((1, 1, 2))), pad_gain=s["pad_gain"] * float(pick.uniform(0.8, 1.25)),
        sat=s["sat"] * float(pick.uniform(0.6, 1.4)),
        mel=one(s["mel"]), mel_oct=0, rhythm=one(RHYTHMS), contour=one(CONTOURS))
    if built.mel == built.lead:     # two layers of one timbre is what reads as "ringing"
        others = [v for v in s["mel"] if v != built.lead]
        built.mel = others[0] if others else CONTRAST.get(built.lead, "marimba")
    # The melody's octave is derived, not drawn: whatever key the seed picked, the tune
    # lands in the same singable register. Drawing it at random put earlier motifs at
    # 3 kHz, fighting the narration for exactly the band a voice needs.
    tonic = hz(built.root + MODES[built.mode][0])
    built.mel_oct = int(round(np.log2(MEL_CENTRE / tonic))) + s["mel_lift"]
    return built


CONTRAST = {"bell": "marimba", "pluck": "marimba", "glass": "marimba",
            "pulse": "square", "marimba": "glass", "square": "pulse"}
MEL_CENTRE = 420.0      # a singable register that sits below the voice's presence band


def scale_hz(p: Palette, degree: int, octave: int = 0) -> float:
    """A note of the key by scale degree — melodies need passing tones, not just triads."""
    scale = MODES[p.mode]
    return hz(p.root + scale[degree % 7] + 12 * (degree // 7) + 12 * octave)


def chords_of(p: Palette) -> list:
    """(root Hz, triad Hz) per bar, built from the mode rather than looked up."""
    scale = MODES[p.mode]
    out = []
    for degree in p.progression:
        notes = []
        for step in (0, 2, 4):
            d = degree + step
            notes.append(hz(p.root + scale[d % 7] + 12 * (d // 7)))
        out.append((hz(p.root + scale[degree % 7] - 12), notes))
    return out


def _read(path: Path) -> np.ndarray:
    with wave.open(str(path)) as w:
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64) / 32768
        rate = w.getframerate()
    if data.ndim > 1:
        data = data.mean(axis=1)
    x_old = np.arange(len(data)) / rate
    x_new = np.arange(int(len(data) * SR / rate)) / SR
    return np.interp(x_new, x_old, data)


def _write(path: Path, stereo: np.ndarray) -> None:
    data = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def build(out_dir: Path, bpm: int = 100, chord_set: str = "auto", gain: float = 0.42,
          duck: float = 0.6, seed: int = 0, style: str = "auto") -> tuple[Path, Path]:
    timeline = json.loads((out_dir / "timeline.json").read_text())
    end, impact, scenes = timeline["end"], timeline["impact"], timeline["scenes"]
    n = int(end * SR)
    rng = np.random.default_rng(3)          # noise texture; the palette carries the identity
    p = palette_for(seed, chord_set, style)
    print(p.line(), flush=True)

    def lowpass(x, f, order=2):
        return sosfilt(butter(order, min(f, SR / 2 - 100), "low", fs=SR, output="sos"), x)

    def highpass(x, f, order=2):
        return sosfilt(butter(order, f, "high", fs=SR, output="sos"), x)

    def bandpass(x, lo, hi, order=2):
        return sosfilt(butter(order, [lo, min(hi, SR / 2 - 100)], "band", fs=SR, output="sos"), x)

    def place(track, sound, at, g=1.0):
        i = int(at * SR)
        if i >= len(track) or i < 0:
            return
        j = min(len(track), i + len(sound))
        track[i:j] += sound[: j - i] * g

    def env(m, attack, decay):
        t = np.arange(m) / SR
        return np.minimum(1, t / max(attack, 1e-4)) * np.exp(-t / decay)

    # --- voices: one function per timbre, so a style can swap the whole palette ---------

    def v_saw(f, m, detune=0.0):
        t = np.arange(m) / SR
        out = np.zeros(m)
        for k in range(1, 14):
            out += np.sin(2 * np.pi * k * f * (1 + detune) * t) / k
        return out

    def v_square(f, m, detune=0.0):
        t = np.arange(m) / SR
        out = np.zeros(m)
        for k in range(1, 16, 2):
            out += np.sin(2 * np.pi * k * f * (1 + detune) * t) / k
        return out

    def v_pulse(f, m, detune=0.0):
        t = np.arange(m) / SR
        return np.where((t * f * (1 + detune)) % 1 < 0.28, 1.0, -1.0) * 0.5

    def v_sub(f, m, detune=0.0):
        t = np.arange(m) / SR
        return np.sin(2 * np.pi * f * t) + 0.22 * np.sin(4 * np.pi * f * t)

    def v_round(f, m, detune=0.0):
        t = np.arange(m) / SR
        return np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 2 * t) * np.exp(-t * 6)

    def v_bell(f, m, detune=0.0):
        """FM: a metallic strike whose index falls away."""
        t = np.arange(m) / SR
        index = 2.4 * np.exp(-t * 9)          # a soft strike; 6 with a 1.41 ratio clangs
        return np.sin(2 * np.pi * f * t + index * np.sin(2 * np.pi * f * 2.0 * t))

    def v_marimba(f, m, detune=0.0):
        t = np.arange(m) / SR
        return (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t * 22)
                + 0.2 * np.sin(2 * np.pi * f * 9.2 * t) * np.exp(-t * 40))

    def v_glass(f, m, detune=0.0):
        t = np.arange(m) / SR
        return sum(np.sin(2 * np.pi * f * h * t + i) / (h ** 1.4)
                   for i, h in enumerate((1, 2, 3.01, 4.97)))

    def v_pluck(f, m, detune=0.0):
        """Karplus-Strong: a real plucked string, and nothing else here sounds like it."""
        length = max(2, int(SR / max(f, 20)))
        buf = list(rng.uniform(-1, 1, length))
        out = np.empty(m)
        i = 0
        for s in range(m):
            out[s] = buf[i]
            nxt = (i + 1) % length
            buf[i] = 0.498 * (buf[i] + buf[nxt])
            i = nxt
        return out

    def v_string(f, m, detune=0.0):
        t = np.arange(m) / SR
        vib = 1 + 0.004 * np.sin(2 * np.pi * 5.2 * t)
        return v_saw(f, m, detune) * vib

    VOICES = {"saw": v_saw, "square": v_square, "pulse": v_pulse, "sub": v_sub, "square_pad": v_square, "round": v_round,
              "bell": v_bell, "marimba": v_marimba, "glass": v_glass, "pluck": v_pluck,
              "string": v_string, "saws": v_saw, "airy": v_glass, "tape": v_round,
              "bowed": v_string, "strings": v_string}

    cache: dict = {}

    def note(kind, f, m, detune=0.0):
        """Voices repeat constantly; render each distinct note once."""
        key = (kind, round(f, 2), m, round(detune, 4))
        if key not in cache:
            cache[key] = VOICES[kind](f, m, detune)
        return cache[key]

    # --- drum kits -----------------------------------------------------------------------

    def kick_synth():
        m = int(0.45 * SR)
        t = np.arange(m) / SR
        f = 45 + 110 * np.exp(-t * 28)
        ph = 2 * np.pi * np.cumsum(f) / SR
        return np.sin(ph) * np.exp(-t * 7) + 0.25 * np.sin(ph * 2) * np.exp(-t * 30)

    def kick_808():
        m = int(1.1 * SR)
        t = np.arange(m) / SR
        f = 38 + 70 * np.exp(-t * 34)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.4)

    def kick_lofi():
        return lowpass(kick_synth(), 900) * 0.9

    def snare_synth():
        m = int(0.3 * SR)
        t = np.arange(m) / SR
        return (0.7 * bandpass(rng.standard_normal(m), 1200, 7000) * env(m, 0.001, 0.09)
                + 0.4 * np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25))

    def clap():
        m = int(0.34 * SR)
        out = np.zeros(m)
        for k, off in enumerate((0.0, 0.011, 0.022)):
            burst = bandpass(rng.standard_normal(m), 1100, 6000) * env(m, 0.0008, 0.05)
            place(out, burst, off, 0.8 ** k)
        return out + bandpass(rng.standard_normal(m), 1400, 5000) * env(m, 0.001, 0.14) * 0.5

    def snare_brush():
        m = int(0.4 * SR)
        return bandpass(rng.standard_normal(m), 900, 4200) * env(m, 0.012, 0.16) * 0.8

    def hat_synth(open_=False):
        m = int((0.25 if open_ else 0.06) * SR)
        return highpass(rng.standard_normal(m), 7500) * env(m, 0.0005, 0.08 if open_ else 0.018)

    def hat_lofi(open_=False):
        m = int((0.2 if open_ else 0.05) * SR)
        return bandpass(rng.standard_normal(m), 4000, 9000) * env(m, 0.001, 0.07 if open_ else 0.016)

    def shaker(open_=False):
        m = int(0.09 * SR)
        return highpass(rng.standard_normal(m), 5200) * env(m, 0.006, 0.035)

    KITS = {
        "synth": (kick_synth, snare_synth, hat_synth),
        "808": (kick_808, clap, hat_synth),
        "lofi": (kick_lofi, snare_brush, hat_lofi),
        "brush": (kick_lofi, snare_brush, shaker),
        "none": (None, None, None),
    }
    kick, snare, hat = KITS[p.kit]

    def boom():
        m = int(2.2 * SR)
        t = np.arange(m) / SR
        f = 32 + 90 * np.exp(-t * 6)
        return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6)
                + lowpass(rng.standard_normal(m), 6000) * env(m, 0.002, 0.7) * 0.35)

    def riser(length):
        m = int(length * SR)
        noise = rng.standard_normal(m)
        out = np.zeros(m)
        for c in range(24):
            a, b = c * m // 24, (c + 1) * m // 24
            f = 400 * (18 ** (c / 24))
            out[a:b] = bandpass(noise[a:b], f * 0.6, min(f * 1.6, 20000))
        return out * np.linspace(0, 1, m) ** 2

    def whoosh(length=0.55):
        m = int(length * SR)
        return bandpass(rng.standard_normal(m), 600, 5000) * np.sin(np.linspace(0, np.pi, m)) ** 2

    # --- voice ---------------------------------------------------------------------------

    voice = np.zeros(n)
    for key, (start, _length) in timeline["vo"].items():
        line = _read(out_dir / "vo" / f"{key}.wav")
        line = highpass(line, 70)
        line = line / (np.max(np.abs(line)) + 1e-9) * 0.9
        line = np.tanh(line * 1.6) / np.tanh(1.6)
        place(voice, line, start)

    # --- music ---------------------------------------------------------------------------

    beat_len = 60 / bpm
    bar_len = 4 * beat_len
    chords = chords_of(p)
    music = np.zeros((n, 2))

    def mono_to(track, sound, at, g=1.0, pan=0.0):
        left, right = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        for channel, side in ((0, left), (1, right)):
            column = np.zeros(n)
            place(column, sound, at, g * side * 1.41)
            track[:, channel] += column

    # Tension before the drop: a low drone, ticking percussion, a riser into the impact.
    drone_n = max(1, int(impact * SR))
    t = np.arange(drone_n) / SR
    low = chords[0][0]
    drone = lowpass(note(p.pad, low, drone_n, 0.003) + note(p.pad, low, drone_n, -0.004),
                    320) * np.minimum(1, t / 1.5) * 0.18
    mono_to(music, drone, 0.0, 1.0)
    if hat is not None:
        tick = 0.6
        while tick < impact - 0.3:
            mono_to(music, hat(), tick, (0.22 + 0.25 * tick / max(impact, 1e-6)) * max(p.drums, 0.5),
                    pan=0.3 if int(tick / (beat_len / 2)) % 2 else -0.3)
            tick += beat_len / 2 if tick < impact * 0.55 else beat_len / 4
    mono_to(music, riser(3.0), max(0.0, impact - 3.0), 0.22)

    # The drop, then the groove until the sign-off.
    groove_end = scenes[-1][1] + 3.2
    mono_to(music, boom(), impact, 0.9)
    eighth = beat_len / 2
    bar_time = impact
    while bar_time < groove_end and p.drums > 0:
        for step in range(8):
            at = bar_time + step * eighth + (p.swing if step % 2 else 0.0)
            if kick and step in p.kick_at:
                mono_to(music, kick(), at, 0.75 * p.drums)
            if snare and step in p.snare_at:
                mono_to(music, snare(), at, 0.32 * p.drums)
            if hat and step in p.hat_at:
                mono_to(music, hat(open_=step == 7), at, 0.16 * p.drums,
                        pan=0.25 if step % 2 else -0.2)
        bar_time += bar_len

    # Bass, pad and the arpeggio, all in the palette's voices.
    bar_time, index = impact, 0
    while bar_time < groove_end:
        root, triad = chords[index % len(chords)]
        n_bar = int(bar_len * SR)
        tb = np.arange(n_bar) / SR
        pad = sum(note(p.pad, f, n_bar, d) for f in triad for d in (-0.004, 0.004))
        pad = lowpass(pad, p.pad_hz) * np.minimum(1, tb / 0.6) * np.minimum(1, (bar_len - tb) / 0.3)
        pad = pad * 0.035 * p.pad_gain
        mono_to(music, pad, bar_time, 1.0, pan=-0.2)
        mono_to(music, pad, bar_time, 0.9, pan=0.2)
        m = int(eighth * SR)
        for step in range(8):
            at = bar_time + step * eighth
            if step in p.bass_at:
                bass = lowpass(note(p.bass, root / 2, m), 400) * env(m, 0.005, 0.18) * 0.28
                mono_to(music, bass, at, 1.0)
            lead_f = triad[p.arp[step % len(p.arp)] % len(triad)] * p.arp_oct
            pluck = note(p.lead, lead_f, m) * env(m, 0.002, 0.12) * 0.045
            mono_to(music, pluck, at, 1.0, pan=0.5 if step % 2 else -0.5)
        bar_time += bar_len
        index += 1

    # The melody: a motif that knows where the talking is. sizzle already has the exact
    # span of every narrated line, so the tune states itself in the gaps and drops to a
    # whisper underneath speech — what someone scoring to a voiceover would do by hand.
    speech = np.zeros(n)
    for _key, (start, length) in timeline["vo"].items():
        a, b = int(start * SR), int(min(n, (start + length) * SR))
        if b > a:
            speech[a:b] = 1.0
    win = int(0.12 * SR)
    speech = np.clip(np.convolve(speech, np.ones(win) / win, mode="same") * 1.4, 0, 1)

    strikes = list(p.rhythm)
    bar_time, index = impact + bar_len, 0        # let the drop breathe for one bar first
    while bar_time < groove_end:
        degree = p.progression[(index + 1) % len(p.progression)]
        closing = index % 4 == 3                 # every fourth bar answers, and resolves home
        for i, step in enumerate(strikes):
            at = bar_time + step * eighth
            if at >= groove_end:
                break
            until = strikes[i + 1] * eighth if i + 1 < len(strikes) else 8 * eighth
            m = max(int((until - step * eighth) * SR), int(0.12 * SR))
            walk = p.contour[i % len(p.contour)]
            wanted = 0 if (closing and i == len(strikes) - 1) else degree + walk
            talking = speech[min(n - 1, int(at * SR))]
            # Under speech a composer plays fewer notes, not quieter mush: keep the note
            # that carries the phrase, drop the passing ones. 86% of a narrated reel is
            # talking, so ducking alone would erase the tune outright.
            if talking > 0.55 and not (i < 2 or (closing and i == len(strikes) - 1)):
                continue
            tune = lowpass(note(p.mel, scale_hz(p, wanted, p.mel_oct), m), 3200)
            hold = min(0.5, max(0.16, m / SR * 0.55))     # let long notes ring, short ones clip
            mono_to(music, tune * env(m, 0.004, hold) * 0.34 * (1 - 0.4 * talking), at, 1.0,
                    pan=0.12 * (1 if i % 2 else -1))
        bar_time += bar_len
        index += 1

    # Sidechain pump: the bed breathes with the kick.
    if p.drums > 0:
        pump = np.ones(n)
        bar_time = impact
        while bar_time < groove_end:
            i = int(bar_time * SR)
            m = min(int(beat_len * SR), n - i)
            if m > 0:
                pump[i:i + m] = np.minimum(pump[i:i + m], 0.55 + 0.45 * np.minimum(
                    1, (np.arange(m) / SR) / (beat_len * 0.55)))
            bar_time += beat_len
        music *= pump[:, None]

    for _name, start in scenes[3:]:
        mono_to(music, whoosh(), max(0.0, start - 0.2), 0.12)
    mono_to(music, boom(), scenes[-1][1] + 0.3, 0.55)
    tail_n = int((end - groove_end + 0.5) * SR)
    if tail_n > 0:
        tf = np.arange(tail_n) / SR
        tail = lowpass(sum(note(p.pad, f, tail_n, d) for f in chords[0][1] for d in (-0.004, 0.004)), 1200)
        tail *= np.minimum(1, tf / 0.2) * np.exp(-tf / 1.4) * 0.05
        mono_to(music, tail, max(0.0, groove_end - 0.5), 1.0)

    # Saturation: what separates a driven synth bed from a clean one.
    if p.sat > 0:
        k = 1 + 3 * p.sat
        music = np.tanh(music * k) / np.tanh(k)

    # Space. A still, reverberant style and a dry, driving one should not share a room.
    if p.rev > 0.02:
        ir_n = int(1.4 * SR)
        ir = rng.standard_normal(ir_n) * np.exp(-np.arange(ir_n) / SR / 0.34)
        ir = lowpass(ir, 5200)
        ir /= np.sqrt(np.sum(ir ** 2)) + 1e-9
        for channel in (0, 1):
            wet = fftconvolve(music[:, channel], ir)[:n]
            music[:, channel] = (1 - p.rev) * music[:, channel] + p.rev * wet

    # Keep the voice on top. Ducking the whole bed equally still leaves music sitting in
    # the 1.5-5 kHz band where consonants live, which is what makes a score fight a
    # narrator: it reads as a sharp ring over the voice. Duck that band hardest, let the
    # low end keep carrying the groove, and take the brittle top off everything.
    for ch in (0, 1):
        music[:, ch] = lowpass(music[:, ch], 12000)
    # An envelope follower alone rides the dips between syllables, letting the bed surge
    # back inside a sentence. sizzle knows the exact span of every narrated line, so hold
    # the duck across the whole line and let the follower only add to it.
    held = np.zeros(n)
    for _key, (start, length) in timeline["vo"].items():
        held[int(start * SR):min(n, int((start + length) * SR))] = 1.0
    edge = int(0.15 * SR)
    held = np.clip(np.convolve(held, np.ones(edge) / edge, mode="same") * 1.6, 0, 1)
    follower = lowpass(np.abs(voice), 6)
    follower = np.clip(follower / (follower.max() + 1e-9) * 3, 0, 1)
    level = np.maximum(held, follower)
    # Depths aimed at a broadcast balance: the bed keeps its low end under a line, the
    # consonant band sits ~20 dB down, and sibilance further still. Crushing the mids to
    # nothing instead leaves a hollow, pumping bed, so this is deliberately not maximal.
    lo_gain = 1 - min(duck * 0.70, 0.94) * level
    mid_gain = 1 - min(duck * 1.00, 0.90) * level
    hi_gain = 1 - min(duck * 1.10, 0.92) * level
    for ch in (0, 1):
        x = music[:, ch]
        # Steep, or the split is a lie: an order-2 lowpass at 900 Hz still passes 2 kHz
        # at only -14 dB, so the consonant band hides in the band that ducks least.
        low_band = lowpass(x, 900, order=8)
        high_band = highpass(x, 5200, order=8)
        music[:, ch] = (low_band * lo_gain + (x - low_band - high_band) * mid_gain
                        + high_band * hi_gain)
    music /= np.max(np.abs(music)) + 1e-9
    music *= gain

    mix = music + voice[:, None] * 0.95
    fade = np.ones(n)
    fade[-int(0.8 * SR):] = np.linspace(1, 0, int(0.8 * SR))
    mix *= fade[:, None]
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    mix *= 0.93 / (np.max(np.abs(mix)) + 1e-9)

    mix_path, voice_path = out_dir / "mix.wav", out_dir / "voice.wav"
    _write(mix_path, mix)
    _write(voice_path, np.repeat(voice[:, None] * 0.9, 2, axis=1) * fade[:, None])
    # The bed on its own: useful to audition, and the only honest way to check how much
    # music is sitting on top of the narration.
    _write(out_dir / "music.wav", music * fade[:, None])
    return mix_path, voice_path


if __name__ == "__main__":
    import sys

    argv = sys.argv[1:]
    build(Path(argv[0]),
          int(argv[1]) if len(argv) > 1 else 100,
          argv[2] if len(argv) > 2 else "auto",
          float(argv[3]) if len(argv) > 3 else 0.42,
          float(argv[4]) if len(argv) > 4 else 0.6,
          int(argv[5]) if len(argv) > 5 else 0,
          argv[6] if len(argv) > 6 else "auto")
    print("audio written")
