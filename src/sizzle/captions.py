"""Word-synced burned-in captions — most people watch a Reel with the sound off."""

from __future__ import annotations

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QLinearGradient, QPainter

from .draw import Canvas, back_out, span
from .timing import Timeline


def draw(canvas: Canvas, timeline: Timeline, p: QPainter, t: float, *, px: int | None = None,
         baseline: float | None = None, max_width: float | None = None) -> None:
    target = canvas.config.active
    px = int(canvas.config.tweak("caption_size", 58) * canvas.k) if px is None else px
    baseline = canvas.H * canvas.config.tweak("caption_y", target.caption_y) if baseline is None else baseline
    max_width = canvas.W * target.caption_width if max_width is None else max_width
    for beat in canvas.config.beats:
        if not beat.caption or not beat.say:
            continue
        s = timeline[beat.key]
        if not (s.vo - 0.15 <= t <= s.vo_end + 0.35):
            continue
        words = timeline.words(beat.key)
        sentences, current = [], []
        for word, at in words:
            current.append((word, at))
            if word[-1] in ".!?":
                sentences.append(current)
                current = []
        if current:
            sentences.append(current)
        active = sentences[0]
        for sentence in sentences:
            if t >= sentence[0][1] - 0.12:
                active = sentence
        fade = span(t, s.vo - 0.15, s.vo + 0.05) * (1 - span(t, s.vo_end + 0.1, s.vo_end + 0.35))
        top = baseline - canvas.H * 0.1
        scrim = QLinearGradient(0, top, 0, top + canvas.H * 0.235)
        scrim.setColorAt(0, QColor(4, 8, 15, 0))
        scrim.setColorAt(0.35, QColor(4, 8, 15, int(170 * fade)))
        scrim.setColorAt(1, QColor(4, 8, 15, int(120 * fade)))
        p.fillRect(QRectF(0, top, canvas.W, canvas.H * 0.235), scrim)
        _block(canvas, p, active, t, fade, px, baseline, max_width)


def _block(canvas: Canvas, p: QPainter, words, t: float, alpha: float, px: int,
           baseline: float, max_width: float) -> None:
    f = canvas.font(px, QFont.Weight.Black)
    m = QFontMetricsF(f)
    space = m.horizontalAdvance(" ")
    lines, line, width = [], [], 0.0
    for i, (word, at) in enumerate(words):
        w = m.horizontalAdvance(word)
        following = words[i + 1][1] if i + 1 < len(words) else at + 0.45
        if line and width + space + w > max_width:
            lines.append((line, width))
            line, width = [], 0.0
        width += (space if line else 0) + w
        line.append((word, at, w, following))
    lines.append((line, width))
    line_h = px * 1.28
    top = baseline - line_h * len(lines) / 2
    for i, (line, width) in enumerate(lines):
        x = canvas.W / 2 - width / 2
        y = top + i * line_h + line_h / 2
        for word, at, w, following in line:
            spoken = t >= at
            current = spoken and t < max(following, at + 0.18)
            bump = back_out(span(t, at, at + 0.2), 2.4) if spoken else 0
            scale = 1 + 0.06 * (1 - span(t, at + 0.1, at + 0.3)) * bump if current else 1.0
            canvas.text(p, word, px, x + w / 2, y, weight=QFont.Weight.Black,
                        alpha=alpha if spoken else alpha * 0.32, scale=scale, gradient=current)
            x += w + space
