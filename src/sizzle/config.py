"""reel.toml — one entry per beat of the video — parsed into the settings every module reads."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field, replace
from pathlib import Path

from PySide6.QtGui import QColor

from .targets import Target, resolve


@dataclass
class Brand:
    name: str = "The App"
    tagline: str = ""
    logo: Path | None = None
    outro_line: str = ""
    outro_features: list[str] = field(default_factory=list)
    font: str = "Noto Sans"


@dataclass
class Theme:
    accent: QColor = field(default_factory=lambda: QColor("#4ea4f6"))
    second: QColor = field(default_factory=lambda: QColor("#7383f7"))
    third: QColor = field(default_factory=lambda: QColor("#b28cff"))
    warn: QColor = field(default_factory=lambda: QColor("#e0662f"))
    text: QColor = field(default_factory=lambda: QColor("#f2f6fb"))
    soft: QColor = field(default_factory=lambda: QColor("#b5c6d8"))
    muted: QColor = field(default_factory=lambda: QColor("#7f91a4"))
    background: tuple[QColor, QColor, QColor] = field(
        default_factory=lambda: (QColor("#08101d"), QColor("#0c1a2e"), QColor("#070d18")))

    def named(self, name: str | None) -> QColor:
        """Colour by theme name ('accent', 'soft', …) or by literal '#rrggbb'."""
        if not name:
            return self.text
        if name.startswith("#"):
            return QColor(name)
        return getattr(self, name, self.text)


@dataclass
class Audio:
    voice: str = "af_heart"
    speed: float = 1.05
    bpm: int = 100
    chords: str = "minor-lift"
    music: float = 0.42
    duck: float = 0.6
    tail: float = 2.4


@dataclass
class Beat:
    """One entry of the video: what is said, and what is drawn while it is said."""
    key: str
    say: str = ""
    gap: float = 0.45
    lead: float = 0.25          # the visuals start this long before the line
    caption: bool = False       # burn word-synced captions for this line
    type: str = "showcase"
    impact: bool = False        # the drop: music hit, screen darkens into it
    data: dict = field(default_factory=dict)   # everything the scene type needs


@dataclass
class Config:
    dir: Path
    brand: Brand
    theme: Theme
    audio: Audio
    targets: list[Target]
    active: Target
    capture: dict
    beats: list[Beat]
    overrides: dict

    # The active target decides the frame; everything else reads these.
    @property
    def width(self) -> int:
        return self.active.width

    @property
    def height(self) -> int:
        return self.active.height

    @property
    def fps(self) -> int:
        return self.active.fps

    @property
    def capture_scale(self) -> int:
        return int(self.capture.get("scale", 2))

    def for_target(self, target: Target) -> "Config":
        """The same reel, aimed at another platform."""
        return replace(self, active=target)

    def tweak(self, key: str, fallback):
        """A [target.<name>] override, falling back to the shared value."""
        return self.overrides.get(self.active.name, {}).get(key, fallback)

    @property
    def shots(self) -> Path:
        return self.dir / "shots"

    @property
    def vo(self) -> Path:
        return self.dir / "vo"

    def spoken(self) -> list[tuple[str, str]]:
        return [(b.key, b.say) for b in self.beats if b.say]


def _color(raw, fallback: str) -> QColor:
    return QColor(raw) if raw else QColor(fallback)


def load(path: str | Path) -> Config:
    path = Path(path)
    if path.is_dir():
        found = next((path / name for name in ("sizzle.toml", "reel.toml") if (path / name).exists()), None)
        if found is None:
            raise SystemExit(f"no sizzle.toml in {path}")
        path = found
    raw = tomllib.loads(path.read_text())
    here = path.parent

    b = raw.get("brand", {})
    logo = b.get("logo")
    brand = Brand(
        name=b.get("name", "The App"),
        tagline=b.get("tagline", ""),
        logo=(here / logo) if logo else None,
        outro_line=b.get("outro_line", ""),
        outro_features=b.get("outro_features", []),
        font=b.get("font", "Noto Sans"),
    )

    t = raw.get("theme", {})
    bg = t.get("background", ["#08101d", "#0c1a2e", "#070d18"])
    theme = Theme(
        accent=_color(t.get("accent"), "#4ea4f6"),
        second=_color(t.get("second"), "#7383f7"),
        third=_color(t.get("third"), "#b28cff"),
        warn=_color(t.get("warn"), "#e0662f"),
        text=_color(t.get("text"), "#f2f6fb"),
        soft=_color(t.get("soft"), "#b5c6d8"),
        muted=_color(t.get("muted"), "#7f91a4"),
        background=tuple(QColor(c) for c in bg),
    )

    a = raw.get("audio", {})
    audio = Audio(voice=a.get("voice", "af_heart"), speed=a.get("speed", 1.05), bpm=a.get("bpm", 100),
                  chords=a.get("chords", "minor-lift"), music=a.get("music", 0.42),
                  duck=a.get("duck", 0.6), tail=a.get("tail", 2.4))

    f = raw.get("format", {})
    fps = f.get("fps", 30)
    wanted = f.get("targets") or [f.get("size", "reels")]
    targets = [resolve(name, fps) for name in wanted]

    c = raw.get("capture", {})
    beats = []
    for entry in raw.get("scene", []):
        known = {"key", "say", "gap", "lead", "caption", "type", "impact"}
        beats.append(Beat(
            key=entry["key"], say=entry.get("say", ""), gap=entry.get("gap", 0.45),
            lead=entry.get("lead", 0.25), caption=entry.get("caption", False),
            type=entry.get("type", "showcase"), impact=entry.get("impact", False),
            data={k: v for k, v in entry.items() if k not in known},
        ))
    if not beats:
        raise SystemExit(f"{path}: no [[scene]] entries")

    return Config(dir=here, brand=brand, theme=theme, audio=audio, targets=targets, active=targets[0],
                  capture=c, beats=beats, overrides=raw.get("target", {}))
