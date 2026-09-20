"""Films sizzle for its own reel.

sizzle has no window: its UI is the config file you write, the terminal you run it in,
and the frames it hands back. So this script draws those three, plus one real rendered
frame kept in assets/, and reports the rectangles worth pointing at.

Every region here is *measured*, never guessed: text rows come from a column spec and a
monospace advance, and the caption box in the rendered frame is found by scanning the
image for lit pixels. A ring that points at empty space is worse than no ring at all.

Contract: write shots/<name>.png and regions.json (logical coordinates) into sys.argv[1].
"""

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPen
from PySide6.QtWidgets import QApplication

HERE = Path(sys.argv[1])
SHOTS = HERE / "shots"
SHOTS.mkdir(parents=True, exist_ok=True)
SCALE = 2
W, H = 1180, 760
regions: dict[str, list[float]] = {}

BG, CHROME, EDGE = QColor("#0b1119"), QColor("#121a25"), QColor("#1f2c3b")
FG, DIM, KEY = QColor("#dce6f2"), QColor("#7d8fa3"), QColor("#7fb2f0")
STR, NUM, OK = QColor("#8fd694"), QColor("#e0b072"), QColor("#6fd39b")
LINE, PAD_X, TOP, PX = 30.0, 42.0, 86.0, 17

app = QApplication([])


def _mono(px=PX, bold=False):
    f = QFont("Hack", px)
    f.setStyleHint(QFont.StyleHint.Monospace)
    f.setWeight(QFont.Weight.Bold if bold else QFont.Weight.Normal)
    return f


CHAR = QFontMetricsF(_mono()).horizontalAdvance("M")      # monospace: one advance fits all


def cols(row: int, start: int, end: int, rows: int = 1, pad: float = 7.0) -> list[float]:
    """The exact rect of character columns [start, end) across `rows` rows."""
    return [PAD_X + start * CHAR - pad, TOP + row * LINE + 2 - pad,
            (end - start) * CHAR + 2 * pad, rows * LINE - 4 + 2 * pad]


def _window(title: str):
    img = QImage(W * SCALE, H * SCALE, QImage.Format.Format_ARGB32)
    img.setDevicePixelRatio(SCALE)
    img.fill(BG)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setRenderHint(QPainter.RenderHint.TextAntialiasing)
    p.fillRect(QRectF(0, 0, W, 56), CHROME)
    p.setPen(QPen(EDGE, 1))
    p.drawLine(0, 56, W, 56)
    for i, dot in enumerate(("#ec6a5f", "#f4bf50", "#61c554")):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(dot))
        p.drawEllipse(QRectF(24 + i * 24, 22, 13, 13))
    p.setPen(DIM)
    p.setFont(_mono(15))
    p.drawText(QRectF(0, 0, W, 56), Qt.AlignmentFlag.AlignCenter, title)
    return img, p


def draw_runs(p, runs, row, x=PAD_X):
    p.setFont(_mono())
    m = QFontMetricsF(_mono())
    cursor = x
    for text, color in runs:
        p.setPen(color)
        p.drawText(QRectF(cursor, TOP + row * LINE, 1400, LINE), Qt.AlignmentFlag.AlignVCenter, text)
        cursor += m.horizontalAdvance(text)


def save(img, p, name):
    p.end()
    img.save(str(SHOTS / f"{name}.png"))
    print("  shot", name)


# --- 1. the config file -------------------------------------------------------------------

CONFIG = [
    '[[scene]]',
    'key = "search"',
    'say = "Search finds any note in milliseconds."',
    'caption = true',
    'type = "showcase"',
    '',
    '  [[scene.shot]]',
    '  name = "search"',
    '  from = { region = "note_list", pad = 16 }',
    '  enter = "right"',
    '',
    '    [[scene.shot.ring]]',
    '    region = "first_note"',
    '    cue = "milliseconds-0.2"',
]
img, p = _window("video/sizzle.toml")
for i, raw in enumerate(CONFIG):
    if not raw.strip():
        continue
    indent = len(raw) - len(raw.lstrip())
    body, x = raw.strip(), PAD_X + indent * CHAR
    if body.startswith("[["):
        draw_runs(p, [(body, KEY)], i, x)
    elif "=" in body:
        k, _, v = body.partition("=")
        colour = NUM if v.strip() in ("true", "false") else (STR if '"' in v else FG)
        draw_runs(p, [(k, FG), ("=", DIM), (v, colour)], i, x)
    else:
        draw_runs(p, [(body, FG)], i, x)
save(img, p, "config")

longest = max(len(r) for r in CONFIG[:5])
regions["config_all"] = [0, 0, W, H]
regions["scene_block"] = cols(0, 0, longest, rows=5)
regions["shot_block"] = cols(6, 0, len(CONFIG[8]), rows=4)
regions["cue_line"] = cols(13, 0, len(CONFIG[13]))
regions["say_line"] = cols(2, 0, len(CONFIG[2]))

# --- 2. the plan ------------------------------------------------------------------------
# Columns are declared, so a region is a column range — not a guess at a pixel offset.

PLAN_COLS = [("scene", 13, "<"), ("type", 14, "<"), ("in", 8, ">"), ("vo", 8, ">"),
             ("out", 8, ">"), ("line", 0, "<")]
PLAN_ROWS = [
    ("hook", "title", "0.00", "0.30", "3.62", "You shipped the app..."),
    ("reveal", "reveal", "3.62", "3.87", "5.38", "This is sizzle."),
    ("config", "showcase", "5.38", "5.63", "8.91", "Your whole video is one..."),
    ("cues", "showcase", "8.91", "9.16", "14.70", "Motion is cued to spoken..."),
    ("music", "icon", "14.70", "14.95", "19.88", "The score is generated..."),
    ("outro", "outro", "19.88", "20.13", "25.44", "sizzle. From a config..."),
]


def plan_span(name: str) -> tuple[int, int]:
    """Character columns occupied by a named column of the table."""
    start = 0
    for label, width, _ in PLAN_COLS:
        if label == name:
            return start, start + (width if width else 26)
        start += width
    raise KeyError(name)


def plan_line(values) -> str:
    out = ""
    for (label, width, align), value in zip(PLAN_COLS, values):
        out += f"{value:{align}{width}}" if width else "  " + str(value)
    return out


HEADER = plan_line([label for label, _, _ in PLAN_COLS])
BODY = [plan_line(r) for r in PLAN_ROWS]

img, p = _window("sizzle plan")
draw_runs(p, [("$ ", OK), ("sizzle plan video/", FG)], 0)
draw_runs(p, [(HEADER, DIM)], 2)
for i, row in enumerate(BODY):
    draw_runs(p, [(row, FG)], 3 + i)
total_row = 3 + len(BODY) + 1
draw_runs(p, [("total 25.44s", FG)], total_row)
TARGETS = ["  reels      1080x1920 30fps  763 frames",
           "  tiktok     1080x1920 30fps  763 frames",
           "  x          1920x1080 30fps  763 frames"]
for i, row in enumerate(TARGETS):
    draw_runs(p, [(row, KEY)], total_row + 1 + i)
save(img, p, "plan")

vo_start, vo_end = plan_span("vo")
regions["plan_all"] = [0, 0, W, H]
regions["plan_rows"] = cols(2, 0, len(HEADER), rows=1 + len(BODY))
# Only the glyph columns: an 8-wide field padded outward would graze the "in" values.
regions["vo_column"] = cols(2, vo_end - 6, vo_end, rows=1 + len(BODY), pad=6)
regions["total_line"] = cols(total_row, 0, len("total 25.44s"))
regions["targets"] = cols(total_row + 1, 0, max(len(r) for r in TARGETS), rows=len(TARGETS))

# --- 3. the output ----------------------------------------------------------------------

OUT_HEAD = [
    [("$ ", OK), ("sizzle build video/ --targets reels,tiktok,x", FG)],
    [],
    [("rendering reels: 25.4s at 1080x1920", DIM)],
    [("rendering tiktok: 25.4s at 1080x1920", DIM)],
    [("rendering x: 25.4s at 1920x1080", DIM)],
    [("audio written", DIM)],
    [],
    [("$ ", OK), ("ls out/", FG)],
]
OUT_FILES = [
    "sizzle-reels-music.mp4        sizzle-reels-cover.jpg",
    "sizzle-reels-voice-only.mp4   sizzle-tiktok-cover.jpg",
    "sizzle-tiktok-music.mp4       sizzle-x-cover.jpg",
    "sizzle-tiktok-voice-only.mp4",
    "sizzle-x-music.mp4",
    "sizzle-x-voice-only.mp4",
]
img, p = _window("sizzle build")
for i, runs in enumerate(OUT_HEAD):
    if runs:
        draw_runs(p, runs, i)
first_file = len(OUT_HEAD)
for i, row in enumerate(OUT_FILES):
    draw_runs(p, [(row, STR)], first_file + i)
save(img, p, "out")

regions["out_all"] = [0, 0, W, H]
regions["out_files"] = cols(first_file, 0, max(len(r) for r in OUT_FILES), rows=len(OUT_FILES))

# --- 4. a real rendered frame -------------------------------------------------------------
# The caption box is found by scanning for lit pixels, because guessing where sizzle put
# its caption is exactly the mistake this file exists to avoid.

asset = HERE / "assets/frame.png"
if asset.exists():
    frame = QImage(str(asset)).convertToFormat(QImage.Format.Format_ARGB32)
    frame.save(str(SHOTS / "frame.png"))
    fw, fh = frame.width(), frame.height()
    lo, hi = int(fh * 0.60), int(fh * 0.92)          # the band captions live in
    min_x, min_y, max_x, max_y = fw, fh, 0, 0
    for y in range(lo, hi, 2):
        for x in range(0, fw, 2):
            c = frame.pixelColor(x, y)
            if c.lightness() > 150:                   # caption type is near-white
                min_x, max_x = min(min_x, x), max(max_x, x)
                min_y, max_y = min(min_y, y), max(max_y, y)
    if max_x > min_x:
        pad = 14
        regions["frame_caption"] = [(min_x - pad) / SCALE, (min_y - pad) / SCALE,
                                    (max_x - min_x + 2 * pad) / SCALE,
                                    (max_y - min_y + 2 * pad) / SCALE]
        print(f"  measured caption box {regions['frame_caption']}")
    regions["frame_all"] = [0, 0, fw / SCALE, fh / SCALE]
    print("  shot frame")

(HERE / "regions.json").write_text(json.dumps({"size": [W, H], **regions}, indent=1))
print("done", len(list(SHOTS.glob("*.png"))), "shots")
