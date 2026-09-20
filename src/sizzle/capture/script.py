"""The script backend: run a Python file that drives the app and writes the contract.

Full control, and the only option for a desktop app whose internals you want to pose
deliberately. The script runs under the project's own interpreter, not sizzle's.
"""

from __future__ import annotations

import os
from pathlib import Path


def run(config, app_python: str, runner) -> None:
    raw = config.capture.get("script")
    if not raw:
        raise SystemExit("[capture] backend = \"script\" needs a script = \"...\" path")
    path = Path(raw)
    script = path if path.is_absolute() else config.dir / path
    if not script.exists():
        raise SystemExit(f"capture script not found: {script}")
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_SCALE_FACTOR=str(config.capture_scale))
    runner([app_python, script, config.dir], env=env)
