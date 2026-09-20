import os
import wave
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

CONFIG = """
[brand]
name = "Test App"
tagline = "A tagline."

[format]
targets = ["reels", "x"]

[[scene]]
key = "hook"
say = "One two three."
gap = 0.5
type = "title"
  [[scene.line]]
  text = "Hello"

[[scene]]
key = "reveal"
say = "Meet Test App."
gap = 0.25
type = "reveal"
impact = true

[[scene]]
key = "outro"
say = "Test App. Ship it."
gap = 0.3
type = "outro"
"""


def _silence(path: Path, seconds: float) -> None:
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(b"\0\0" * int(24000 * seconds))


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """A minimal reel with pre-rendered 'narration', so tests never need a TTS model."""
    (tmp_path / "sizzle.toml").write_text(CONFIG)
    vo = tmp_path / "vo"
    vo.mkdir()
    for key, seconds in (("hook", 1.5), ("reveal", 1.0), ("outro", 2.0)):
        _silence(vo / f"{key}.wav", seconds)
    return tmp_path
