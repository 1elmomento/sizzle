"""Frame rendering: one function of time, then either a few stills or every frame into ffmpeg."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

from PySide6.QtGui import QColor, QImage, QPainter

from . import captions as caption_layer
from . import scenes as archetypes
from .card import Regions
from .config import Config
from .draw import Canvas, span
from .timing import Timeline


def load_custom(config: Config) -> dict:
    """Project-supplied scene functions: `draw_<type>(ctx, painter, t)` in reel/scenes.py."""
    path = config.dir / "scenes.py"
    if not path.exists():
        return {}
    spec = importlib.util.spec_from_file_location("reel_project_scenes", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return {name[5:]: fn for name, fn in vars(module).items() if name.startswith("draw_") and callable(fn)}


class Reel:
    def __init__(self, config: Config):
        self.config = config
        self.canvas = Canvas(config)
        self.timeline = Timeline(config)
        self.regions = Regions(config.dir / "regions.json")
        self.custom = load_custom(config)
        self.scenes = []
        for beat_span in self.timeline.order:
            ctx = archetypes.Ctx(self.canvas, self.timeline, self.regions, beat_span)
            draw = archetypes.resolve(beat_span.beat.type, self.custom)
            overlap = beat_span.beat.data.get("overlap", 0.35 if beat_span.beat.type == "showcase" else 0.0)
            self.scenes.append((ctx, draw, overlap))
        self.bar_from, self.bar_to = self._bar_window()

    def _bar_window(self):
        """The small logo bar runs through the feature scenes: after the reveal, before the sign-off."""
        wanted = []
        seen_impact = False
        for s in self.timeline.order:
            if s.beat.impact:
                seen_impact = True
                continue
            default = seen_impact and s.beat.type in ("showcase", "hold")
            if s.beat.data.get("bar", default):
                wanted.append(s)
        if not wanted:
            return None, None
        return wanted[0].start, wanted[-1].end

    def frame(self, t: float) -> QImage:
        c = self.canvas
        img = QImage(c.W, c.H, QImage.Format.Format_ARGB32_Premultiplied)
        p = QPainter(img)
        for hint in (QPainter.RenderHint.Antialiasing, QPainter.RenderHint.SmoothPixmapTransform,
                     QPainter.RenderHint.TextAntialiasing):
            p.setRenderHint(hint)
        impact = self.timeline.impact
        darken = 0.5 * span(t, impact - 0.6, impact) * (1 - span(t, impact, impact + 0.2))
        c.background(p, t, darken)
        for ctx, draw, overlap in self.scenes:
            if ctx.span.start - 0.01 <= t < ctx.span.end + overlap:
                draw(ctx, p, t)
        if self.bar_from is not None:
            c.brand_bar(p, t, span(t, self.bar_from, self.bar_from + 0.3)
                        * (1 - span(t, self.bar_to - 0.2, self.bar_to + 0.2)))
        caption_layer.draw(c, self.timeline, p, t)
        fade = 1 - span(t, 0, 0.25)
        if fade > 0:
            p.fillRect(0, 0, c.W, c.H, QColor(0, 0, 0, int(255 * fade)))
        p.end()
        return img

    # --- outputs ---------------------------------------------------------------------

    def stills(self, times: list[float], out: Path | None = None) -> list[Path]:
        out = out or self.config.dir / "stills"
        out.mkdir(parents=True, exist_ok=True)
        written = []
        for t in times:
            path = out / f"t{t:06.2f}.png"
            img = self.frame(t)
            img.save(str(path))
            written.append(path)
        return written

    def contact_sheet(self, count: int = 12, out: Path | None = None) -> list[Path]:
        """One still per scene (or `count` evenly spread) — the quickest way to review pacing."""
        if count <= 0:
            times = [s.start + s.length * 0.55 for s in self.timeline.order]
        else:
            times = [self.timeline.end * (i + 0.5) / count for i in range(count)]
        return self.stills(times, out)

    def video(self, target: Path, *, crf: int = 17, preset: str = "slow") -> Path:
        frames = int(self.timeline.end * self.config.fps)
        ffmpeg = subprocess.Popen(
            ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgra",
             "-s", f"{self.config.width}x{self.config.height}", "-r", str(self.config.fps), "-i", "-",
             "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-pix_fmt", "yuv420p",
             "-movflags", "+faststart", str(target)],
            stdin=subprocess.PIPE)
        for i in range(frames):
            img = self.frame(i / self.config.fps)   # keep the image alive: constBits() points into it
            ffmpeg.stdin.write(bytes(img.constBits()))
            if i % 150 == 0:
                print(f"  frame {i}/{frames}", flush=True)
        ffmpeg.stdin.close()
        if ffmpeg.wait() != 0:
            raise SystemExit("ffmpeg failed")
        return target

    def cover(self, t: float, target: Path) -> Path:
        img = self.frame(t)
        img.save(str(target), None, 94)
        return target
