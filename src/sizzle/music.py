"""The soundtrack: narration placed on the timeline over an original, synthesized bed.

Everything is generated from numpy, so a reel never needs a licensed track. Writes
`mix.wav` (voice + music) and `voice.wav` (voice alone, for when the platform's own
audio is used instead).

Standalone like the narrator, so it can run in the small numpy/scipy environment
rather than forcing those into the app being advertised:

    python music.py <reel_dir> [bpm] [chords] [music_gain] [duck]
"""

from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000

CHORDS = {
    # name: (root Hz, triad Hz) per bar
    "minor-lift": [(110.0, [220.0, 261.63, 329.63]), (87.31, [174.61, 220.0, 261.63]),
                   (130.81, [261.63, 329.63, 392.0]), (98.0, [196.0, 246.94, 293.66])],
    "bright": [(130.81, [261.63, 329.63, 392.0]), (98.0, [196.0, 246.94, 293.66]),
               (110.0, [220.0, 277.18, 329.63]), (116.54, [233.08, 293.66, 349.23])],
    "tense": [(82.41, [164.81, 196.0, 246.94]), (87.31, [174.61, 207.65, 261.63]),
              (92.5, [185.0, 220.0, 277.18]), (82.41, [164.81, 196.0, 246.94])],
}


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


def build(out_dir: Path, bpm: int = 100, chord_set: str = "minor-lift",
          gain: float = 0.42, duck: float = 0.6) -> tuple[Path, Path]:
    timeline = json.loads((out_dir / "timeline.json").read_text())
    end, impact, scenes = timeline["end"], timeline["impact"], timeline["scenes"]
    n = int(end * SR)
    rng = np.random.default_rng(3)

    def lowpass(x, hz, order=2):
        return sosfilt(butter(order, hz, "low", fs=SR, output="sos"), x)

    def highpass(x, hz, order=2):
        return sosfilt(butter(order, hz, "high", fs=SR, output="sos"), x)

    def bandpass(x, lo, hi, order=2):
        return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x)

    def place(track, sound, at, gain=1.0):
        i = int(at * SR)
        if i >= len(track):
            return
        j = min(len(track), i + len(sound))
        track[i:j] += sound[: j - i] * gain

    def env(length, attack, decay):
        t = np.arange(length) / SR
        return np.minimum(1, t / max(attack, 1e-4)) * np.exp(-t / decay)

    # --- voice ---------------------------------------------------------------------
    voice = np.zeros(n)
    for key, (start, _length) in timeline["vo"].items():
        line = _read(out_dir / "vo" / f"{key}.wav")
        line = highpass(line, 70)
        line = line / (np.max(np.abs(line)) + 1e-9) * 0.9
        line = np.tanh(line * 1.6) / np.tanh(1.6)   # gentle compression: evens out loud and soft words
        place(voice, line, start)

    # --- music ---------------------------------------------------------------------
    beat_len = 60 / bpm
    bar_len = 4 * beat_len
    chords = CHORDS.get(chord_set, CHORDS["minor-lift"])
    music = np.zeros((n, 2))

    def mono_to(track, sound, at, gain=1.0, pan=0.0):
        left, right = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        for channel, g in ((0, left), (1, right)):
            column = np.zeros(n)
            place(column, sound, at, gain * g * 1.41)
            track[:, channel] += column

    def kick():
        m = int(0.45 * SR)
        t = np.arange(m) / SR
        freq = 45 + 110 * np.exp(-t * 28)
        phase = 2 * np.pi * np.cumsum(freq) / SR
        return np.sin(phase) * np.exp(-t * 7) + 0.25 * np.sin(phase * 2) * np.exp(-t * 30)

    def snare():
        m = int(0.3 * SR)
        noise = bandpass(rng.standard_normal(m), 1200, 7000) * env(m, 0.001, 0.09)
        t = np.arange(m) / SR
        return 0.7 * noise + 0.4 * (np.sin(2 * np.pi * 190 * t) * np.exp(-t * 25))

    def hat(open_=False):
        m = int((0.25 if open_ else 0.06) * SR)
        return highpass(rng.standard_normal(m), 7500) * env(m, 0.0005, 0.08 if open_ else 0.018)

    def saw(freq, m, detune=0.0):
        t = np.arange(m) / SR
        out = np.zeros(m)
        for k in range(1, 14):
            out += np.sin(2 * np.pi * k * freq * (1 + detune) * t) / k
        return out

    def boom():
        m = int(2.2 * SR)
        t = np.arange(m) / SR
        freq = 32 + 90 * np.exp(-t * 6)
        sub = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 1.6)
        crash = lowpass(rng.standard_normal(m), 6000) * env(m, 0.002, 0.7) * 0.35
        return sub + crash

    def riser(length):
        m = int(length * SR)
        noise = rng.standard_normal(m)
        out = np.zeros(m)
        chunks = 24
        for c in range(chunks):       # the filter opens as it rises
            a, b = c * m // chunks, (c + 1) * m // chunks
            hz = 400 * (18 ** (c / chunks))
            out[a:b] = bandpass(noise[a:b], hz * 0.6, min(hz * 1.6, 20000))
        return out * np.linspace(0, 1, m) ** 2

    def whoosh(length=0.55):
        m = int(length * SR)
        shape = np.sin(np.linspace(0, np.pi, m)) ** 2
        return bandpass(rng.standard_normal(m), 600, 5000) * shape

    # Tension before the drop: a low drone, ticking hats, a riser into the impact.
    drone_n = max(1, int(impact * SR))
    t = np.arange(drone_n) / SR
    drone = lowpass(saw(55, drone_n, 0.003) + saw(55, drone_n, -0.004), 300) * np.minimum(1, t / 1.5) * 0.18
    mono_to(music, drone, 0.0, 1.0)
    tick = 0.6
    while tick < impact - 0.3:
        mono_to(music, hat(), tick, 0.22 + 0.25 * tick / max(impact, 1e-6),
                pan=0.3 if int(tick / (beat_len / 2)) % 2 else -0.3)
        tick += beat_len / 2 if tick < impact * 0.55 else beat_len / 4
    mono_to(music, riser(3.0), max(0.0, impact - 3.0), 0.22)

    # The drop: an impact, then the groove until the sign-off.
    groove_end = scenes[-1][1] + 3.2
    mono_to(music, boom(), impact, 0.9)
    beat_time, index = impact, 0
    while beat_time < groove_end:
        bar_pos = index % 4
        mono_to(music, kick(), beat_time, 0.75)
        if bar_pos in (1, 3):
            mono_to(music, snare(), beat_time, 0.32)
        mono_to(music, hat(open_=bar_pos == 3), beat_time + beat_len / 2, 0.16, pan=0.25)
        beat_time += beat_len
        index += 1

    # Bass, pad and a soft arpeggio following the chords.
    bar_time, chord_index = impact, 0
    while bar_time < groove_end:
        root, triad = chords[chord_index % len(chords)]
        n_bar = int(bar_len * SR)
        tb = np.arange(n_bar) / SR
        pad = sum(saw(f, n_bar, d) for f in triad for d in (-0.004, 0.004))
        pad = lowpass(pad, 1400) * np.minimum(1, tb / 0.6) * np.minimum(1, (bar_len - tb) / 0.3) * 0.035
        mono_to(music, pad, bar_time, 1.0, pan=-0.2)
        mono_to(music, pad, bar_time, 0.9, pan=0.2)
        for eighth in range(8):
            m = int(beat_len / 2 * SR)
            te = np.arange(m) / SR
            bass = lowpass(saw(root / 2, m), 400) * env(m, 0.005, 0.18) * 0.28
            mono_to(music, bass, bar_time + eighth * beat_len / 2, 1.0)
            note = triad[[0, 1, 2, 1][eighth % 4]] * 2
            pluck = (np.sin(2 * np.pi * note * te) + 0.3 * np.sin(4 * np.pi * note * te)) * env(m, 0.002, 0.12) * 0.06
            mono_to(music, pluck, bar_time + eighth * beat_len / 2, 1.0, pan=0.5 if eighth % 2 else -0.5)
        bar_time += bar_len
        chord_index += 1

    # Sidechain pump: the bed breathes with the kick.
    pump = np.ones(n)
    beat_time = impact
    while beat_time < groove_end:
        i = int(beat_time * SR)
        m = min(int(beat_len * SR), n - i)
        if m > 0:
            pump[i:i + m] = np.minimum(pump[i:i + m],
                                       0.55 + 0.45 * np.minimum(1, (np.arange(m) / SR) / (beat_len * 0.55)))
        beat_time += beat_len
    music *= pump[:, None]

    # Transitions and the closing hit.
    for _name, start in scenes[3:]:
        mono_to(music, whoosh(), max(0.0, start - 0.2), 0.12)
    mono_to(music, boom(), scenes[-1][1] + 0.3, 0.55)
    tail_n = int((end - groove_end + 0.5) * SR)
    if tail_n > 0:
        tf = np.arange(tail_n) / SR
        tail = lowpass(sum(saw(f, tail_n, d) for f in chords[0][1] for d in (-0.004, 0.004)), 1200)
        tail *= np.minimum(1, tf / 0.2) * np.exp(-tf / 1.4) * 0.05
        mono_to(music, tail, max(0.0, groove_end - 0.5), 1.0)

    # Keep the voice on top: duck the music while someone is talking.
    level = lowpass(np.abs(voice), 6)
    level = level / (level.max() + 1e-9)
    music *= (1 - duck * np.clip(level * 3, 0, 1))[:, None]
    music /= np.max(np.abs(music)) + 1e-9
    music *= gain

    mix = music + voice[:, None] * 0.95
    fade_out = np.ones(n)
    fade_n = int(0.8 * SR)
    fade_out[-fade_n:] = np.linspace(1, 0, fade_n)
    mix *= fade_out[:, None]
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    mix *= 0.93 / (np.max(np.abs(mix)) + 1e-9)

    mix_path, voice_path = out_dir / "mix.wav", out_dir / "voice.wav"
    _write(mix_path, mix)
    _write(voice_path, np.repeat(voice[:, None] * 0.9, 2, axis=1) * fade_out[:, None])
    return mix_path, voice_path


if __name__ == "__main__":
    import sys

    argv = sys.argv[1:]
    build(Path(argv[0]),
          int(argv[1]) if len(argv) > 1 else 100,
          argv[2] if len(argv) > 2 else "minor-lift",
          float(argv[3]) if len(argv) > 3 else 0.42,
          float(argv[4]) if len(argv) > 4 else 0.6)
    print("audio written")
