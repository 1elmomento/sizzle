# sizzle

**Narrated product demo videos, built from your app's real UI, for every platform you ship to.**

You built the thing. Now you need a forty-five second video of it for Instagram, TikTok,
X and YouTube — narrated, captioned, scored, and not embarrassing. sizzle makes that
video from a config file and your app's own screens.

---

> ## ⚠️ This is a work in progress
>
> sizzle is **not released**. It is not on PyPI, there are no tagged versions, and
> `pip install sizzle` does **not** work. The only way to run it is from source, below.
>
> What that means for you:
>
> - **Interfaces will change.** Config keys, CLI flags and scene options are still moving.
>   Expect to edit your `sizzle.toml` when you pull.
> - **Two of the four capture backends are not built.** `script` and `images` work.
>   `web` and `video` are designed and stubbed, and will exit with a clear error.
> - **It has produced exactly two real videos** — the example in this repo and sizzle's
>   own promo. It has not been run against many apps, many fonts, or many platforms.
> - **Rough edges are likely.** Non-9:16 targets in particular are under-tested; the
>   scene archetypes are tuned for tall video.
>
> It does work, end to end, today. But treat it as something to experiment with, not
> something to depend on. Issues and reports of what broke are genuinely useful.
>
> [`ROADMAP.md`](ROADMAP.md) lists what is missing, what is next, and what is known
> to be rough.

---

## What it actually does

1. **Narrates** your script, line by line, in a synthetic voice you pick (or your own
   recordings — see [Narration](#narration)).
2. **Captures** your product: screenshots you already have, or a Python script that poses
   the app deliberately.
3. **Composes** the video — the timeline is derived from the *actual* length of each
   narrated line, so nothing is hand-timed and re-recording re-times everything.
4. **Scores** it with an original bed generated for your project: a seed taken from your
   brand name picks a style, key, mode, chord progression, drum kit, a synthesis voice
   each for bass, lead and pad, and a melodic motif. Nothing to license, and no two
   projects get the same track.
5. **Captions** it word by word, because most people watch with the sound off.
6. **Ships** it to each platform's size, duration limit and safe area.

## Requirements

- **Python 3.11+**
- **ffmpeg** on your `PATH` (a system package — pip cannot supply it)
- **A font** — Noto Sans by default
- Rendering is CPU only: roughly a minute per ten seconds of 1080×1920 video

## Install

Not on PyPI. From source:

```bash
git clone https://github.com/1elmomento/sizzle
cd sizzle
python -m venv .venv
.venv/bin/pip install -e .
.venv/bin/sizzle --help
```

Add narration with the `voice` extra:

```bash
.venv/bin/pip install -e ".[voice]"
```

That pulls [Kokoro](https://github.com/thewh1teagle/kokoro-onnx), which downloads about
350 MB of model on first use into `~/.local/share/kokoro`. The extra is optional on
purpose: espeak-ng, which Kokoro uses to turn text into phonemes, is GPL-3.0, so nobody
inherits it by installing sizzle. Prefer a human voice? Drop WAV files named after your
scene keys into `<project>/vo/` and the rest of the pipeline is unchanged.

## Quickstart

The shortest path needs **no Python at all** — just screenshots you already have.

**1. Make a folder with your screenshots.**

```
notekeeper-video/
  screenshots/
    library.png
    search.png
```

**2. Write `sizzle.toml` next to them.** This is the entire video:

```toml
[brand]
name = "Notekeeper"
tagline = "Every note, one keystroke away."
outro_line = "Write it down. Find it later."

[format]
targets = ["reels"]

[capture]
backend = "images"
from = "screenshots"
size = [1200, 800]      # the logical size of your PNGs
scale = 2               # they are 2x that on disk (retina); use 1 if not

  [capture.regions]     # name the rectangles you want to point at
  note_list = [292, 90, 870, 620]
  first_note = [292, 90, 870, 88]

[[scene]]
key = "hook"
say = "Your notes are everywhere. You never find them again."
type = "title"
  [[scene.line]]
  text = "Your notes"
  cue = 0
  size = 110
  y = 0.40
  [[scene.line]]
  text = "are everywhere."
  cue = "everywhere"        # this line lands on that spoken word
  size = 110
  y = 0.50
  style = "glitch"

[[scene]]
key = "reveal"
say = "Meet Notekeeper."
gap = 0.8
type = "reveal"
impact = true               # the music drops here

[[scene]]
key = "search"
say = "Search finds any note in milliseconds."
caption = true
type = "showcase"
chip = { text = "SEARCH", glyph = "search" }
  [[scene.shot]]
  name = "search"                       # screenshots/search.png
  from = { region = "note_list", pad = 16 }
  enter = "right"
    [[scene.shot.ring]]
    region = "first_note"
    cue = "milliseconds-0.2"            # highlight, 0.2s before that word

[[scene]]
key = "outro"
say = "Notekeeper. Write it down. Find it later."
type = "outro"
cue = "Write-0.1"
```

**3. Run it a step at a time.** Don't use `build` the first time — you want to see each
stage:

```bash
sizzle capture .     #   2 shots: library, search
sizzle narrate .     #   hook 2.77s · reveal 1.26s · search 2.18s · outro 2.69s
sizzle plan .        #   the timeline, and whether it fits each platform
```

`plan` prints exactly what you are about to get, before you spend a minute rendering:

```
scene        type            in      vo     out  line
hook         title         0.00    0.30    3.62  Your notes are everywhere...
reveal       reveal        3.62    3.87    5.38  Meet Notekeeper.
search       showcase      5.38    5.63    7.75  Search finds any note in milliseconds.
outro        outro         7.75    8.00   13.10  Notekeeper. Write it down...
total 13.10s
  reels      1080x1920 30fps  393 frames
```

**4. Look before you render.**

```bash
sizzle sheet .       # one PNG per scene, into stills/
```

This is the step people skip and regret. Fix framing here, where it costs a second
instead of a minute.

**5. Render.**

```bash
sizzle video .
sizzle audio .
sizzle mux .
```

You end up with, in `out/`:

```
notekeeper-music.mp4        the video, scored
notekeeper-voice-only.mp4   same video, no music (some platforms prefer it)
notekeeper-cover.jpg        a thumbnail
```

Once you trust it, `sizzle build .` chains all six steps.

## The config is the video

One `[[scene]]` entry per beat. Shared keys:

| key | meaning |
|---|---|
| `key` | the scene's name; also its narration file's name |
| `say` | the line spoken over it |
| `gap` | silence before the line — your main pacing dial |
| `lead` | the visuals start this long before the line |
| `caption` | burn word-synced captions for this line |
| `type` | the archetype |
| `impact` | mark the reveal: the music drops and the screen darkens into it |

Scene types: `title`, `stats`, `reveal`, `showcase`, `icon`, `outro`, `hold`, and
`custom` for a Python function you write yourself in `scenes.py`.

### Motion is cued to spoken words

```toml
cue = "mute-0.1"          # a highlight, a tenth of a second before the word "mute"
```

This is the idea the whole tool is built around. Anywhere a time is wanted you can write
a spoken word, a word index (`cue = 3`), seconds into the scene (`cue = 1.4`), or
`"start"` / `"vo"` / `"end"` — each taking an offset. Change the voice, rewrite the line,
translate the script: every callout still lands where it should, with no other edit.

## Capturing your product

The only part that knows what your app is.

| backend | you write | status |
|---|---|---|
| `images` | a folder path | **works** — screenshots you already have |
| `script` | Python that drives the app | **works** — full control, pose the UI exactly |
| `web` | config: go here, click that, shoot this | *not built yet* |
| `video` | timestamps into a screen recording | *not built yet* |

Every backend writes the same thing: `shots/<name>.png` and a `regions.json` naming the
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

Eleven presets ship: `reels`, `tiktok`, `shorts`, `stories`, `x`, `x-square`, `youtube`,
`linkedin`, `square`, `landscape`, `portrait`. The archetypes are tuned for 9:16, so
landscape and square targets usually need their `y` and `width` fractions revisited.

## Narration

Audition voices before you commit:

```bash
sizzle voices . --voices af_heart,af_bella,bf_emma
```

## The score

Generated per project, not chosen from presets. `[audio] seed` — the brand name by
default — picks the whole arrangement, so two products never get the same bed. Reroll it
without re-rendering the video:

```bash
sizzle audio . --seed 42      # keep the one you like as [audio] seed = 42
```

`[audio] style` pins one of `neon`, `eight`, `lofi`, `drive`, `organic`, `dub`, `still`.

The narration always wins: the bed is split at 900 Hz and 5.2 kHz and ducked per band, so
the consonant range sits about 20 dB under a spoken line while the low end keeps carrying
the groove. `sizzle audio` also writes `music.wav`, the bed on its own.

## Example

[`examples/telegram-manager/`](examples/telegram-manager) is a complete, eleven-beat reel
for a desktop app, including the fixture that invents the account it films so no real data
reaches the video. [`video/`](video) is sizzle's own promo, built with sizzle.

## Contributing

[`ROADMAP.md`](ROADMAP.md) is the to-do list, ordered by what blocks someone else
using this. Early enough that the most useful contribution is telling me what broke. If you point it
at your app and it falls over, an issue with your `sizzle.toml` and the error is worth
more than a patch right now.

Run the tests with:

```bash
.venv/bin/python -m pytest
```

## Licence

MIT. See [LICENSE](LICENSE).
