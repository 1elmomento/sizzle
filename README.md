# sizzle

**Narrated product demo videos, built from your app's real UI, for every platform you ship to.**

You built the thing. Now you need a forty-five second video of it for Instagram, TikTok,
X and YouTube — narrated, captioned, scored, and not embarrassing. sizzle makes that
video from a config file and your app's own screens.

```bash
pip install sizzle
sizzle build video/ --targets reels,tiktok,x
```

Out comes one video per platform, each with the music mixed, a voice-only cut for when
the platform supplies its own audio, and a cover frame.

## What it actually does

1. **Narrates** your script, line by line, in a synthetic voice you pick (or your own
   recordings — see [Narration](#narration)).
2. **Captures** your product: a browser driven from config, screenshots you already have,
   a screen recording, or a Python script that poses the app deliberately.
3. **Composes** the video — the timeline is derived from the *actual* length of each
   narrated line, so nothing is hand-timed and re-recording re-times everything.
4. **Scores** it: an original synthesized bed — drums, bass, pad, risers, a sidechain
   pump, an impact on the reveal — built from the same timeline, so it lands on the cuts.
   Nothing to license.
5. **Captions** it word by word, because most people watch with the sound off.
6. **Ships** it to each platform's size, duration limit and safe area.

## The config is the video

One entry per beat. This is the whole of a feature scene:

```toml
[[scene]]
key = "clean"
say = "When it's time to clean up, mute a channel, or leave dozens of groups at once."
caption = true
type = "showcase"
chip = { text = "BULK ACTIONS", glyph = "stack" }
  [[scene.shot]]
  name = "sheet"
  from = { region = "panel", pad = 12 }
  enter = "below"
    [[scene.shot.ring]]
    region = "mute_button"
    cue = "mute-0.1"          # a highlight, a tenth of a second before the word
```

That `cue = "mute-0.1"` is the idea the whole tool is built around: **motion is cued to
spoken words, not to timestamps.** Change the voice, rewrite the line, translate the
script — every callout still lands where it should.

Scene types: `title`, `stats`, `reveal`, `showcase`, `icon`, `outro`, `hold`, and
`custom` for a Python function you write yourself.

## Capturing your product

The only part that knows what your app is. Pick the backend that fits:

| backend | you write | good for |
|---|---|---|
| `images` | a folder path | screenshots you already have |
| `web` | config: go here, click that, shoot this | web apps *(planned)* |
| `video` | timestamps into a screen recording | anything at all — native, mobile, terminal *(planned)* |
| `script` | Python that drives the app | full control; pose the UI exactly |

Every backend writes the same thing: `shots/<name>.png`, and a `regions.json` naming the
rectangles worth pointing at. The config then says "zoom to `chart`" or "ring
`mute_button`" and never mentions a pixel.

## Platforms

```toml
[format]
targets = ["reels", "tiktok", "shorts", "x", "youtube", "linkedin"]
```

A target is more than a canvas size. Short-form apps paint their own interface over your
video — caption and username along the bottom, a column of buttons up the right edge — so
each target carries the margins words must stay out of, and its duration limit. `sizzle
plan` tells you if the script is too long *before* you render. Authors compose against
Reels; every other target is mapped from it, so adding a platform is a config line rather
than a redesign.

## Narration

`pip install sizzle[voice]` adds [Kokoro](https://github.com/thewh1teagle/kokoro-onnx).
Audition before you commit:

```bash
sizzle voices video/ --voices af_heart,af_bella,bf_emma
```

The voice extra is optional deliberately: espeak-ng, which Kokoro uses to turn text into
phonemes, is GPL-3.0, so nobody inherits it by installing sizzle. Prefer a human? Drop
WAV files named after your scene keys into `video/vo/` and the rest of the pipeline is
unchanged.

## Requirements

Python 3.11+, `ffmpeg`, and a font (Noto Sans by default). Rendering is CPU only — about
a minute per ten seconds of 1080×1920 video.

## Example

[`examples/telegram-manager/`](examples/telegram-manager) is the real thing sizzle was
extracted from: an eleven beat, 47 second Reel for a desktop app, including the fixture
that invents the account it films so no real data ever reaches the video.

## Status

Early. The engine, the archetypes, the scoring and the `script` and `images` backends
work and have shipped a real video. `web` and `video` capture are next. Interfaces may
move before 1.0.

## Licence

MIT. See [LICENSE](LICENSE).
