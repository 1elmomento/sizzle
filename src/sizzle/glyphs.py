"""Line icons on a 24x24 grid, and the brand mark.

Self-contained on purpose: a reel must never import drawing code from the app it
is advertising, or the skill stops being portable.
"""

from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QLinearGradient, QPainter, QPainterPath, QPen

NAMES = ("home", "chart", "users", "user", "stack", "search", "feed", "lock", "shield", "check", "close",
         "arrow-up", "arrow-down", "chevron-down", "chevron-right", "muted", "bell", "refresh", "trash",
         "star", "heart", "bolt", "clock", "calendar", "mail", "folder", "cloud", "globe", "code",
         "database", "play", "filter", "sparkle", "tag", "map-pin", "eye", "download", "link")


def paint(painter: QPainter, rect: QRectF, name: str, color: QColor, weight: float = 1.9) -> None:
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.translate(rect.topLeft())
    painter.scale(rect.width() / 24, rect.height() / 24)
    painter.setPen(QPen(color, weight, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    painter.setBrush(Qt.BrushStyle.NoBrush)

    def line(*points, close=False):
        path = QPainterPath(QPointF(*points[0]))
        for point in points[1:]:
            path.lineTo(*point)
        if close:
            path.closeSubpath()
        painter.drawPath(path)

    def circle(cx, cy, r):
        painter.drawEllipse(QPointF(cx, cy), r, r)

    def box(x, y, w, h, r=2.5):
        painter.drawRoundedRect(QRectF(x, y, w, h), r, r)

    def dot(cx, cy, r=1.1):
        painter.save()
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), r, r)
        painter.restore()

    def person(cx, top, scale=1.0):
        circle(cx, top, 2.6 * scale)
        arc = QRectF(cx - 4.6 * scale, top + 2.2 * scale, 9.2 * scale, 8.4 * scale)
        path = QPainterPath(QPointF(arc.left(), arc.center().y()))
        path.arcTo(arc, 180, -180)
        painter.drawPath(path)

    if name == "home":
        line((3, 11), (12, 3.5), (21, 11))
        line((5.5, 10), (5.5, 20), (18.5, 20), (18.5, 10))
        line((10, 20), (10, 14), (14, 14), (14, 20))
    elif name == "chart":
        line((3.5, 20.5), (20.5, 20.5))
        line((4, 16), (9, 10.5), (13.5, 14), (20, 5.5))
        dot(9, 10.5), dot(13.5, 14)
    elif name == "users":
        person(9, 8)
        painter.setOpacity(0.7)
        person(16.5, 8.5, 0.8)
        painter.setOpacity(1.0)
    elif name == "user":
        person(12, 8)
    elif name == "stack":
        for i in range(3):
            y = 6.5 + i * 5
            dot(5, y)
            line((9, y), (19.5, y))
    elif name == "search":
        circle(10.5, 10.5, 6.5)
        line((15.4, 15.4), (20.5, 20.5))
    elif name == "feed":
        box(3.5, 4.5, 17, 15, 3)
        line((7, 9), (17, 9))
        line((7, 12.5), (17, 12.5))
        line((7, 16), (13, 16))
    elif name == "lock":
        box(4.5, 10.5, 15, 9.5, 2.5)
        shackle = QPainterPath(QPointF(8.5, 10.5))     # legs meet the body, or it reads as unlocked
        shackle.lineTo(8.5, 9)
        shackle.arcTo(QRectF(8.5, 4.5, 7, 9), 180, -180)
        shackle.lineTo(15.5, 10.5)
        painter.drawPath(shackle)
        dot(12, 15.2, 1.5)
    elif name == "shield":
        line((12, 3), (20, 6.5), (20, 12), (12, 21), (4, 12), (4, 6.5), close=True)
        line((8.5, 12), (11, 14.5), (15.5, 9.5))
    elif name == "check":
        line((5, 12.5), (10, 17.5), (19, 6.5))
    elif name == "close":
        line((6, 6), (18, 18))
        line((18, 6), (6, 18))
    elif name in ("arrow-up", "arrow-down"):
        sign = 1 if name == "arrow-up" else -1
        line((12, 12 - 8 * sign), (12, 12 + 8 * sign))
        line((6.5, 12 - 2.5 * sign), (12, 12 - 8 * sign), (17.5, 12 - 2.5 * sign))
    elif name == "chevron-down":
        line((6, 9.5), (12, 15.5), (18, 9.5))
    elif name == "chevron-right":
        line((9.5, 6), (15.5, 12), (9.5, 18))
    elif name == "muted":
        line((5, 9.5), (8.5, 9.5), (13, 5.5), (13, 18.5), (8.5, 14.5), (5, 14.5), close=True)
        line((16.5, 9.5), (21, 14.5))
        line((21, 9.5), (16.5, 14.5))
    elif name == "bell":
        path = QPainterPath(QPointF(6.5, 16))
        path.lineTo(6.5, 11)
        path.arcTo(QRectF(6.5, 3.5, 11, 11), 180, -180)
        path.lineTo(17.5, 16)
        path.closeSubpath()
        painter.drawPath(path)
        line((4.5, 16.5), (19.5, 16.5))
        line((10, 19.5), (14, 19.5))
    elif name == "refresh":
        painter.drawArc(QRectF(4.5, 4.5, 15, 15), 60 * 16, 250 * 16)
        line((19, 3.5), (19.5, 9), (14, 8.5))
    elif name == "trash":
        line((4.5, 6.5), (19.5, 6.5))
        line((9.5, 6.5), (10, 4), (14, 4), (14.5, 6.5))
        line((6.5, 6.5), (7.5, 20.5), (16.5, 20.5), (17.5, 6.5))
        line((10.5, 10), (10.5, 17))
        line((13.5, 10), (13.5, 17))
    elif name == "star":
        pts = []
        for i in range(10):
            angle = -math.pi / 2 + i * math.pi / 5
            r = 8.5 if i % 2 == 0 else 3.6
            pts.append((12 + r * math.cos(angle), 12 + r * math.sin(angle)))
        line(*pts, close=True)
    elif name == "heart":
        path = QPainterPath(QPointF(12, 20))
        path.cubicTo(2, 13.5, 4, 4.5, 12, 8.5)
        path.cubicTo(20, 4.5, 22, 13.5, 12, 20)
        painter.drawPath(path)
    elif name == "bolt":
        line((13.5, 2.5), (5.5, 13.5), (11, 13.5), (10.5, 21.5), (18.5, 10.5), (13, 10.5), close=True)
    elif name == "clock":
        circle(12, 12, 8.5)
        line((12, 7), (12, 12.5), (16, 14.5))
    elif name == "calendar":
        box(3.5, 5.5, 17, 15, 3)
        line((3.5, 10), (20.5, 10))
        line((8, 3), (8, 7))
        line((16, 3), (16, 7))
        dot(9, 14), dot(15, 14), dot(9, 17.5)
    elif name == "mail":
        box(3, 5.5, 18, 13, 2.5)
        line((3.5, 7), (12, 13.5), (20.5, 7))
    elif name == "folder":
        line((3.5, 18.5), (3.5, 6), (9.5, 6), (11.5, 8.5), (20.5, 8.5), (20.5, 18.5), close=True)
    elif name == "cloud":
        path = QPainterPath(QPointF(7, 18))
        path.arcTo(QRectF(2.5, 11, 9, 9), 180, -140)
        path.arcTo(QRectF(6, 5, 11, 11), 170, -170)
        path.arcTo(QRectF(13, 10.5, 9, 9), 90, -110)
        path.closeSubpath()
        painter.drawPath(path)
    elif name == "globe":
        circle(12, 12, 8.5)
        line((3.5, 12), (20.5, 12))
        painter.drawArc(QRectF(7.5, 3.5, 9, 17), -90 * 16, 180 * 16)
        painter.drawArc(QRectF(7.5, 3.5, 9, 17), 90 * 16, 180 * 16)
    elif name == "code":
        line((9, 6.5), (3.5, 12), (9, 17.5))
        line((15, 6.5), (20.5, 12), (15, 17.5))
    elif name == "database":
        painter.drawEllipse(QRectF(4, 3.5, 16, 5.5))
        line((4, 6.5), (4, 17.5))
        line((20, 6.5), (20, 17.5))
        painter.drawArc(QRectF(4, 14.5, 16, 5.5), 180 * 16, 180 * 16)
        painter.drawArc(QRectF(4, 9, 16, 5.5), 180 * 16, 180 * 16)
    elif name == "play":
        line((8.5, 5.5), (18.5, 12), (8.5, 18.5), close=True)
    elif name == "filter":
        line((3.5, 5.5), (20.5, 5.5), (14, 13), (14, 19.5), (10, 17.5), (10, 13), close=True)
    elif name == "sparkle":
        for cx, cy, r in ((11, 10, 6.5), (18.5, 17.5, 3.4)):
            path = QPainterPath(QPointF(cx, cy - r))
            for dx, dy in ((r * 0.28, -r * 0.28), (r, 0), (r * 0.28, r * 0.28), (0, r),
                           (-r * 0.28, r * 0.28), (-r, 0), (-r * 0.28, -r * 0.28)):
                path.quadTo(cx + dx, cy + dy, *((cx, cy + r) if dy == r else (cx + dx * 2.4, cy + dy * 2.4)))
            path.closeSubpath()
            painter.drawPath(path)
    elif name == "tag":
        line((3.5, 11), (11, 3.5), (20.5, 3.5), (20.5, 13), (13, 20.5), close=True)
        circle(16.5, 7.5, 1.6)
    elif name == "map-pin":
        path = QPainterPath(QPointF(12, 21))
        path.lineTo(6.5, 13)
        path.arcTo(QRectF(4.5, 2.5, 15, 15), 215, -250)
        path.closeSubpath()
        painter.drawPath(path)
        circle(12, 9.5, 2.6)
    elif name == "eye":
        path = QPainterPath(QPointF(2.5, 12))
        path.quadTo(12, 3.5, 21.5, 12)
        path.quadTo(12, 20.5, 2.5, 12)
        painter.drawPath(path)
        circle(12, 12, 3.1)
    elif name == "download":
        line((12, 3.5), (12, 14.5))
        line((7.5, 10), (12, 14.5), (16.5, 10))
        line((4.5, 18.5), (19.5, 18.5))
    elif name == "link":
        painter.drawArc(QRectF(2.5, 8.5, 12, 7), 40 * 16, 260 * 16)
        painter.drawArc(QRectF(9.5, 8.5, 12, 7), 220 * 16, 260 * 16)
        line((8.5, 12), (15.5, 12))
    painter.restore()


def logo_image(size: int, name: str, accent: QColor, second: QColor, path: Path | None = None) -> QImage:
    """The brand mark: the project's own file if it has one, else a generated initials tile."""
    if path is not None and Path(path).exists():
        img = QImage(str(path))
        if not img.isNull():
            return img.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
    img = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0, accent)
    gradient.setColorAt(1, second)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(gradient)
    p.drawRoundedRect(QRectF(0, 0, size, size), size * 0.26, size * 0.26)
    initials = "".join(w[0] for w in name.split()[:2]).upper() or "A"
    f = QFont("Noto Sans")
    f.setPixelSize(int(size * (0.46 if len(initials) > 1 else 0.58)))
    f.setWeight(QFont.Weight.Black)
    p.setFont(f)
    p.setPen(QColor("white"))
    m = QFontMetricsF(f)
    p.drawText(QPointF(size / 2 - m.horizontalAdvance(initials) / 2,
                       size / 2 + (m.ascent() - m.descent()) / 2), initials)
    p.end()
    return img
