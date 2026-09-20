"""Where a video is going, and what that platform does to it.

A target is not just a canvas size. Every short-form platform paints its own interface
over the video — a caption and username along the bottom, a column of buttons up the
right edge — so each one carries the margins that words must stay out of. Captions,
chips and the brand bar read those margins instead of hardcoding a position.
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Safe:
    """Fractions of the frame the platform's own interface can cover."""
    top: float = 0.0
    right: float = 0.0
    bottom: float = 0.0
    left: float = 0.0


@dataclass(frozen=True)
class Target:
    name: str
    width: int
    height: int
    fps: int = 30
    max_duration: float | None = None      # seconds the platform accepts
    safe: Safe = Safe()
    note: str = ""

    @property
    def portrait(self) -> bool:
        return self.height > self.width

    @property
    def caption_y(self) -> float:
        """Caption baseline, clear of the platform's own bottom furniture."""
        return min(0.82, max(0.62, 1 - self.safe.bottom - 0.10))

    @property
    def caption_width(self) -> float:
        return 1 - self.safe.left - self.safe.right - 0.12

    @property
    def bar_y(self) -> float:
        return max(0.09, self.safe.top + 0.04)

    @property
    def chip_y(self) -> float:
        return self.bar_y + 0.055      # the scene chip rides just under the brand bar

    # The band a screenshot may occupy: under the chip, above the caption block.
    @property
    def content_top(self) -> float:
        return self.chip_y + 0.05

    @property
    def content_bottom(self) -> float:
        return self.caption_y - 0.12

    @property
    def content_height(self) -> float:
        return self.content_bottom - self.content_top

    @property
    def content_width(self) -> float:
        return 1 - self.safe.left - self.safe.right - 0.06

    def remap_y(self, y: float) -> float:
        """A y written for the reference portrait frame, placed in this target's band."""
        share = (y - REFERENCE.content_top) / REFERENCE.content_height
        return self.content_top + share * self.content_height

    def resized(self, width: int, height: int, fps: int | None = None) -> "Target":
        return replace(self, width=width, height=height, fps=fps or self.fps)


# Margins are measured from each app's own overlay, rounded up a little: being
# conservative costs a few pixels of layout, being wrong buries the caption.
PRESETS: dict[str, Target] = {
    "reels": Target("reels", 1080, 1920, 30, 90,
                    Safe(top=0.08, right=0.14, bottom=0.18), "Instagram Reels"),
    "tiktok": Target("tiktok", 1080, 1920, 30, 600,
                     Safe(top=0.10, right=0.16, bottom=0.20), "TikTok"),
    "shorts": Target("shorts", 1080, 1920, 30, 60,
                     Safe(top=0.08, right=0.12, bottom=0.16), "YouTube Shorts"),
    "stories": Target("stories", 1080, 1920, 30, 60,
                      Safe(top=0.12, right=0.10, bottom=0.14), "Instagram/Facebook Stories"),
    "x": Target("x", 1920, 1080, 30, 140, Safe(), "X / Twitter timeline"),
    "x-square": Target("x-square", 1080, 1080, 30, 140, Safe(), "X / Twitter, square"),
    "youtube": Target("youtube", 1920, 1080, 30, None, Safe(), "YouTube, landscape"),
    "linkedin": Target("linkedin", 1080, 1350, 30, 600, Safe(bottom=0.06), "LinkedIn feed, 4:5"),
    "square": Target("square", 1080, 1080, 30, None, Safe(), "generic square"),
    "landscape": Target("landscape", 1920, 1080, 30, None, Safe(), "generic 16:9"),
    "portrait": Target("portrait", 1080, 1920, 30, None, Safe(), "generic 9:16, no platform UI"),
}

# Authors design against Reels; every other target is mapped from it.
REFERENCE = PRESETS["reels"]

ASPECTS = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080), "4:5": (1080, 1350)}


def resolve(name: str, fps: int = 30) -> Target:
    """A preset name, an aspect ratio like '9:16', or an explicit '1080x1920'."""
    key = str(name).strip().lower()
    if key in PRESETS:
        preset = PRESETS[key]
        return preset if fps == preset.fps else replace(preset, fps=fps)
    if key in ASPECTS:
        width, height = ASPECTS[key]
        return Target(key.replace(":", "x"), width, height, fps)
    if "x" in key:
        width, height = (int(v) for v in key.split("x"))
        return Target(key, width, height, fps)
    raise SystemExit(f"unknown target {name!r}; known: {', '.join(sorted(PRESETS))}")


def check_duration(target: Target, seconds: float) -> str | None:
    """Warn before rendering, not after — a full render is minutes."""
    if target.max_duration and seconds > target.max_duration:
        return (f"{target.name}: {seconds:.0f}s exceeds the {target.max_duration:.0f}s limit "
                f"({target.note or target.name}); trim a line or shorten the gaps")
    return None
