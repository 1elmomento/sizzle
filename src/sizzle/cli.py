"""The pipeline: narrate → capture → compose → score → mux.

    sizzle build video/                  everything, for every target
    sizzle narrate video/                (re)record the narration
    sizzle voices video/                 audition voices before committing to one
    sizzle capture video/                run the configured capture backend
    sizzle plan video/                   the timeline, and whether it fits each platform
    sizzle stills video/ --at 1.2,5,9    frames for review
    sizzle sheet video/                  one frame per scene
    sizzle video video/                  silent video per target
    sizzle audio video/                  music bed + mix
    sizzle mux video/                    the finished files and the cover
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from . import capture as capture_backends
from . import targets as target_presets

HERE = Path(__file__).resolve().parent
SHARE = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "sizzle"


def _python(env_var: str, hints: list[Path], needs: str) -> str:
    """An interpreter that can import `needs`: the env override, a known venv, or this one."""
    override = os.environ.get(env_var)
    if override:
        return override
    for hint in hints:
        if hint.exists() and subprocess.run([str(hint), "-c", f"import {needs}"],
                                            capture_output=True).returncode == 0:
            return str(hint)
    return sys.executable


def tts_python() -> str:
    return _python("SIZZLE_TTS_PYTHON", [SHARE / "tts/bin/python"], "kokoro_onnx")


def audio_python() -> str:
    """numpy and scipy, kept out of the app's own environment."""
    return _python("SIZZLE_AUDIO_PYTHON", [SHARE / "tts/bin/python"], "scipy")


def app_python(config) -> str:
    hints = [parent / ".venv/bin/python" for parent in [config.dir, *config.dir.parents][:5]]
    return _python("SIZZLE_APP_PYTHON", hints, "PySide6")


# ffmpeg is a system package; pip cannot supply it. Say so once, up front, rather than
# letting subprocess raise FileNotFoundError six frames deep after a long render.
NEEDS_FFMPEG = {"build", "video", "mux"}

INSTALL_FFMPEG = {"linux": "apt install ffmpeg  (or dnf/pacman)",
                  "darwin": "brew install ffmpeg",
                  "win32": "winget install ffmpeg"}


def require_ffmpeg() -> None:
    if shutil.which("ffmpeg"):
        return
    hint = INSTALL_FFMPEG.get(sys.platform, "see https://ffmpeg.org/download.html")
    raise SystemExit(f"ffmpeg is not on your PATH — sizzle encodes and muxes with it.\n  {hint}")


def _run(cmd: list[str], **kw) -> None:
    print("·", " ".join(str(c) for c in cmd), flush=True)
    if subprocess.run([str(c) for c in cmd], **kw).returncode != 0:
        raise SystemExit(f"failed: {cmd[0]}")


def _reel(config):
    from .render import Reel
    return Reel(config)


def _slug(config) -> str:
    return config.brand.name.lower().replace(" ", "-").replace("/", "-")


def _stem(config, target) -> str:
    """One target keeps a clean name; several get the platform in the filename."""
    return _slug(config) if len(config.targets) == 1 else f"{_slug(config)}-{target.name}"


# --- steps -----------------------------------------------------------------------------


def step_narrate(config) -> None:
    lines = [[b.key, b.say] for b in config.beats if b.say]
    if not lines:
        print("nothing to narrate")
        return
    path = config.dir / "lines.json"
    path.write_text(json.dumps(lines, indent=1))
    _run([tts_python(), HERE / "narrate.py", "lines", path, config.vo, config.audio.voice, config.audio.speed])


def step_voices(config, text: str | None, wanted: str | None) -> None:
    text = text or next((b.say for b in config.beats if b.say), "Hello.")
    out = config.dir / "voice-samples"
    _run([tts_python(), HERE / "narrate.py", "samples", out, text] + ([wanted] if wanted else []))
    print(f"auditions in {out}")


def step_capture(config) -> None:
    capture_backends.run(config, app_python(config), _run)


def step_plan(config) -> None:
    reel = _reel(config)
    print(f"{'scene':12s} {'type':10s} {'in':>7s} {'vo':>7s} {'out':>7s}  line")
    for s in reel.timeline.order:
        print(f"{s.key:12s} {s.beat.type:10s} {s.start:7.2f} {s.vo:7.2f} {s.end:7.2f}  {s.beat.say[:52]}")
    print(f"{'impact':>31s} {reel.timeline.impact:7.2f}")
    print(f"total {reel.timeline.end:.2f}s")
    for target in config.targets:
        frames = int(reel.timeline.end * target.fps)
        warning = target_presets.check_duration(target, reel.timeline.end)
        print(f"  {target.name:10s} {target.width}x{target.height} {target.fps}fps  {frames} frames"
              + (f"\n    ! {warning}" if warning else ""))
    reel.timeline.dump(config.dir / "timeline.json")


def step_stills(config, at: str | None) -> None:
    reel = _reel(config)
    reel.timeline.dump(config.dir / "timeline.json")
    times = [float(v) for v in at.split(",")] if at else None
    out = config.dir / "stills" / config.active.name
    paths = reel.stills(times, out) if times else reel.contact_sheet(0, out)
    for path in paths:
        print(" ", path)


def step_video(config) -> None:
    for target in config.targets:
        aimed = config.for_target(target)
        reel = _reel(aimed)
        reel.timeline.dump(config.dir / "timeline.json")
        warning = target_presets.check_duration(target, reel.timeline.end)
        if warning:
            print(f"! {warning}")
        print(f"rendering {target.name}: {reel.timeline.end:.1f}s at {target.width}x{target.height}")
        reel.video(config.dir / f"silent-{target.name}.mp4")
        at = config.cover_at if config.cover_at is not None else reel.timeline.impact + 1.4
        reel.cover(at, config.dir / f"cover-{target.name}.jpg")


def step_audio(config, seed: int | None = None) -> None:
    """`--seed` rerolls the score without touching anything else."""
    if seed is not None:
        config.audio.seed = seed
    if not (config.dir / "timeline.json").exists():
        _reel(config).timeline.dump(config.dir / "timeline.json")
    _run([audio_python(), HERE / "music.py", config.dir, config.audio.bpm,
          config.audio.chords, config.audio.music, config.audio.duck, config.score_seed,
          config.audio.style])


def step_mux(config, out: Path | None) -> None:
    out = out or config.dir / "out"
    out.mkdir(parents=True, exist_ok=True)
    for target in config.targets:
        silent = config.dir / f"silent-{target.name}.mp4"
        if not silent.exists():
            raise SystemExit(f"no {silent.name} — run the video step first")
        stem = _stem(config, target)
        for suffix, track in (("music", "mix.wav"), ("voice-only", "voice.wav")):
            if not (config.dir / track).exists():
                continue
            target_file = out / f"{stem}-{suffix}.mp4"
            _run(["ffmpeg", "-y", "-loglevel", "error", "-i", silent, "-i", config.dir / track,
                  "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", target_file])
            print(" ", target_file)
        cover = config.dir / f"cover-{target.name}.jpg"
        if cover.exists():
            shutil.copy(cover, out / f"{stem}-cover.jpg")
            print(" ", out / f"{stem}-cover.jpg")


def step_build(config, out: Path | None) -> None:
    step_narrate(config)
    step_capture(config)
    step_plan(config)
    step_video(config)
    step_audio(config)
    step_mux(config, out)


# --- entry point -----------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="sizzle", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("step", choices=["build", "narrate", "voices", "capture", "plan",
                                         "stills", "sheet", "video", "audio", "mux"])
    parser.add_argument("dir", nargs="?", default=".", help="the folder holding sizzle.toml")
    parser.add_argument("--targets", help="override [format] targets, e.g. reels,x")
    parser.add_argument("--at", help="stills: comma-separated seconds")
    parser.add_argument("--out", help="where the finished files go (default <dir>/out)")
    parser.add_argument("--text", help="voices: the line to audition")
    parser.add_argument("--voices", help="voices: comma-separated names")
    parser.add_argument("--seed", type=int, help="audio: reroll the score with another seed")
    args = parser.parse_args(argv)

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if args.step in NEEDS_FFMPEG:
        require_ffmpeg()
    from .config import load
    config = load(args.dir)
    if args.targets:
        chosen = [target_presets.resolve(name, config.targets[0].fps) for name in args.targets.split(",")]
        config.targets = chosen
        config.active = chosen[0]
    out = Path(args.out) if args.out else None

    steps = {"build": lambda: step_build(config, out), "narrate": lambda: step_narrate(config),
             "voices": lambda: step_voices(config, args.text, args.voices),
             "capture": lambda: step_capture(config), "plan": lambda: step_plan(config),
             "stills": lambda: step_stills(config, args.at), "sheet": lambda: step_stills(config, None),
             "video": lambda: step_video(config), "audio": lambda: step_audio(config, args.seed),
             "mux": lambda: step_mux(config, out)}
    steps[args.step]()


if __name__ == "__main__":
    main()
