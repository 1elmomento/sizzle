"""Films the app for the reel: screenshots plus the rectangles worth pointing at.

Contract: write shots/<name>.png and regions.json (logical coordinates) into sys.argv[1].
"""

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_SCALE_FACTOR", "2")

from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QWidget

HERE = Path(sys.argv[1])
SHOTS = HERE / "shots"
SHOTS.mkdir(exist_ok=True)
W, H = 1060, 1500
regions: dict[str, list[int]] = {}

app = QApplication([])
# win = build_the_window(fixture_data())          # never a real account
# win.resize(W, H)
# win.show()


def settle(times: int = 3) -> None:
    for _ in range(times):
        app.processEvents()


def shot(name: str) -> None:
    win.grab().save(str(SHOTS / f"{name}.png"))


def rect_of(widget: QWidget) -> list[int]:
    top_left = widget.mapTo(win, QPoint(0, 0))
    return [top_left.x(), top_left.y(), widget.width(), widget.height()]


# settle()
# shot("overview")
# regions["main_panel"] = rect_of(win.panel)
# regions["action_bar"] = rect_of(win.actions)
# regions["primary_button"] = rect_of(win.actions.primary)

(HERE / "regions.json").write_text(json.dumps({"size": [W, H], **regions}, indent=1))
print("done", len(list(SHOTS.glob("*.png"))), "shots")
