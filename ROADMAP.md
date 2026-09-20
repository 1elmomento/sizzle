# Roadmap

Where sizzle is, and what has to happen next. Written down so the next person — or the
next session — does not have to rediscover it.

**Today:** the engine, the seven archetypes, the generated score and the `script` and
`images` capture backends work end to end. Two real videos have been produced with it:
`examples/telegram-manager/` and `video/`, sizzle's own promo. It is not released, not on
PyPI, and interfaces are still moving.

The ordering below is by *what unblocks someone else using this*, not by what is most
interesting to build.

---

## Now — the gap between "installed" and "first video"

Everything here is a reason a willing stranger gives up.

- [ ] **`sizzle init`.** There is no scaffold. A newcomer has to hand-write their first
      `sizzle.toml` out of the README, and the README's own quickstart cannot be run as
      written until they do. `sizzle init video/` should produce a commented config, a
      `screenshots/` folder and a one-page README. This is the single highest-value item
      in this file.
- [ ] **`web` capture backend** (Playwright, driven from config: go here, click that,
      shoot this). Designed, stubbed, exits with a clear error. Together with `video`
      capture it is what makes sizzle usable by people who are not fluent in Python —
      most of the audience. Today the only no-Python path is `images`, which assumes you
      already have the screenshots.
- [ ] **CI.** The 19 tests run on one laptop. A GitHub Actions workflow on push, on at
      least Linux, ideally macOS too, since the project has only ever run on Linux.
- [ ] **Better failure messages.** `no sizzle.toml in .` is correct and useless. It should
      say what to do about it, and point at `sizzle init` once that exists.
- [ ] **A release.** No build tooling is installed, no version is tagged, nothing is on
      PyPI. The packaging metadata is already correct, so this is `python -m build`, a
      tag, and a decision about the name. Until then the README must keep saying
      `pip install sizzle` does not work.

## Next — making it good rather than possible

- [ ] **`video` capture backend** — cut frames out of an existing screen recording by
      timestamp. Works for anything: native apps, mobile, a terminal.
- [ ] **Draft render mode.** A full 50 s reel is about two minutes at 1080×1920. A
      `--draft` flag rendering at half resolution and a fast x264 preset would make the
      edit loop bearable. `sheet` covers some of this, but not motion.
- [ ] **`sizzle regions`** — render the shots with their named rectangles drawn on top.
      Regions are the most error-prone part of authoring: a guessed rectangle produces a
      callout ring over blank space, and you only find out after a render. Being able to
      *see* them would have caught two such bugs in this repo's own promo.
- [ ] **Teach measuring, not guessing, in `references/capture-guide.md`.** Same root
      cause. A capture script should derive region rectangles from the widgets or text it
      draws, never from arithmetic on pixel offsets.
- [ ] **Promote the `tally` scene to an archetype.** `video/scenes.py` has one, written
      because `stats` bakes in a messaging metaphor — it rains notification cards and
      unread badges, which suits Telegram and nothing else. A neutral "line items and a
      total" archetype belongs in the engine.
- [ ] **`cover_at` should accept a cue,** not just seconds — `cover_at = "reveal+0.5"`
      like every other time in the config. Seconds were the quick fix for a cover frame
      landing in the gap between scenes.
- [ ] **Offer the music bed as an output.** `sizzle audio` already writes `music.wav`;
      `mux` should be able to ship a music-only cut alongside the scored and voice-only
      ones.

## Later — the bigger bets

- [ ] **Non-9:16 targets, properly.** Eleven presets ship, but the archetypes are tuned
      for tall video: landscape and square need their `y` and `width` fractions
      revisited, and today an author has to do that by hand per scene. The content-band
      mapping was built for exactly this and is not yet carrying its weight.
- [ ] **More of the score's palette.** Roughly one project in seven draws the same style
      as another. Those two get different keys, progressions, grooves and melodies —
      different songs in one genre — but more styles and instrument voices would spread
      it further. This is now a data edit, not a rewrite.
- [ ] **A dynamics arc.** The score has one intensity from the drop to the sign-off. It
      should build: thinner under the first feature, fullest at the last, and a real
      ending rather than a fade.
- [ ] **Translation.** The cue system means a translated script re-times the whole video
      with no other edit — rewrite the lines, re-narrate, done. This is close to free and
      has never been tried.
- [ ] **Windows and macOS.** Developed and only ever run on Linux. The Qt offscreen
      rendering and the ffmpeg pipe are the likely friction.

## Known rough edges

Not features — things that are wrong or awkward right now.

- [ ] `examples/telegram-manager/` cannot be rendered from this repo; its capture script
      imports an app that lives elsewhere. It documents a real reel but is not runnable.
- [ ] A long reel holds a lot of captured screenshots in memory — roughly 900 MB for 47
      seconds. Capture only the frames you use; there is no streaming path.
- [ ] No way to preview audio against the video without a full render.
- [ ] The narration voice list is hardcoded to ten Kokoro voices in `narrate.py`.
- [ ] `[audio] speed` applies to the whole script; there is no per-line pacing control
      beyond `gap`.

## Open questions

- **Is `sizzle` the right name to claim on PyPI?** It was free as of this writing. It is
  also a generic word, which cuts both ways.
- **How much should the tool decide for you?** The config is expressive and therefore
  long — the promo in `video/` is about 200 lines for ten beats. A `--auto` mode that
  takes a script and some screenshots and picks the archetypes itself would be a very
  different product, and possibly the better one.
- **Should capture and composition be separable?** Today `regions.json` is the contract
  between them, which works. Making it a documented, versioned format would let people
  write capture backends sizzle does not ship.

---

Contributions welcome, but at this stage the most useful thing you can do is point sizzle
at your own app and tell me what broke.
