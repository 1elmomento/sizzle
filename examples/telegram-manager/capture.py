"""Films the real app on the showcase account: screenshots (2x) plus where the interesting parts are."""

import asyncio
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_SCALE_FACTOR", "2")

import qasync
from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QWidget

from telegram_manager.core.avatars import AvatarCache
from telegram_manager.core.storage import Storage
from telegram_manager.ui.main_window import MainWindow
from telegram_manager.ui.painting import logo_pixmap
from telegram_manager.ui.theme import apply_theme

HERE = Path(sys.argv[1])
SHOTS = HERE / "shots"
SHOTS.mkdir(exist_ok=True)

# The showcase account is invented: no real chat, name or message ever reaches the video.
if not (HERE / "showcase.db").exists():
    import subprocess
    subprocess.run([sys.executable, str(Path(__file__).with_name("showcase.py")), str(HERE / "showcase.db")],
                   check=True)
W, H = 1060, 1500

app = QApplication([])
apply_theme(app)
loop = qasync.QEventLoop(app)
asyncio.set_event_loop(loop)
storage = Storage(HERE / "showcase.db", 1)
account = Storage.last_account(HERE / "showcase.db")
chats, _synced = storage.load_chat_snapshot()
win = MainWindow(None, storage, account, AvatarCache(None, HERE))
win._engine._chats = list(chats)
win._apply_chats(chats)
win._engine._publish_progress()
win.setMinimumSize(0, 0)
win.resize(W, H)
win.show()
ws = win._workspace
regions: dict[str, list[int]] = {}


def settle(t=0.4):
    loop.run_until_complete(asyncio.sleep(t))


def rect_of(widget: QWidget) -> list[int]:
    top_left = widget.mapTo(win, QPoint(0, 0))
    return [top_left.x(), top_left.y(), widget.width(), widget.height()]


def shot(name: str) -> None:
    win.grab().save(str(SHOTS / f"{name}.png"))


def hover(widget: QWidget, x: float, y: float) -> None:
    pos = QPointF(x, y)
    widget.mouseMoveEvent(QMouseEvent(QEvent.Type.MouseMove, pos, widget.mapToGlobal(pos), Qt.MouseButton.NoButton,
                                      Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier))


# The app's own mark, so the video and the product agree.
logo_pixmap(420).save(str(HERE / "logo.png"))

settle(0.3)
ws.show_overview()
settle(0.4)
shot("overview")
regions["overview_tiles"] = rect_of(ws._overview._tiles["chats"].parentWidget())
regions["workspace"] = rect_of(ws)

# Trends: the timeline drawing itself in, frame by frame.
ws.open_trends()
settle(2.5)
page = ws.trends
charts = [page._timeline, page._hours, page._calendar]
for chart in charts:
    chart._animation.stop()
for i in range(25):
    for chart in charts:
        chart._progress = (i / 24) ** 0.7
        chart.update()
    app.processEvents()
    shot(f"trends_{i:02d}")
regions["trends_tiles"] = rect_of(page._tiles[0].parentWidget())
regions["trends_timeline"] = rect_of(page._timeline.parentWidget())
hover(page._timeline, page._timeline.width() * 0.8, page._timeline.height() * 0.4)
app.processEvents()
shot("trends_hover")

bar = page._scroll.verticalScrollBar()
bar.setValue(page._hours.parentWidget().y() - 16)
settle(0.2)
shot("trends_heat")
regions["trends_hours"] = rect_of(page._hours.parentWidget())
regions["trends_calendar"] = rect_of(page._calendar.parentWidget())

for sort, name in ((1, "rising"), (2, "fading"), (3, "quiet")):
    page._sorts.set_current(sort)
    page._on_sort(sort)
    settle(0.1)
    bar.setValue(page._people_card.y() - 16)
    settle(0.2)
    shot(f"people_{name}")
    regions[f"people_{name}"] = rect_of(page._people_card)

people = page._trends.people(page._period)
page.show_person(people[1].chat_id)
settle(1.2)
bar.setValue(0)
settle(0.2)
shot("person")
regions["person_card"] = rect_of(page._person_card)
regions["person_timeline"] = rect_of(page._timeline.parentWidget())
page.show_person(None)
page._sorts.set_current(0)
page._on_sort(0)
win._on_escape()
settle(0.3)

# Unread chats: the panel over the Overview.
ws.show_overview()
settle(0.3)
ws._overview._tiles["unread"].clicked.emit()
settle(0.6)
sheet = ws._sheet
shot("sheet_unread")
regions["sheet_panel"] = rect_of(sheet._panel)
for key, button in sheet._buttons.items():
    regions[f"sheet_{key}"] = rect_of(button)
sheet.dismiss()
settle(0.5)

# Bulk: inactive groups, all ticked, with the action bar.
insight = next(i for i in __import__("telegram_manager.core.insights", fromlist=["x"]).compute_insights(
    ws.engine.chats(), {c.id: ws.engine.state(c.id) for c in ws.engine.chats() if ws.engine.state(c.id)},
    storage.chats_with_own_messages(), __import__("datetime").datetime.now(__import__("datetime").timezone.utc))
    if i.key == "inactive_groups")
win.resize(W, 1000)
settle(0.3)
ws.show_insight(insight)
settle(0.5)
shot("bulk")
regions["bulk_bar"] = rect_of(ws.chats.bulk_bar)
from PySide6.QtWidgets import QPushButton
for button in ws.chats.bulk_bar.findChildren(QPushButton):
    if button.isVisible() and button.text():
        regions["bulk_" + button.text().split()[0].lower()] = rect_of(button)
regions["bulk_table"] = rect_of(ws.chats)

win.resize(W, H)
settle(0.3)
# Search.
ws.search_field.setText("trip")
settle(1.5)
regions["search_field"] = rect_of(ws.search_field)
shot("search")
regions["search_page"] = rect_of(ws._search)
ws.search_field.clear()
settle(0.3)

# Feed.
ws.open_feed()
settle(1.5)
shot("feed")
regions["feed_page"] = rect_of(ws.feed)
win._on_escape()
settle(0.2)

(HERE / "regions.json").write_text(json.dumps({"size": [W, H], **regions}, indent=1))
print("done", len(list(SHOTS.glob("*.png"))), "shots", flush=True)
ws.stop()
win.close()
os._exit(0)
