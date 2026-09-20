"""The painting toolbox: easing, text, pills, badges and the animated background.

`Canvas` holds the frame size and the theme so scenes never reach for globals; it
is the only thing a custom `scenes.py` needs to learn.
"""

from __future__ import annotations

import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QColor, QFont, QFontMetricsF, QGuiApplication, QImage, QLinearGradient, QPainter,
                           QPainterPath, QPen, QRadialGradient)

from . import glyphs
from .config import Config

_app = None


def ensure_app() -> QGuiApplication:
    """Qt needs an application before fonts or images exist, even with no window."""
    global _app
    if QGuiApplication.instance() is None:
        import os
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        _app = QGuiApplication([])
    return QGuiApplication.instance()

# --- easing ------------------------------------------------------------------------------


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(x):
    return 1 - (1 - clamp(x)) ** 3


def ease_in(x):
    return clamp(x) ** 3


def ease_in_out(x):
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def back_out(x, s=1.9):
    """Overshoots and settles — the pop that makes a title feel alive."""
    x = clamp(x) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_rect(a, b, t):
    return [lerp(x, y, t) for x, y in zip(a, b)]


def span(t, a, b):
    """0 before `a`, 1 after `b`, linear between — the unit of every animation here."""
    return clamp((t - a) / (b - a)) if b > a else float(t >= a)


def mix(c1: QColor, c2: QColor, t: float, alpha: float = 1.0) -> QColor:
    t = clamp(t)
    return QColor.fromRgbF(lerp(c1.redF(), c2.redF(), t), lerp(c1.greenF(), c2.greenF(), t),
                           lerp(c1.blueF(), c2.blueF(), t), alpha)


def with_alpha(color: QColor, alpha: float) -> QColor:
    c = QColor(color)
    c.setAlphaF(clamp(alpha))
    return c


class Canvas:
    def __init__(self, config: Config):
        ensure_app()
        self.config = config
        self.theme = config.theme
        self.brand = config.brand
        self.W, self.H = config.width, config.height
        self.cx = self.W / 2
        self.k = min(self.W, self.H) / 1080      # type and icon scale, by the short edge
        self.logo = glyphs.logo_image(420, config.brand.name, self.theme.accent, self.theme.second,
                                      config.brand.logo)
        rng = random.Random(4)
        self._sparks = [(rng.uniform(0, self.W), rng.uniform(0, self.H), rng.uniform(0.6, 2.4),
                         rng.uniform(8, 30), rng.uniform(0, 6)) for _ in range(70)]
        self._dots = self._make_dots()
        self._vignette = self._make_vignette()
        self._shots: dict[str, QImage] = {}

    # --- static layers ---------------------------------------------------------------

    def _make_dots(self) -> QImage:
        img = QImage(self.W, self.H + 60, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 255, 255, 13))
        for y in range(0, self.H + 60, 30):
            for x in range(15 * ((y // 30) % 2), self.W, 30):
                p.drawEllipse(QPointF(x, y), 1.3, 1.3)
        p.end()
        return img

    def _make_vignette(self) -> QImage:
        img = QImage(self.W, self.H, QImage.Format.Format_ARGB32_Premultiplied)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        g = QRadialGradient(QPointF(self.W / 2, self.H / 2), self.H * 0.72)
        g.setColorAt(0.55, QColor(0, 0, 0, 0))
        g.setColorAt(1.0, QColor(0, 0, 0, 170))
        p.fillRect(img.rect(), g)
        p.end()
        return img

    def shot(self, name: str) -> QImage:
        if name not in self._shots:
            path = self.config.shots / f"{name}.png"
            if not path.exists():
                raise SystemExit(f"missing screenshot {path} — run the capture step first")
            self._shots[name] = QImage(str(path))
        return self._shots[name]

    def background(self, p: QPainter, t: float, darken: float = 0.0) -> None:
        top, middle, bottom = self.theme.background
        g = QLinearGradient(0, 0, 0, self.H)
        g.setColorAt(0, top)
        g.setColorAt(0.5, middle)
        g.setColorAt(1, bottom)
        p.fillRect(0, 0, self.W, self.H, g)
        for cx, cy, r, color, a in (
            (self.cx + self.W * 0.31 * math.sin(t * 0.33), self.H * 0.29 + self.H * 0.115 * math.cos(t * 0.27),
             self.H * 0.40, self.theme.accent, 0.30),
            (self.cx - self.W * 0.31 * math.cos(t * 0.29), self.H * 0.72 + self.H * 0.104 * math.sin(t * 0.21),
             self.H * 0.375, self.theme.second, 0.26),
            (self.cx + self.W * 0.19 * math.sin(t * 0.5 + 2), self.H * 0.51 + self.H * 0.156 * math.cos(t * 0.4),
             self.H * 0.27, self.theme.third, 0.10),
        ):
            glow = QRadialGradient(QPointF(cx, cy), r)
            glow.setColorAt(0, with_alpha(color, a))
            glow.setColorAt(1, with_alpha(color, 0))
            p.fillRect(0, 0, self.W, self.H, glow)
        p.drawImage(0, -int((t * 12) % 60), self._dots)
        p.setPen(Qt.PenStyle.NoPen)
        for x, y, size, speed, phase in self._sparks:
            yy = (y - t * speed) % self.H
            a = 0.25 + 0.25 * math.sin(t * 1.3 + phase)
            p.setBrush(with_alpha(QColor("#cfe6ff"), a * 0.6))
            p.drawEllipse(QPointF(x + 8 * math.sin(t * 0.6 + phase), yy), size, size)
        p.drawImage(0, 0, self._vignette)
        if darken > 0:
            p.fillRect(0, 0, self.W, self.H, QColor(0, 0, 0, int(200 * clamp(darken))))

    # --- text ------------------------------------------------------------------------

    def font(self, px: float, weight=QFont.Weight.Bold) -> QFont:
        f = QFont(self.brand.font)
        f.setPixelSize(max(1, round(px)))
        f.setWeight(weight)
        return f

    def brand_gradient(self, rect: QRectF) -> QLinearGradient:
        g = QLinearGradient(rect.topLeft(), rect.topRight())
        g.setColorAt(0, mix(self.theme.accent, QColor("white"), 0.35))
        g.setColorAt(0.5, self.theme.second)
        g.setColorAt(1, self.theme.third)
        return g

    def text_path(self, text: str, f: QFont, cx: float, cy: float) -> QPainterPath:
        m = QFontMetricsF(f)
        path = QPainterPath()
        path.addText(cx - m.horizontalAdvance(text) / 2, cy + (m.ascent() - m.descent()) / 2, f, text)
        return path

    def text(self, p: QPainter, text: str, px: float, cx: float, cy: float, *, color=None, alpha=1.0,
             weight=QFont.Weight.Bold, gradient=False, scale=1.0, glow=0.0, shadow=True, dx=0.0, dy=0.0) -> None:
        if alpha <= 0:
            return
        color = self.theme.text if color is None else color
        p.save()
        p.translate(cx + dx, cy + dy)
        p.scale(scale, scale)
        path = self.text_path(text, self.font(px, weight), 0, 0)
        if glow > 0:
            for width, a in ((34, 0.05), (20, 0.08), (10, 0.12)):
                p.strokePath(path, QPen(with_alpha(self.theme.accent, a * glow * alpha), width,
                                        Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        if shadow:
            p.fillPath(path.translated(0, px * 0.05), QColor(0, 0, 0, int(120 * alpha)))
        if gradient:
            p.setOpacity(alpha)
            p.fillPath(path, self.brand_gradient(path.boundingRect()))
        else:
            p.fillPath(path, with_alpha(color, alpha * color.alphaF()))
        p.restore()

    def width_of(self, text: str, px: float, weight=QFont.Weight.Bold) -> float:
        return QFontMetricsF(self.font(px, weight)).horizontalAdvance(text)

    def pill(self, p: QPainter, text: str, cx: float, cy: float, *, px=30, fill=None, color=None,
             alpha=1.0, scale=1.0, glyph=None) -> None:
        if alpha <= 0:
            return
        color = self.theme.text if color is None else color
        f = self.font(px, QFont.Weight.Bold)
        m = QFontMetricsF(f)
        icon = px * 1.05 if glyph else 0
        width = m.horizontalAdvance(text) + px * 1.4 + (icon + px * 0.35 if glyph else 0)
        height = px * 2.0
        p.save()
        p.translate(cx, cy)
        p.scale(scale, scale)
        p.setOpacity(alpha)
        rect = QRectF(-width / 2, -height / 2, width, height)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 90))
        p.drawRoundedRect(rect.translated(0, 6), height / 2, height / 2)
        p.setBrush(self.brand_gradient(rect) if fill is None else fill)
        p.drawRoundedRect(rect, height / 2, height / 2)
        x = rect.left() + px * 0.7
        if glyph:
            glyphs.paint(p, QRectF(x, -icon / 2, icon, icon), glyph, color)
            x += icon + px * 0.35
        p.setFont(f)
        p.setPen(color)
        p.drawText(QRectF(x, rect.top(), m.horizontalAdvance(text) + 4, height), Qt.AlignmentFlag.AlignVCenter, text)
        p.restore()

    def badge(self, p: QPainter, x, y, text, scale, alpha, muted=False) -> None:
        """A floating unread-count style chip — the visual vocabulary of 'too much'."""
        if alpha <= 0 or scale <= 0:
            return
        f = self.font(30, QFont.Weight.Bold)
        w = max(56.0, QFontMetricsF(f).horizontalAdvance(text) + 34)
        h = 54
        p.save()
        p.translate(x, y)
        p.scale(scale, scale)
        p.setOpacity(alpha)
        rect = QRectF(-w / 2, -h / 2, w, h)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 80))
        p.drawRoundedRect(rect.translated(0, 5), h / 2, h / 2)
        if muted:
            p.setBrush(QColor("#4a5a6a"))
        else:
            g = QLinearGradient(rect.topLeft(), rect.topRight())
            g.setColorAt(0, self.theme.accent)
            g.setColorAt(1, self.theme.second)
            p.setBrush(g)
        p.drawRoundedRect(rect, h / 2, h / 2)
        p.setFont(f)
        p.setPen(QColor("white"))
        p.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
        p.restore()

    def note_card(self, p: QPainter, x, y, title, detail, alpha, angle) -> None:
        """A notification card, for the 'drowning in noise' beat."""
        if alpha <= 0:
            return
        p.save()
        p.translate(x, y)
        p.rotate(angle)
        p.setOpacity(alpha)
        rect = QRectF(-230, -52, 460, 104)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 90))
        p.drawRoundedRect(rect.translated(0, 8), 24, 24)
        p.setBrush(QColor(31, 43, 56, 235))
        p.setPen(QPen(QColor(255, 255, 255, 30), 1.5))
        p.drawRoundedRect(rect, 24, 24)
        p.setPen(Qt.PenStyle.NoPen)
        g = QLinearGradient(-210, -30, -150, 30)
        g.setColorAt(0, self.theme.accent)
        g.setColorAt(1, self.theme.second)
        p.setBrush(g)
        p.drawEllipse(QPointF(-178, 0), 32, 32)
        initials = "".join(w[0] for w in title.split()[:2]).upper()
        p.setFont(self.font(24, QFont.Weight.Bold))
        p.setPen(QColor("white"))
        p.drawText(QRectF(-210, -32, 64, 64), Qt.AlignmentFlag.AlignCenter, initials)
        p.setFont(self.font(28, QFont.Weight.Bold))
        p.setPen(self.theme.text)
        p.drawText(QRectF(-128, -40, 340, 40), Qt.AlignmentFlag.AlignVCenter, title)
        p.setFont(self.font(24, QFont.Weight.Normal))
        p.setPen(self.theme.soft)
        p.drawText(QRectF(-128, 2, 340, 36), Qt.AlignmentFlag.AlignVCenter, detail)
        p.restore()

    def brand_bar(self, p: QPainter, t: float, alpha: float, y: float | None = None) -> None:
        """Small mark + wordmark held at the top through the feature scenes."""
        if alpha <= 0:
            return
        y = self.H * self.config.active.bar_y if y is None else y
        p.save()
        p.setOpacity(alpha)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        size = 58 * self.k
        f = self.font(34 * self.k, QFont.Weight.Bold)
        label = self.brand.name
        width = size + 16 * self.k + QFontMetricsF(f).horizontalAdvance(label)
        x = self.cx - width / 2
        p.drawImage(QRectF(x, y - size / 2, size, size), self.logo)
        p.setFont(f)
        p.setPen(self.theme.text)
        p.drawText(QRectF(x + size + 16, y - 30 * self.k, width, 60 * self.k),
                   Qt.AlignmentFlag.AlignVCenter, label)
        p.restore()
