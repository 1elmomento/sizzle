"""The app window as a floating, tilted card — plus the callouts drawn on top of it.

A screenshot is addressed in the *logical* coordinates the capture script reported,
so `reel.toml` can say "zoom to the region called trends_timeline" and never mention
pixels or device scale factors.
"""

from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen, QRadialGradient, QTransform

from .draw import Canvas, back_out, clamp, ease_out, lerp, with_alpha


class Regions:
    """The named rectangles the capture script found, in logical coordinates."""

    def __init__(self, path: Path):
        raw = json.loads(path.read_text()) if path.exists() else {"size": [1000, 1400]}
        self.size = raw.get("size", [1000, 1400])
        self.items = {k: v for k, v in raw.items() if k != "size"}

    def rect(self, spec) -> list[float]:
        """A rect from reel.toml: [x,y,w,h], a region name, or {region=…, pad=…, height=…}."""
        if spec is None:
            return [0, 0, self.size[0], self.size[1]]
        if isinstance(spec, list):
            return [float(v) for v in spec]
        if isinstance(spec, str):
            return list(self._named(spec))
        base = list(self._named(spec["region"])) if "region" in spec else [0, 0, *self.size]
        pad = spec.get("pad", 0)
        out = [base[0] - pad, base[1] - pad, base[2] + 2 * pad, base[3] + 2 * pad]
        for i, key in enumerate(("dx", "dy", "dw", "dh")):
            out[i] += float(spec.get(key, 0))
        for i, key in enumerate(("x", "y", "width", "height")):
            if key in spec:
                out[i] = float(spec[key])
        anchor = spec.get("anchor")
        if anchor == "bottom":      # hold the crop to the foot of the region, e.g. an action bar
            out[1] = base[1] + base[3] - out[3] + float(spec.get("dy", 0))
        elif anchor == "center":
            out[1] = base[1] + (base[3] - out[3]) / 2 + float(spec.get("dy", 0))
        return out

    def _named(self, name: str):
        if name not in self.items:
            raise SystemExit(f"unknown region {name!r}; capture reported: {', '.join(sorted(self.items))}")
        return self.items[name]


def draw_shot(canvas: Canvas, p: QPainter, name: str, src, cx: float, cy: float, width: float, *,
              tilt_x=0.0, tilt_y=0.0, alpha=1.0, scale=1.0, radius=26.0, clip_height=None, overlay=None):
    """Draws `src` (logical x, y, w, h) of a screenshot as a lit, tilted card.

    `overlay(painter, to_card, k)` may draw on top in card space: `to_card(x, y)`
    maps logical screenshot coordinates to the card, `k` is pixels per logical pixel.
    """
    scaled = canvas.config.capture_scale
    x, y, w, h = src
    height = width * h / w
    k = width / w
    transform = QTransform()
    transform.translate(cx, cy)
    transform.rotate(tilt_x, Qt.Axis.XAxis, 1800)
    transform.rotate(tilt_y, Qt.Axis.YAxis, 1800)
    transform.scale(scale, scale)
    if alpha <= 0:
        return transform, k, src
    p.save()
    p.setTransform(transform)
    p.setOpacity(alpha)
    shown = height if clip_height is None else min(height, clip_height)
    card = QRectF(-width / 2, -height / 2, width, shown)
    p.setPen(Qt.PenStyle.NoPen)
    for spread, a in ((60, 14), (34, 26), (16, 40), (6, 60)):
        p.setBrush(QColor(0, 0, 0, a))
        p.drawRoundedRect(card.adjusted(-spread, -spread * 0.5, spread, spread * 1.3), radius + spread, radius + spread)
    glow = QRadialGradient(QPointF(0, -height * 0.2), width * 0.75)
    glow.setColorAt(0, with_alpha(canvas.theme.accent, 0.18))
    glow.setColorAt(1, with_alpha(canvas.theme.accent, 0))
    p.setBrush(glow)
    p.drawRoundedRect(card.adjusted(-40, -40, 40, 40), radius + 40, radius + 40)
    path = QPainterPath()
    path.addRoundedRect(card, radius, radius)
    p.setClipPath(path)
    p.drawImage(QRectF(-width / 2, -height / 2, width, height), canvas.shot(name),
                QRectF(x * scaled, y * scaled, w * scaled, h * scaled))
    if overlay is not None:
        overlay(p, lambda rx, ry: QPointF(-width / 2 + (rx - x) * k, -height / 2 + (ry - y) * k), k)
    p.setClipping(False)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor(255, 255, 255, 34), 1.5))
    p.drawRoundedRect(card, radius, radius)
    p.restore()
    return transform, k, src


def ring(p: QPainter, to_card, k: float, rect, t: float, *, color: QColor) -> None:
    """A pulsing highlight around a region of the screenshot: 'look here'."""
    if t < 0:
        return
    x, y, w, h = rect
    top_left = to_card(x, y)
    r = QRectF(top_left.x(), top_left.y(), w * k, h * k)
    appear = ease_out(t / 0.35)
    for i in range(2):
        phase = (t * 1.3 + i * 0.5) % 1.0
        grow = 6 + 26 * phase
        p.setPen(QPen(with_alpha(color, (1 - phase) * 0.7 * appear), 3))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(r.adjusted(-grow, -grow, grow, grow), 12 + grow, 12 + grow)
    p.setPen(QPen(with_alpha(color, appear), 4))
    p.drawRoundedRect(r.adjusted(-5, -5, 5, 5), 14, 14)


def type_into(canvas: Canvas, p: QPainter, to_card, k: float, field, text: str, shown: float,
              *, src=None, reveal=0.0, blank: QColor | None = None, text_color="#e9eef4",
              font_px=14, pad_left=30) -> None:
    """Retypes a query into a captured input, and wipes what is below until it is typed.

    The screenshot already holds the finished search; covering the field and writing
    the query letter by letter turns one still into a believable interaction.
    """
    typed = text[: max(0, int(shown * len(text) + 0.999))]
    top_left = to_card(field[0] + pad_left - 2, field[1] + 6)
    cover = QRectF(top_left.x(), top_left.y(), (canvas.width_of(text, font_px * 2) + 60) * k, (field[3] - 12) * k)
    p.fillRect(cover, blank or QColor("#121b25"))
    f = canvas.font(font_px * k, QFont.Weight.Normal)
    p.setFont(f)
    p.setPen(QColor(text_color))
    m = QFontMetricsF(f)
    baseline = to_card(0, field[1] + field[3] / 2).y()
    x0 = to_card(field[0] + pad_left, 0).x() + 2 * k
    p.drawText(QPointF(x0, baseline + (m.ascent() - m.descent()) / 2), typed)
    if shown < 1 or int(shown * 40) % 2 == 0:
        caret = x0 + m.horizontalAdvance(typed) + 2
        p.fillRect(QRectF(caret, baseline - 9 * k, 1.6 * k, 18 * k), canvas.theme.accent)
    if src is not None:
        cut = to_card(0, field[1] + field[3] + 8).y()
        bottom = to_card(0, src[1] + src[3]).y()
        hide_from = lerp(cut, bottom, clamp(reveal))
        p.fillRect(QRectF(to_card(src[0], 0).x(), hide_from, src[2] * k, bottom - hide_from + 2),
                   blank or QColor("#121b25"))


def pop(t: float, at: float, over: float = 0.4, strength: float = 2.2) -> float:
    return back_out((t - at) / over if over > 0 else 1.0, strength)


def sample(canvas: Canvas, name: str, x: float, y: float) -> QColor:
    """The screenshot's own colour at a logical point — for covering part of it seamlessly."""
    scaled = canvas.config.capture_scale
    return canvas.shot(name).pixelColor(int(x * scaled), int(y * scaled))
