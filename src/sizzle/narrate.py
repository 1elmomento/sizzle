"""Narration with Kokoro: one 16-bit WAV per line, plus voice auditions.

Standalone on purpose — it imports nothing from the rest of sizzle, so it can run
in the small TTS environment (kokoro-onnx, soundfile, espeakng-loader) while the
rest of the pipeline runs wherever PySide6 lives.

    python narrate.py lines <lines.json> <out_dir> [voice] [speed]
    python narrate.py samples <out_dir> "some text" [voice,voice,...]
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import urllib.request
from pathlib import Path

HOME = Path(os.environ.get("SIZZLE_MODELS", Path.home() / ".local/share/kokoro"))
FILES = {
    "kokoro-v1.0.onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
    "voices-v1.0.bin": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
}
VOICES = ["af_heart", "af_bella", "af_nicole", "af_sarah", "af_sky", "bf_emma", "bf_isabella",
          "am_michael", "am_adam", "bm_george"]


def ensure_models() -> tuple[Path, Path]:
    """Download the model once, into a shared cache — never into a project."""
    HOME.mkdir(parents=True, exist_ok=True)
    for name, url in FILES.items():
        target = HOME / name
        if target.exists() and target.stat().st_size > 1_000_000:
            continue
        print(f"downloading {name} → {target}", flush=True)
        tmp = target.with_suffix(target.suffix + ".part")
        urllib.request.urlretrieve(url, tmp)
        tmp.rename(target)
    return HOME / "kokoro-v1.0.onnx", HOME / "voices-v1.0.bin"


def _kokoro():
    import espeakng_loader
    from kokoro_onnx import EspeakConfig, Kokoro

    model, voices = ensure_models()
    # espeak-ng mishandles long data paths (and resolves symlinks), so it reads a short copy.
    data = espeakng_loader.get_data_path()
    short = Path("/tmp/sizzle-espeak/espeak-ng-data")
    if len(str(data)) > 60 and not short.exists():
        short.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(data, short)
    if short.exists():
        data = short
    return Kokoro(str(model), str(voices),
                  espeak_config=EspeakConfig(lib_path=espeakng_loader.get_library_path(), data_path=str(data)))


def _say(kokoro, text: str, voice: str, speed: float):
    lang = "en-gb" if voice.startswith("b") else "en-us"
    return kokoro.create(text, voice=voice, speed=speed, lang=lang)


def lines(path: Path, out: Path, voice: str, speed: float) -> None:
    import numpy as np
    import soundfile as sf

    out.mkdir(parents=True, exist_ok=True)
    kokoro = _kokoro()
    for key, text in json.loads(Path(path).read_text()):
        samples, rate = _say(kokoro, text, voice, speed)
        # A breath either side keeps lines from butting against the music.
        samples = np.concatenate([np.zeros(int(0.05 * rate)), samples, np.zeros(int(0.1 * rate))])
        sf.write(str(out / f"{key}.wav"), samples, rate, subtype="PCM_16")
        print(f"  {key:10s} {len(samples) / rate:5.2f}s", flush=True)


def samples(out: Path, text: str, wanted: list[str], speed: float = 1.05) -> None:
    import soundfile as sf

    out.mkdir(parents=True, exist_ok=True)
    kokoro = _kokoro()
    for voice in wanted:
        audio, rate = _say(kokoro, text, voice, speed)
        sf.write(str(out / f"{voice}.wav"), audio, rate, subtype="PCM_16")
        print(f"  {voice}", flush=True)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "lines"
    if mode == "lines":
        lines(Path(sys.argv[2]), Path(sys.argv[3]),
              sys.argv[4] if len(sys.argv) > 4 else "af_heart",
              float(sys.argv[5]) if len(sys.argv) > 5 else 1.05)
    elif mode == "samples":
        samples(Path(sys.argv[2]), sys.argv[3],
                (sys.argv[4].split(",") if len(sys.argv) > 4 else VOICES[:6]))
    elif mode == "fetch":
        ensure_models()
    else:
        raise SystemExit(__doc__)
