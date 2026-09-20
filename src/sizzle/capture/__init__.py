"""Getting pictures of the product.

This is the only part of a reel that is genuinely specific to the thing being
advertised, so it is a choice of backend rather than a file everyone must write:

    script   run a Python file that drives the app (full control, needs Python)
    images   use screenshots that already exist
    web      drive a real browser from config (no Python)
    video    cut frames out of an existing screen recording (works for anything)

Every backend honours the same contract: write `shots/<name>.png` at
`[capture] scale` times logical size, and `regions.json` mapping names to
`[x, y, w, h]` in logical coordinates.
"""

from __future__ import annotations

import json
from pathlib import Path

BACKENDS = ("script", "images", "web", "video")


def write_regions(out: Path, size: list[int], regions: dict) -> Path:
    path = out / "regions.json"
    path.write_text(json.dumps({"size": size, **regions}, indent=1))
    return path


def run(config, app_python: str, runner) -> None:
    """Dispatch to the configured backend. `runner` runs a subprocess for us."""
    kind = config.capture.get("backend")
    if kind is None:
        kind = "script" if config.capture.get("script") else None
    if kind is None:
        print("no [capture] backend configured — skipping")
        return
    if kind not in BACKENDS:
        raise SystemExit(f"unknown capture backend {kind!r}; choose one of {', '.join(BACKENDS)}")
    if kind == "script":
        from . import script
        script.run(config, app_python, runner)
    elif kind == "images":
        from . import images
        images.run(config)
    else:
        raise SystemExit(f"the {kind!r} capture backend is not built yet — use 'script' or 'images'")
