"""The images backend: screenshots you already have.

The quickest way in — point at a folder, name the regions you care about, and you are
rendering. Regions are given in the config because there is no live app to measure.

    [capture]
    backend = "images"
    from = "screenshots"          # relative to the config file
    size = [1440, 900]            # logical size of those images
    scale = 2                     # they are 2880x1800 on disk

    [capture.regions]
    chart = [40, 220, 600, 320]
"""

from __future__ import annotations

import shutil
from pathlib import Path

from . import write_regions

SUFFIXES = (".png", ".jpg", ".jpeg", ".webp")


def run(config) -> None:
    source = config.capture.get("from")
    if not source:
        raise SystemExit("[capture] backend = \"images\" needs from = \"<folder>\"")
    folder = Path(source)
    folder = folder if folder.is_absolute() else config.dir / folder
    if not folder.is_dir():
        raise SystemExit(f"no such folder: {folder}")

    shots = config.dir / "shots"
    shots.mkdir(parents=True, exist_ok=True)
    found = []
    for path in sorted(folder.iterdir()):
        if path.suffix.lower() not in SUFFIXES:
            continue
        target = shots / f"{path.stem}.png"
        if path.suffix.lower() == ".png":
            shutil.copy(path, target)
        else:
            from PySide6.QtGui import QImage
            image = QImage(str(path))
            if image.isNull():
                continue
            image.save(str(target))
        found.append(path.stem)
    if not found:
        raise SystemExit(f"no images in {folder}")

    size = config.capture.get("size")
    if not size:
        from PySide6.QtGui import QImage
        first = QImage(str(shots / f"{found[0]}.png"))
        size = [first.width() // config.capture_scale, first.height() // config.capture_scale]
    write_regions(config.dir, list(size), dict(config.capture.get("regions", {})))
    print(f"  {len(found)} shots: {', '.join(found[:8])}{' …' if len(found) > 8 else ''}")
