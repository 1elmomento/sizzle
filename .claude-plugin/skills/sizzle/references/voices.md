# Narration voices

Kokoro (ONNX), run through `sizzle/narrate.py`. Always audition before committing:

```bash
sizzle voices video/ --voices af_heart,af_bella,af_nicole,bf_emma
```

This writes `video/voice-samples/<voice>.wav`. **Let the user choose** — a voice that
reads as "too old" or "too corporate" sinks an otherwise good video, and you cannot
judge that for them.

| voice | character |
|---|---|
| `af_heart` | young, warm, natural American — the safe default |
| `af_bella` | brighter, more energetic |
| `af_nicole` | softer, close-mic, intimate |
| `af_sarah`, `af_sky` | neutral American alternatives |
| `bf_emma`, `bf_isabella` | British, calmer, more formal |
| `am_michael`, `am_adam`, `bm_george` | male voices |

`b*` voices are phonemised as `en-gb`, `a*` as `en-us`; `narrate.py` handles that.

`speed` in `[audio]` is the dial for pace — 1.05 is a touch brisk and suits short-form.
Prefer lengthening a `gap` over slowing the whole read.

## Writing for a synthetic voice

- Short sentences. Full stops, not semicolons.
- Spell awkward words the way they should sound; check any product name in a sample.
- Numbers read better written as digits ("4,812") than as words.
- One idea per line. Each line becomes one scene.
