---
name: sizzle
description: Build a narrated, scored promo video (Instagram Reel, TikTok, YouTube Short or landscape) for a software project from its own UI — synthesized narration, motion graphics over real screenshots, an original music bed, burned-in captions, and a cover frame. Use when the user asks for a promo video, demo video, reel, trailer, teaser or launch video for an app, or wants to update or re-cut one.
---

# sizzle

A reel is built from **three small project files** driving a shared engine (`sizzle`,
in this skill's folder). Nothing about the engine is project-specific; nothing in the
project repeats the engine.

```
<project>/video/
  sizzle.toml    the video, one [[scene]] entry per beat
  capture.py     only for [capture] backend = "script"
  scenes.py      optional — custom drawing the archetypes can't express
```

`[capture] backend` is `script` (a Python file that drives the app), `images` (a folder
of screenshots you already have), `web` (a browser driven from config) or `video` (cut
out of a screen recording). Prefer a backend that needs no Python when one fits.

```bash
sizzle build video/          # or: uvx sizzle build video/
```

The capture step runs under the *project's* interpreter (sizzle finds `.venv/bin/python`,
or set `SIZZLE_APP_PYTHON`), so sizzle never has to share an environment with the app.

Steps: `build` (all of them), `narrate`, `voices`, `capture`, `plan`, `stills`, `sheet`,
`video`, `audio`, `mux`. Add `--targets reels,tiktok,x` to override the platforms.

## The order of work

Follow this; it is the order that avoids wasted renders.

1. **Learn the product first.** Read the README, the UI code, and run the app if you
   can. Every spoken claim must be true of the real build. Do not describe a feature
   you have not seen work. Ask the user to confirm anything you are unsure of.
2. **Write the script and show it to the user before rendering anything.** Lead with
   what the product is *for*, not with its feature list. Roughly: hook → the problem,
   with real numbers → the reveal → three to five features, each one shot → the
   closing promise. 45–60 s for a Reel.
3. **Audition voices** (`voices`) and let the user pick. Never assume.
4. **Write `capture.py`.** See `references/capture-guide.md`. Its whole job is to
   produce `shots/<name>.png` and a `regions.json` of named rectangles.
5. **`narrate`, then `capture`, then `plan`** to see the timeline. Real narration
   lengths decide every cut, so nothing can be timed before this.
6. **`sheet`** — one still per scene. **Look at them.** Fix framing, crops and
   overlaps here, where a render costs a second instead of five minutes.
7. **`video`, `audio`, `mux`.**
8. **Show the user the stills and the final file**, and write the caption (see
   `references/caption-guide.md`).

## sizzle.toml

One `[[scene]]` per beat, in order. Shared keys:

| key | meaning |
|---|---|
| `key` | the scene's name; also the narration file's name |
| `say` | the line spoken over it (omit for a silent beat, then set `hold`) |
| `gap` | silence before the line — this is your pacing dial |
| `lead` | the visuals start this long before the line (default 0.25) |
| `caption` | burn word-synced captions for this line |
| `type` | the archetype (below) |
| `impact` | mark the reveal: the music drops and the screen darkens into it |

**Cues.** Anywhere a time is wanted, write a spoken word (`cue = "mute"`), a word index
(`cue = 3`), seconds into the scene (`cue = 1.4`), or `"start"` / `"vo"` / `"end"` — and
any of them takes an offset: `"mute-0.1"`, `"leave+0.3"`. This is why re-recording the
narration re-times the whole video without touching anything else.

**Archetypes** (`type =`):

- `title` — stacked lines landing on their words. `[[scene.line]]` with
  `text`, `cue`, `size`, `y` (fraction of height), `style` (`plain`/`soft`/`gradient`/`glitch`).
- `stats` — a counting figure per sentence over a storm of notification cards and unread
  badges. `[[scene.stat]]` with `value`, `label`, `cue`; plus `notes`, `badge_count`.
- `reveal` — logo burst, the name written letter by letter, the tagline; settles into the
  small brand bar. Put `impact = true` here.
- `showcase` — the workhorse: one or more `[[scene.shot]]` of the real app.
- `icon` — one idea as a big glyph tile with orbiting dots and stacked words.
- `outro` — logo, name, promise, feature list, a shine sweep.
- `hold` — background and captions only.

**`[[scene.shot]]`** — the grammar of the feature scenes:

| key | meaning |
|---|---|
| `name` | the screenshot |
| `frames` | `{prefix, count, over, delay, curve}` — play a captured animation |
| `after` | `{name, at}` — swap to another shot partway through |
| `from` / `to` | the crop, and the crop to pan/zoom toward |
| `zoom` | `[start_cue, end_cue]` for that move |
| `at` | when this shot takes over from the previous one |
| `enter` / `exit` | `below`/`above`/`left`/`right`/`fade`, with `enter_amount`, `exit_amount`, `tilt_in`, `tilt_out` |
| `width`, `y`, `scale` | framing, as fractions of the frame |
| `pill` | `{text, color, glyph}` — a label riding beside the card |
| `[[scene.shot.ring]]` | `{region, cue, color}` — a pulsing highlight: "look here" |
| `[[scene.shot.note]]` | `{text, cue, glyph, x, y}` — a floating label |
| `type_into` | `{region, text, at, over, results_at}` — retype a query into a captured field and reveal the results |

A crop is `[x, y, w, h]`, a region name, or `{region, pad, dx, dy, dw, dh, x, y, width, height, anchor}`
where `anchor = "bottom"` holds it to the foot of the region.

Glyph names are in `sizzle/glyphs.py`.

## Custom scenes

`reel/scenes.py` with `def draw_<type>(ctx, painter, t)` adds a scene type. `ctx` gives
`ctx.canvas` (text, pills, background, logo, `shot()`), `ctx.span` (`start`, `end`, `vo`),
`ctx.cue(...)` and `ctx.d` (the scene's own config). Use `sizzle.draw` for easing —
`span`, `ease_out`, `back_out` — and `sizzle.card.draw_shot` for app cards. Reach for
this only after an archetype genuinely will not bend.

## Environment

- **Narration and music** run in `~/.local/share/sizzle/tts`
  (`kokoro-onnx soundfile espeakng-loader scipy`). The Kokoro model lives in
  `~/.local/share/kokoro` — a shared cache, downloaded once by
  `python sizzle/narrate.py fetch`. Never put either in a project venv, and never in a
  temp directory: a 350 MB model in `/tmp` is a re-download on the next machine reboot.
- **Rendering** needs PySide6 (the project's venv, for a Qt app) and `ffmpeg`.
- Override interpreters with `SIZZLE_TTS_PYTHON`, `SIZZLE_AUDIO_PYTHON`,
  `SIZZLE_APP_PYTHON`; the model cache with `SIZZLE_MODELS`.

## The score

Generated per project, not chosen from presets. `[audio] seed` (default: the brand name)
picks a style, key, mode, progression, drum kit, one voice each for bass, lead and pad,
and a melodic motif — a rhythm and a contour phrased in four-bar answers, resolving home
every fourth bar. The melody reads the narration timeline: under a spoken line it drops to
the notes that carry the phrase, and states itself in full between lines. Two products
never get the same score. Reroll without touching anything else:

```bash
sizzle audio video/ --seed 42       # try another; keep the one you like in [audio] seed
```

The narration always wins. The bed is split at 900 Hz and 5.2 kHz and ducked per band, so
the 1.5-5 kHz consonant range sits ~20 dB under a spoken line while the low end keeps
carrying the groove — a broadband duck leaves bright content sitting on the voice, which
is what reads as a sharp ring over the narrator. `sizzle audio` also writes `music.wav`,
the bed alone: the only honest way to check how much music is on top of the voice, since
`mix.wav` minus `voice.wav` leaves a residue that hides the answer.

`[audio] style` pins one of `neon`, `eight`, `lofi`, `drive`, `organic`, `dub`, `still`.
`[audio] chords` pins a mode (`aeolian`, `dorian`, `phrygian`, `ionian`, `mixolydian`,
`lydian`, `harmonic`); the old names still work. `[format] cover_at` sets the cover frame's
time in seconds, for when the default lands between scenes.

## Things that will bite

- **Hold the QImage.** `bytes(image.constBits())` on a temporary reads freed memory and
  segfaults. Bind the frame to a name first. `sizzle` does; custom code must too.
- **Screenshots are big.** A 47 s reel holds ~900 MB of captured frames in memory.
  Capture only the frames you will use.
- **Capture at `scale = 2`** and address everything in logical coordinates; the engine
  handles the device pixel ratio.
- **Non-9:16 formats** need the `y` and `width` fractions revisited — the archetypes are
  tuned for tall video.
- Generated files (`shots/`, `vo/`, `stills/`, `*.wav`, `silent.mp4`, `timeline.json`)
  do not belong in git. Commit `sizzle.toml`, `capture.py` and `scenes.py`.

## Worked example

`examples/telegram-manager/` is a complete, rendering example: an eleven beat video using
every archetype, a capture script that drives a PySide6 app offscreen, and a
`showcase.py` that invents the account it films so no real data is ever shown.
