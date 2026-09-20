"""sizzle — a promo-reel engine: narration, motion graphics, music and mux.

Everything here is project-independent. A project supplies three things:
a `reel.toml` (the beats of the video), a capture script (screenshots plus
named regions) and, optionally, a `scenes.py` with custom drawing.
"""

__all__ = ["config", "timing", "draw", "glyphs", "card", "captions", "scenes", "render", "music", "narrate"]
