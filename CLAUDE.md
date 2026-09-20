# sizzle

Narrated product demo videos, built from an app's real UI, for Reels, TikTok, Shorts, X
and YouTube. A config file plus screenshots in; a narrated, captioned, scored video per
platform out.

## Layout

```
src/sizzle/          the engine — see README.md for the user-facing story
  config.py          sizzle.toml → settings; `for_target()` re-aims the same reel
  timing.py          the timeline; word cues ("mute-0.1") resolve here
  targets.py         platform presets, safe areas, the content band
  scenes.py          the seven archetypes; `resolve()` also finds custom types
  draw.py            Canvas: easing, text, pills, badges, background
  card.py            the tilted app card, callout rings, the typing overlay
  captions.py        word-synced burned-in captions
  render.py          Reel: frame(t), stills, video → ffmpeg
  music.py           the synthesized score; standalone, numpy + scipy only
  narrate.py         Kokoro; standalone, imports nothing from the package
  glyphs.py          38 line icons + the generated brand mark
  capture/           script · images (web · video planned)
examples/telegram-manager/   the real reel this was extracted from
templates/qt/                a starter config + capture stub
.claude-plugin/skills/sizzle/   the skill; ~/.claude/skills/sizzle symlinks to it
```

## Working on it

```bash
.venv/bin/python -m pytest          # 19 tests, <1s, no model or network needed
```

The end-to-end check is the Telegram Manager reel, which lives in its own project
because its capture script imports the app:

```bash
cd ~/Desktop/Projects/telegram-manger
~/Desktop/Projects/sizzle/.venv/bin/sizzle plan reel/
~/Desktop/Projects/sizzle/.venv/bin/sizzle stills reel/ --targets tiktok --at 30.5
```

Always look at stills before rendering a full video — a render is minutes, a still is a
second. `sheet` gives one frame per scene.

## Decisions, and why

- **sizzle is a tool you install, not a project dependency.** It carries its own PySide6,
  numpy and scipy. The capture step runs under the *target project's* interpreter
  (`SIZZLE_APP_PYTHON`, or a `.venv` found by walking up), so the two environments never
  have to agree.
- **Narration is the `voice` extra.** espeak-ng, which Kokoro uses to phonemise, is
  GPL-3.0; making it optional keeps the core MIT and lets people bring their own WAVs in
  `vo/<key>.wav` instead.
- **Motion is cued to spoken words, not timestamps.** This is the central idea. Changing
  the voice or rewriting a line re-times the whole video with no other edit.
- **Authors compose against Reels.** Every other target is mapped from it through
  `Target.remap_y` and the content band, so adding a platform is a config line rather
  than a redesign. The first 16:9 attempt was a wreck; this is what fixed it.
- **The model cache is `~/.local/share/kokoro`**, never a temp directory — an earlier
  copy was lost to a scratchpad cleanup and cost a 350 MB re-download.

## Traps

- **Hold the QImage.** `bytes(image.constBits())` on a temporary reads freed memory and
  segfaults. Bind the frame to a name first. This cost an afternoon once.
- A 47 s reel holds ~900 MB of captured screenshots in memory; capture only what is used.
- Screenshots are addressed in *logical* coordinates at `[capture] scale`; the engine
  applies the device pixel ratio.

## Open

- `web` capture (Playwright, driven from config) and `video` capture (cut from a screen
  recording) are designed but not built. They are what make the tool usable by people who
  are not fluent in Python — most of the audience.
- Not published: no GitHub repo, not on PyPI. The name is free on PyPI as of today.
- `pyproject.toml` guesses `github.com/behnamrezaei/sizzle`; confirm before publishing.
