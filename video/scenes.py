"""Custom scene types for sizzle's own reel.

`tally` replaces the `stats` archetype for the problem beat. `stats` rains notification
cards and unread badges down the frame — imagery built for a messaging app, and wrong
for a developer tool, where the pain is not unread messages but the hours a launch video
costs you every single release. This draws that as a receipt instead: line items that
arrive on the words that name them, then a rule and a total.
"""

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QFont, QPen

from sizzle.draw import back_out, ease_out, span, with_alpha


def draw_tally(ctx, p, t) -> None:
    c, s = ctx.canvas, ctx.span
    target = c.config.active
    rows = ctx.d.get("row", [])
    leave = span(t, s.end - 0.45, s.end)
    if leave >= 1:
        return

    left, right = c.W * 0.14, c.W * 0.86          # the Reels safe width, exactly
    label_px, value_px = 42 * c.k, 44 * c.k
    base, step = ctx.d.get("top", 0.29), ctx.d.get("step", 0.060)

    for i, row in enumerate(rows):
        at = ctx.cue(row.get("cue"), s.vo + i * 1.1)
        k = ease_out(span(t, at, at + 0.4))
        alpha = span(t, at, at + 0.22) * (1 - leave)
        if alpha <= 0:
            continue
        y = c.H * target.remap_y(base + i * step)
        slide = (1 - k) * c.W * 0.045
        label, value = row.get("text", ""), row.get("value", "")
        lw = c.width_of(label, label_px, QFont.Weight.Medium)
        vw = c.width_of(value, value_px, QFont.Weight.Black)
        c.text(p, label, label_px, left + lw / 2 - slide, y,
               color=c.theme.soft, alpha=alpha, weight=QFont.Weight.Medium)
        c.text(p, value, value_px, right - vw / 2 + slide, y, alpha=alpha,
               color=ctx.color(row.get("color"), c.theme.text),
               weight=QFont.Weight.Black, scale=0.85 + 0.15 * k)
        x0, x1 = left + lw + 20, right - vw - 20    # the leader draws itself across
        if x1 > x0:
            p.setPen(QPen(with_alpha(c.theme.muted, 0.55 * alpha), 2 * c.k, Qt.PenStyle.DotLine))
            p.drawLine(QPointF(x0, y + 3), QPointF(x0 + (x1 - x0) * k, y + 3))

    total = ctx.d.get("total")
    if not total:
        return
    at = ctx.cue(total.get("cue"), s.vo_end - 0.4)
    k = back_out(span(t, at, at + 0.5), 1.8)
    alpha = span(t, at, at + 0.25) * (1 - leave)
    if alpha <= 0:
        return
    rule_y = c.H * target.remap_y(base + len(rows) * step)
    half = (right - left) / 2 * min(1.0, ease_out(span(t, at, at + 0.35)))
    p.setPen(QPen(with_alpha(c.theme.accent, 0.75 * alpha), 3 * c.k))
    p.drawLine(QPointF(c.cx - half, rule_y), QPointF(c.cx + half, rule_y))
    y = rule_y + c.H * ctx.d.get("total_gap", 0.042)
    label, value = total.get("text", ""), total.get("value", "")
    lw = c.width_of(label, label_px, QFont.Weight.Black)
    vw = c.width_of(value, value_px * 1.15, QFont.Weight.Black)
    c.text(p, label, label_px, left + lw / 2, y, color=c.theme.text,
           alpha=alpha, weight=QFont.Weight.Black)
    c.text(p, value, value_px * 1.15, right - vw / 2, y, gradient=True, glow=0.9,
           alpha=alpha, weight=QFont.Weight.Black, scale=0.8 + 0.2 * k)
