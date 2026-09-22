# reel.toml reference

Beyond what SKILL.md covers.

## `[brand]`

| key | |
|---|---|
| `name` | shown in the reveal, the brand bar and the outro |
| `logo` | path to a PNG, relative to reel.toml; falls back to a generated initials tile |
| `tagline` | the line under the name at the reveal |
| `outro_line` | the closing promise |
| `outro_features` | the dot-separated list at the very end |
| `font` | family name; must be installed (default "Noto Sans") |

## `[format]`

`size` is `"9:16"`, `"16:9"`, `"1:1"`, `"4:5"` or `"1920x1080"`. `fps` defaults to 30.
The archetypes are tuned for 9:16; other shapes need the `y` and `width` fractions
revisited scene by scene.

## `[theme]`

`accent`, `second`, `third` drive every gradient; `warn` is the "this is going away"
colour. `background` is three hex stops, top to bottom. Colours in scenes may name a
theme key (`color = "warn"`) or give a literal (`color = "#ff7b7b"`).

## `[audio]`

| key | |
|---|---|
| `voice`, `speed` | narration |
| `bpm` | the bed's tempo (default 100) |
| `chords` | `minor-lift` (default), `bright`, `tense` |
| `music` | bed level against the voice (default 0.42) |
| `duck` | how far the bed drops under speech (default 0.6) |
| `tail` | seconds of music after the last word (default 2.4) |

The bed is synthesized from scratch — drums, bass, pad, arpeggio, risers, a sidechain
pump on the kick and a boom on the `impact` scene. No licensing, and it lands on the
cuts because it is built from the same timeline.

## `[capture]`

`script` (relative to reel.toml) and `scale` (2). Omit the whole table for a video with
no screenshots.

## Outputs

`mux` writes, into `--out` (default `reel/out`):

- `<name>-music.mp4` — voice over the bed
- `<name>-voice-only.mp4` — voice alone, for when the platform's own audio is used
- `cover.jpg` — the frame just after the reveal
