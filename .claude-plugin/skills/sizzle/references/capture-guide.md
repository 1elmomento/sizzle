# Writing `capture.py`

The one genuinely project-specific file. Its contract is small:

- write `shots/<name>.png` into the directory passed as `sys.argv[1]`
- write `regions.json` there too: `{"size": [w, h], "<name>": [x, y, w, h], ...}`

Both in **logical** coordinates (CSS pixels), at capture scale 2. `reel.toml` then refers
to shots and regions by name and never mentions pixels.

Regions are what make a reel feel like a product demo rather than a slideshow: they let
the video zoom to a chart, ring the button being described, and retype a query into the
real search field.

## A Qt app, offscreen

The strongest option when the app is PySide6/PyQt: no window server, no recording, and
you can drive internals directly.

```python
import os, sys, json
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_SCALE_FACTOR", "2")
from PySide6.QtCore import QPoint
from PySide6.QtWidgets import QApplication, QWidget

HERE = Path(sys.argv[1])
(HERE / "shots").mkdir(exist_ok=True)
regions: dict[str, list[int]] = {}

app = QApplication([])
win = build_your_window()
win.resize(1060, 1500)
win.show()

def shot(name):
    win.grab().save(str(HERE / "shots" / f"{name}.png"))

def rect_of(widget: QWidget):
    tl = widget.mapTo(win, QPoint(0, 0))
    return [tl.x(), tl.y(), widget.width(), widget.height()]

shot("overview")
regions["overview_tiles"] = rect_of(win.tiles)
(HERE / "regions.json").write_text(json.dumps({"size": [1060, 1500], **regions}, indent=1))
```

Notes that matter:

- **Settle between steps.** `app.processEvents()`, or run the event loop briefly
  (`qasync` if the app is async). Screens grabbed mid-layout look broken.
- **Capture animations as frames.** Stop the widget's own animation, step its progress
  by hand, and save `chart_00.png` … `chart_24.png`. `reel.toml`'s `frames` plays them.
- **Capture states, not interactions.** One PNG per state — sorted this way, that tab
  open, the panel dismissed. The motion is added later.
- **Export the app's own logo** to `logo.png` here, so the video and the product agree.
- Resize the window per scene if a shot wants a different shape.

## A web app

Playwright, with the same contract:

```python
page.set_viewport_size({"width": 1060, "height": 1500})
page.goto(url)
page.screenshot(path=str(HERE / "shots" / "overview.png"), scale="css")
box = page.locator("#chart").bounding_box()
regions["chart"] = [box["x"], box["y"], box["width"], box["height"]]
```

Use `device_scale_factor=2` on the context and keep `scale="css"` so the PNG is 2× the
logical size, which is what the engine expects.

## A terminal app

Render the terminal yourself rather than filming it: run the command, capture the
output, and draw it into a PNG with a monospace font on the theme's background. Regions
are then the line ranges you want to ring. A custom `scenes.py` that types the output
line by line usually beats a screenshot here.

## Data on screen

Never film a real account. Build a fixture that *looks* real — plausible names, a
believable distribution over time, a few pinned and muted items — and film that. The
worked example's `showcase.py` invents two years of history for forty-two people; the
numbers on screen are the ones the narration quotes.
