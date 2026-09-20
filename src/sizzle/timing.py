"""The timeline: where each narration line lands, where each scene starts, and when each word is spoken.

Everything downstream (scenes, captions, music) asks this module for times, so a
re-recorded narration re-times the whole video without any other edit.
"""

from __future__ import annotations

import json
import wave
from dataclasses import dataclass
from pathlib import Path

from .config import Beat, Config


def wav_length(path: Path) -> float:
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


@dataclass
class Span:
    """A scene: when it starts, how long it lasts, and the line spoken inside it."""
    beat: Beat
    start: float          # visuals in
    end: float
    vo: float             # narration in (>= start)
    vo_length: float

    @property
    def key(self) -> str:
        return self.beat.key

    @property
    def length(self) -> float:
        return self.end - self.start

    @property
    def vo_end(self) -> float:
        return self.vo + self.vo_length


class Timeline:
    def __init__(self, config: Config):
        self.config = config
        self.spans: dict[str, Span] = {}
        self.order: list[Span] = []

        cursor = 0.0
        placed: list[tuple[Beat, float, float]] = []
        for beat in config.beats:
            cursor += beat.gap
            length = wav_length(config.vo / f"{beat.key}.wav") if beat.say else beat.data.get("hold", 1.5)
            placed.append((beat, cursor, length))
            cursor += length
        self.end = cursor + config.audio.tail

        for i, (beat, vo, length) in enumerate(placed):
            start = 0.0 if i == 0 else max(0.0, vo - beat.lead)
            span = Span(beat=beat, start=start, end=0.0, vo=vo, vo_length=length)
            self.spans[beat.key] = span
            self.order.append(span)
        for i, span in enumerate(self.order):
            span.end = self.order[i + 1].start if i + 1 < len(self.order) else self.end

        impacts = [s.start for s in self.order if s.beat.impact]
        self.impact = impacts[0] if impacts else self.order[0].end

    def __getitem__(self, key: str) -> Span:
        return self.spans[key]

    # --- word-level timing -------------------------------------------------------------

    def words(self, key: str) -> list[tuple[str, float]]:
        """Each word of a line with an estimated start time.

        Kokoro gives no word timings, so the line's length is split by word length plus
        a bonus for the pause that punctuation buys. It lands close enough that captions
        and callouts feel synced.
        """
        span = self.spans[key]
        words = span.beat.say.split()
        if not words:
            return []
        weights = [len(w) + 2 + (6 if w[-1] in ".!?" else 3 if w[-1] == "," else 0) for w in words]
        speak = span.vo_length - 0.15
        out, t = [], span.vo
        for word, weight in zip(words, weights):
            out.append((word, t))
            t += speak * weight / sum(weights)
        return out

    def word(self, key: str, which: int | str) -> float:
        """When a word is spoken — by index, or by the word itself ('leave')."""
        times = self.words(key)
        if isinstance(which, int):
            return times[which][1]
        return next(t for w, t in times if w.strip(".,!?;:").lower() == which.lower())

    def cue(self, key: str, value, default: float | None = None) -> float:
        """A cue as written in reel.toml.

        A number is seconds into the scene; an integer-like word index is the nth word;
        a string is a spoken word, or "start"/"end". Any of them may carry an offset:
        `"mute-0.1"` is a tenth of a second before the word "mute" is spoken.
        """
        span = self.spans[key]
        if value is None:
            return span.start if default is None else default
        if isinstance(value, bool):
            return span.start
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return self.word(key, int(value)) if isinstance(value, int) else span.start + float(value)
        text, offset = str(value), 0.0
        for sign in ("+", "-"):
            head, sep, tail = text.rpartition(sign)
            if sep and head and tail.replace(".", "", 1).isdigit():
                text, offset = head, float(sep + tail)
                break
        text = text.strip()
        if text == "start":
            base = span.start
        elif text == "end":
            base = span.end
        elif text == "vo":
            base = span.vo
        elif text.lstrip("-").isdigit():
            base = self.word(key, int(text))
        else:
            base = self.word(key, text)
        return base + offset

    # --- handed to the music and mux steps ---------------------------------------------

    def dump(self, path: Path) -> None:
        path.write_text(json.dumps({
            "vo": {s.key: [s.vo, s.vo_length] for s in self.order if s.beat.say},
            "scenes": [[s.key, s.start] for s in self.order],
            "impact": self.impact,
            "end": self.end,
        }, indent=1))
