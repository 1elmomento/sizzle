"""Scene archetypes: the seven shapes a product reel actually needs.

Each is driven entirely by its `[[scene]]` entry in reel.toml. A project that wants
something none of these express drops a `scenes.py` next to its config and uses
`type = "custom"`; everything below stays available to it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QRadialGradient

from . import glyphs
from .card import Regions, draw_shot, ring, sample, type_into
from .config import Beat
from .draw import Canvas, back_out, clamp, ease_in, ease_in_out, ease_out, lerp, lerp_rect, span, with_alpha
from .timing import Span, Timeline

# How a card flies in and out, in units of the frame width / height.
ENTER = {"below": (0.0, 0.135, 24.0, 0.0), "above": (0.0, -0.135, -24.0, 0.0),
         "right": (0.83, 0.0, 0.0, -26.0), "left": (-0.83, 0.0, 0.0, 26.0), "fade": (0.0, 0.0, 0.0, 0.0)}
EXIT = {"left": (-0.83, 0.0, 0.0, 20.0), "right": (0.83, 0.0, 0.0, -20.0),
        "down": (0.0, 0.16, -16.0, 0.0), "fade": (0.0, 0.0, 0.0, 0.0)}


@dataclass
class Ctx:
    canvas: Canvas
    timeline: Timeline
    regions: Regions
    span: Span

    @property
    def beat(self) -> Beat:
        return self.span.beat

    @property
    def d(self) -> dict:
        return self.span.beat.data

    def cue(self, value, default=None) -> float:
        """A time written in reel.toml: a word of the line, a word index, or seconds in."""
        if value is None:
            return self.span.start if default is None else default
        return self.timeline.cue(self.span.key, value)

    def color(self, name, fallback=None) -> QColor:
        return self.canvas.theme.named(name) if name else (fallback or self.canvas.theme.accent)


# --- title: stacked lines, each landing on a word ------------------------------------------


def title(ctx: Ctx, p: QPainter, t: float) -> None:
    c, s = ctx.canvas, ctx.span
    leave = span(t, s.end - 0.35, s.end + 0.1)
    lines = ctx.d.get("line", [])
    default_y = [0.33, 0.43, 0.53, 0.63, 0.73]
    for i, entry in enumerate(lines):
        at = ctx.cue(entry.get("cue"), s.start + i * 0.22)
        px = entry.get("size", 120) * c.k
        y = c.H * entry.get("y", default_y[min(i, 4)])
        style = entry.get("style", "plain")
        k = back_out(span(t, at, at + 0.35), entry.get("bounce", 1.9))
        alpha = span(t, at, at + 0.2) * (1 - leave)
        shake = 0.0
        if style == "glitch" and t > at:
            fade = 1 - span(t, at, at + 0.35)
            shake = 10 * math.sin(t * 90) * (1 - span(t, at + 0.1, at + 0.7))
            for dx, tint in ((-14, QColor(255, 60, 90)), (14, QColor(60, 220, 255))):
                c.text(p, entry["text"], px, c.cx, y, color=tint, alpha=0.7 * fade * (1 - leave),
                       dx=dx * fade + shake, shadow=False, scale=k, weight=QFont.Weight.Black)
        c.text(p, entry["text"], px, c.cx, y - (1 - k) * px * 0.3 + (0 if style == "glitch" else 0),
               color=ctx.color(entry.get("color"), c.theme.soft if style == "soft" else c.theme.text),
               alpha=alpha, scale=entry.get("scale", 0.7) + (1 - entry.get("scale", 0.7)) * k, dx=shake,
               gradient=style in ("gradient", "glitch"), glow=1.0 if style in ("gradient", "glitch") else 0.0,
               weight=QFont.Weight.Black if style != "soft" else QFont.Weight.Medium)
    if ctx.d.get("badges"):
        density = ctx.d["badges"] if isinstance(ctx.d["badges"], (int, float)) else 0.35
        last = ctx.cue(lines[-1].get("cue"), s.start) if lines else s.start
        _badges(ctx, p, t, span(t, last, last + 1.2) * density)


# --- stats: one big counting figure per sentence, in a storm of noise -----------------------


def _badge_field(ctx: Ctx):
    if "_badges" not in ctx.d:
        import random
        rng = random.Random(7)
        c = ctx.canvas
        texts = ctx.d.get("badge_texts", ["99+", "1,204", "57", "12", "3", "248", "9", "31", "4,812",
                                          "86", "7", "120", "2", "640", "15", "1"])
        ctx.d["_badges"] = [(rng.uniform(80, c.W - 80), rng.uniform(c.H * 0.22, c.H * 0.81), rng.choice(texts),
                             rng.uniform(0, 1), rng.uniform(-1, 1), rng.uniform(0.75, 1.35), rng.random() < 0.3)
                            for _ in range(ctx.d.get("badge_count", 46))]
    return ctx.d["_badges"]


def _badges(ctx: Ctx, p: QPainter, t: float, density: float, implode: float = 0.0) -> None:
    c = ctx.canvas
    field = _badge_field(ctx)
    for i, (x, y, text, phase, drift, size, muted) in enumerate(field):
        if i / len(field) > density:
            continue
        wob_x = x + 18 * math.sin(t * 2.2 + phase * 7) + drift * 30 * t % 1
        wob_y = y + 14 * math.cos(t * 1.8 + phase * 5)
        cx = lerp(wob_x, c.cx, ease_in(implode))
        cy = lerp(wob_y, c.H * 0.47, ease_in(implode))
        pop = back_out(clamp((density * len(field) - i) / 3), 2.2)
        c.badge(p, cx, cy, text, size * pop * (1 - 0.9 * ease_in(implode)),
                0.9 * (1 - ease_in(implode)) + 0.1 * (1 - implode), muted)


def stats(ctx: Ctx, p: QPainter, t: float) -> None:
    c, s = ctx.canvas, ctx.span
    finish = ctx.timeline.impact if ctx.d.get("implode", True) else s.end
    implode = span(t, finish - 0.55, finish)
    entries = ctx.d.get("stat", [])
    density = 0.35 + 0.65 * span(t, s.vo, s.vo_end - 0.6)
    for i, (head, detail) in enumerate(ctx.d.get("notes", [])):
        born = s.vo + i * 0.55
        if t < born:
            continue
        age = t - born
        x = c.cx + (-1) ** i * (c.W * 0.157 + c.W * 0.056 * (i % 3))
        y = -120 + age * 420
        c.note_card(p, lerp(x, c.cx, ease_in(implode)), lerp(y, c.H * 0.47, ease_in(implode)),
                    head, detail, (1 - ease_in(implode)) * span(age, 0, 0.3) * 0.95,
                    (-1) ** i * 6 * (1 - implode))
    _badges(ctx, p, t, density, implode)
    for i, entry in enumerate(entries):
        begin = ctx.cue(entry.get("cue"), s.vo + i * 1.4)
        end = ctx.cue(entries[i + 1].get("cue")) if i + 1 < len(entries) else finish - 0.4
        if not (begin - 0.1 <= t <= end + 0.3):
            continue
        k = back_out(span(t, begin, begin + 0.4), 2.2)
        leave = span(t, end, end + 0.25)
        target = int(str(entry["value"]).replace(",", ""))
        shown = f"{int(target * ease_out(span(t, begin, begin + 0.8))):,}"
        a = span(t, begin, begin + 0.15) * (1 - leave)
        pool = QRadialGradient(QPointF(c.cx, c.H * 0.47), c.H * 0.27)
        pool.setColorAt(0, QColor(5, 10, 20, int(215 * a)))
        pool.setColorAt(1, QColor(5, 10, 20, 0))
        p.fillRect(QRectF(0, c.H * 0.16, c.W, c.H * 0.63), pool)
        c.text(p, shown, entry.get("size", 230) * c.k, c.cx, c.H * 0.448 - 60 * leave, gradient=True, alpha=a,
               scale=0.6 + 0.4 * k, glow=0.8, weight=QFont.Weight.Black)
        c.text(p, entry.get("label", ""), 64 * c.k, c.cx, c.H * 0.526 - 60 * leave, alpha=a, scale=0.8 + 0.2 * k)


# --- reveal: the logo lands, the name writes itself, both settle into the brand bar ---------


def reveal(ctx: Ctx, p: QPainter, t: float) -> None:
    c, s = ctx.canvas, ctx.span
    at = s.start
    flash = 1 - span(t, at, at + 0.5)
    shock = span(t, at, at + 1.1)
    k = back_out(span(t, at, at + 0.7), 1.6)
    exit_k = ease_in_out(span(t, s.end - 0.9, s.end - 0.35))
    size = lerp(c.H * 0.172 * (0.4 + 0.6 * k), 58, exit_k)
    cy = lerp(c.H * 0.396, c.H * 0.13, exit_k)
    halo = QRadialGradient(QPointF(c.cx, cy), size * 1.6)
    halo.setColorAt(0, with_alpha(c.theme.accent, 0.55 * (1 - exit_k)))
    halo.setColorAt(1, with_alpha(c.theme.accent, 0))
    p.fillRect(0, 0, c.W, c.H, halo)
    if shock < 1:
        for i, delay in enumerate((0, 0.12)):
            r = 120 + c.W * 0.83 * ease_out(clamp(shock - delay))
            p.setPen(QPen(with_alpha(c.theme.accent.lighter(130), 0.7 * (1 - shock)), 10 - i * 4))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(c.cx, c.H * 0.396), r, r)
    p.save()
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.drawImage(QRectF(c.cx - size / 2, cy - size / 2, size, size), c.logo)
    p.restore()
    name = ctx.d.get("name", c.brand.name)
    px = ctx.d.get("size", 98) * c.k
    x = c.cx - c.width_of(name, px, QFont.Weight.Black) / 2
    for i, ch in enumerate(name):
        letter = at + 0.25 + i * 0.03
        kk = ease_out(span(t, letter, letter + 0.35))
        w = c.width_of(ch, px, QFont.Weight.Black)
        c.text(p, ch, px, x + w / 2, c.H * 0.552 + 50 * (1 - kk), alpha=kk * (1 - exit_k),
               weight=QFont.Weight.Black)
        x += w
    tagline = ctx.d.get("tagline", c.brand.tagline)
    if tagline:
        c.text(p, tagline, 42 * c.k, c.cx, c.H * 0.604, color=c.theme.soft, weight=QFont.Weight.Medium,
               alpha=span(t, at + 0.9, at + 1.3) * (1 - exit_k))
    if flash > 0:
        p.fillRect(0, 0, c.W, c.H, QColor(210, 235, 255, int(235 * flash ** 2)))


# --- showcase: the app itself, one or more shots, with callouts -----------------------------


def _chip(ctx: Ctx, p: QPainter, t: float) -> None:
    chip = ctx.d.get("chip")
    if not chip:
        return
    c, s = ctx.canvas, ctx.span
    a = span(t, s.start, s.start + 0.3) * (1 - span(t, s.end - 0.25, s.end))
    chip_y = c.H * c.config.active.chip_y
    c.pill(p, chip["text"], c.cx, chip_y, px=28 * c.k, alpha=a, glyph=chip.get("glyph"),
           scale=0.85 + 0.15 * back_out(span(t, s.start, s.start + 0.4)),
           fill=with_alpha(c.theme.accent, 0.18), color=QColor("#cfe6ff"))


def _frame_name(ctx: Ctx, entry: dict, t: float, begin: float, end: float) -> str:
    frames = entry.get("frames")
    after = entry.get("after")
    if after and t >= begin + (end - begin) * after.get("at", 0.6):
        return after["name"]
    if frames:
        count = frames["count"]
        over = frames.get("over", 0.95)
        i = min(count - 1, int(span(t, begin + frames.get("delay", 0.15), begin + frames.get("delay", 0.15) + over)
                               ** frames.get("curve", 0.7) * (count - 1) + 1e-6))
        digits = frames.get("digits", 2)
        return f"{frames['prefix']}{i:0{digits}d}"
    return entry["name"]


def showcase(ctx: Ctx, p: QPainter, t: float) -> None:
    c, s = ctx.canvas, ctx.span
    _chip(ctx, p, t)
    entries = ctx.d.get("shot", [])
    for i, entry in enumerate(entries):
        begin = ctx.cue(entry.get("at"), s.start)
        end = ctx.cue(entries[i + 1].get("at")) if i + 1 < len(entries) else s.end
        tail = entry.get("hold", 0.35)
        if not (begin - 0.01 <= t <= end + tail):
            continue
        _one_shot(ctx, p, t, entry, begin, end)


def _fit(c: Canvas, want: float, src) -> float:
    """Honour the author's width, but never spill out of this target's content band."""
    target = c.config.active
    width = min(want, target.content_width) * c.W
    height = width * src[3] / src[2]
    room = target.content_height * c.H
    if height > room:
        width *= room / height
    return width


def _one_shot(ctx: Ctx, p: QPainter, t: float, entry: dict, begin: float, end: float) -> None:
    c = ctx.canvas
    enter = ease_out(span(t, begin, begin + entry.get("enter_over", 0.55)))
    leave = ease_in(span(t, end - entry.get("exit_over", 0.3), end))
    ex, ey, etx, ety = ENTER[entry.get("enter", "right")]
    xx, xy, xtx, xty = EXIT[entry.get("exit", "left")]
    ea, xa = entry.get("enter_amount", 1.0), entry.get("exit_amount", 1.0)
    etx, ety = entry.get("tilt_in", etx), entry.get("tilt_in_y", ety)
    xtx, xty = entry.get("tilt_out", xtx), entry.get("tilt_out_y", xty)
    rest_y = c.config.active.remap_y(entry.get("y", 0.453)) * c.H
    cx = c.cx + c.W * ex * ea * (1 - enter) + c.W * xx * xa * leave
    cy = rest_y + c.H * ey * ea * (1 - enter) + c.H * xy * xa * leave
    tilt_x = etx * (1 - enter) + xtx * leave
    tilt_y = ety * (1 - enter) + xty * leave
    fades_out = entry.get("exit", "left") == "fade" or entry.get("fade_out", False)
    alpha = enter * (1 - leave) if fades_out else enter * (1 - 0.2 * leave)

    src_from = ctx.regions.rect(entry.get("from", entry.get("region")))
    src_to = ctx.regions.rect(entry.get("to")) if "to" in entry else None
    if src_to is not None:
        zoom = entry.get("zoom")
        if zoom is None:                       # default: pan through the middle of the shot
            a, b = begin + (end - begin) * 0.45, begin + (end - begin) * 0.85
        else:
            a = ctx.cue(zoom[0])
            b = ctx.cue(zoom[1]) if len(zoom) > 1 and zoom[1] is not None else end
        src = lerp_rect(src_from, src_to, ease_in_out(span(t, a, b)))
    else:
        src = src_from
    name = _frame_name(ctx, entry, t, begin, end)
    width = _fit(c, entry.get("width", 0.926), src)

    rings = entry.get("ring", [])
    typing = entry.get("type_into")

    def overlay(q, to_card, k):
        for spec in rings:
            ring(q, to_card, k, ctx.regions.rect(spec.get("region", spec.get("rect"))),
                 t - ctx.cue(spec.get("cue"), begin + 0.4), color=ctx.color(spec.get("color")))
        if typing:
            field = ctx.regions.rect(typing["region"])
            shown = span(t, ctx.cue(typing.get("at"), begin + 0.45),
                         ctx.cue(typing.get("until"), begin + 0.45 + typing.get("over", 0.6)))
            blank = sample(c, name, field[0] + field[2] * 0.6, field[1] + field[3] / 2) \
                if typing.get("sample", True) else QColor(typing.get("blank", "#121b25"))
            reveal_from = ctx.cue(typing.get("results_at"), begin + 1.1)
            type_into(c, q, to_card, k, field, typing["text"], shown, src=src,
                      reveal=span(t, reveal_from, reveal_from + typing.get("results_over", 0.8)),
                      blank=blank, font_px=typing.get("font", 14), pad_left=typing.get("pad", 30))

    draw_shot(c, p, name, src, cx, cy, width, tilt_x=tilt_x, tilt_y=tilt_y, alpha=alpha,
              scale=entry.get("scale", 0.9) + (1 - entry.get("scale", 0.9)) * enter - 0.1 * leave * entry.get("shrink", 0),
              overlay=overlay if (rings or typing) else None)

    label = entry.get("pill")
    if label:
        c.pill(p, label["text"], cx + c.W * label.get("x", -0.23), c.H * label.get("y", 0.245), px=34 * c.k,
               color=QColor("white"), fill=ctx.color(label.get("color")), glyph=label.get("glyph"),
               scale=back_out(span(t, begin + 0.1, begin + 0.45), 2.2), alpha=1 - leave)

    for note in entry.get("note", []):         # a floating label pointing at what was just said
        at = ctx.cue(note.get("cue"), begin + 0.5)
        gone = ctx.cue(note.get("until"), end + 0.15)
        c.pill(p, note["text"], c.W * note.get("x", 0.435), c.H * note.get("y", 0.657), px=note.get("size", 36) * c.k,
               glyph=note.get("glyph"), fill=ctx.color(note["color"]) if note.get("color") else None,
               scale=back_out(span(t, at, at + 0.4), 2.6),
               alpha=span(t, at, at + 0.15) * (1 - span(t, gone, gone + 0.3)))



# --- icon: one idea, held as a big tile with orbiting dots ----------------------------------


def icon(ctx: Ctx, p: QPainter, t: float) -> None:
    c, s = ctx.canvas, ctx.span
    enter = ease_out(span(t, s.start, s.start + 0.55))
    leave = ease_in(span(t, s.end - 0.3, s.end))
    k = back_out(span(t, s.start, s.start + 0.5), 2)
    size = c.H * 0.13 * k
    cy = c.H * ctx.d.get("y", 0.406)
    rect = QRectF(c.cx - size / 2, cy - size / 2, size, size)
    halo = QRadialGradient(QPointF(c.cx, cy), c.H * 0.22)
    halo.setColorAt(0, with_alpha(c.theme.accent, 0.45 * enter * (1 - leave)))
    halo.setColorAt(1, with_alpha(c.theme.accent, 0))
    p.fillRect(0, 0, c.W, c.H, halo)
    p.save()
    p.setOpacity(1 - leave)
    p.setPen(Qt.PenStyle.NoPen)
    g = QLinearGradient(rect.topLeft(), rect.bottomRight())
    g.setColorAt(0, c.theme.accent)
    g.setColorAt(1, c.theme.second)
    p.setBrush(g)
    p.drawRoundedRect(rect, size * 0.28, size * 0.28)
    if size > 0:
        glyphs.paint(p, rect.adjusted(size * 0.24, size * 0.22, -size * 0.24, -size * 0.26),
                     ctx.d.get("glyph", "lock"), QColor("white"), weight=1.6)
    for i in range(12):
        angle = t * 0.8 + i * math.pi / 6
        r = c.H * 0.13 + 8 * math.sin(t * 3 + i)
        p.setBrush(with_alpha(c.theme.accent.lighter(140), 0.5 * enter))
        p.drawEllipse(QPointF(c.cx + r * math.cos(angle), cy + r * math.sin(angle)), 5, 5)
    p.restore()
    lines = ctx.d.get("line", [])
    for i, entry in enumerate(lines):
        at = ctx.cue(entry.get("cue"), s.vo + i * 0.28)
        kk = back_out(span(t, at, at + 0.35))
        last = i == len(lines) - 1
        c.text(p, entry["text"], entry.get("size", 88) * c.k, c.cx,
               c.H * entry.get("y", 0.578 + i * 0.052) - 30 * (1 - kk),
               alpha=span(t, at, at + 0.2) * (1 - leave), weight=QFont.Weight.Black,
               gradient=entry.get("style", "gradient" if last else "plain") == "gradient",
               glow=0.6 if last else 0.0, scale=0.8 + 0.2 * kk)


# --- outro: the card people screenshot ------------------------------------------------------


def outro(ctx: Ctx, p: QPainter, t: float) -> None:
    c, s = ctx.canvas, ctx.span
    k = back_out(span(t, s.start, s.start + 0.7), 1.7)
    halo = QRadialGradient(QPointF(c.cx, c.H * 0.375), c.H * 0.27)
    halo.setColorAt(0, with_alpha(c.theme.accent, 0.5 * span(t, s.start, s.start + 0.6)))
    halo.setColorAt(1, with_alpha(c.theme.accent, 0))
    p.fillRect(0, 0, c.W, c.H, halo)
    size = c.H * 0.13 * k
    p.save()
    p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    p.drawImage(QRectF(c.cx - size / 2, c.H * 0.375 - size / 2, size, size), c.logo)
    p.restore()
    c.text(p, ctx.d.get("name", c.brand.name), ctx.d.get("size", 96) * c.k, c.cx, c.H * 0.521,
           weight=QFont.Weight.Black, alpha=span(t, s.start + 0.3, s.start + 0.6),
           scale=0.85 + 0.15 * back_out(span(t, s.start + 0.3, s.start + 0.7)))
    take = ctx.cue(ctx.d.get("cue"), s.vo)
    line = ctx.d.get("line", c.brand.outro_line)
    if line:
        c.text(p, line, ctx.d.get("line_size", 49) * c.k, c.cx, c.H * 0.578, gradient=True, weight=QFont.Weight.Black,
               glow=0.7, alpha=span(t, take, take + 0.25), scale=0.8 + 0.2 * back_out(span(t, take, take + 0.45)))
    features = ctx.d.get("features", c.brand.outro_features)
    if features:
        c.text(p, "  ·  ".join(features), 34 * c.k, c.cx, c.H * 0.63, color=c.theme.soft,
               weight=QFont.Weight.Medium, alpha=span(t, take + 0.6, take + 1.0))
    shine = span(t, s.start + 0.5, s.start + 1.3)
    if 0 < shine < 1:
        g = QLinearGradient(lerp(-200, c.W * 1.19, shine), 0, lerp(0, c.W * 1.37, shine), 200)
        g.setColorAt(0, QColor(255, 255, 255, 0))
        g.setColorAt(0.5, QColor(255, 255, 255, 40))
        g.setColorAt(1, QColor(255, 255, 255, 0))
        p.fillRect(QRectF(0, 0, c.W, c.H), g)


# --- hold: nothing but the background and whatever the caption says --------------------------


def hold(ctx: Ctx, p: QPainter, t: float) -> None:
    lines = ctx.d.get("line")
    if lines:
        title(ctx, p, t)


ARCHETYPES = {"title": title, "stats": stats, "reveal": reveal, "showcase": showcase,
              "icon": icon, "outro": outro, "hold": hold}


def resolve(kind: str, custom: dict):
    """A scene type from the archetypes, or `draw_<key>` in the project's own scenes.py."""
    if kind in ARCHETYPES:
        return ARCHETYPES[kind]
    if kind in custom:
        return custom[kind]
    raise SystemExit(f"unknown scene type {kind!r}; built in: {', '.join(sorted(ARCHETYPES))}"
                     + (f"; project: {', '.join(sorted(custom))}" if custom else ""))
