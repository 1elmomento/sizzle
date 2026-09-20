# Telegram Manager

The video sizzle was extracted from: an eleven beat, 47 second Reel for a PySide6 desktop
app. It uses every archetype — `title`, `stats`, `reveal`, `showcase`, `icon`, `outro` —
and the `script` capture backend.

It cannot render from inside this repository, because `capture.py` imports the app it is
advertising. Copy the three files into that project and run `sizzle build` there. They are
here to be read.

Worth stealing:

- **`showcase.py` invents the account it films.** Forty-two people, two years of history,
  plausible activity curves. No real chat, name or message ever reaches the video — and
  the numbers the narration quotes are the numbers on screen, because both come from this
  fixture.
- **`capture.py` poses the app rather than recording it.** It stops the chart's own
  animation and steps its progress by hand to capture 25 frames, so the video can replay
  the chart drawing itself in at whatever speed the edit wants.
- **`sizzle.toml` cues motion to spoken words.** The ring around the mute button appears
  at `"mute-0.1"` — a tenth of a second before the word is said. Re-record the narration
  in another voice and every callout still lands.
