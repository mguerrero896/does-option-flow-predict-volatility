# Research motion overview

A 30-second silent explainer of the public RP4 v4 study. Motion is explanatory,
not a live feed or an interactive neural network. B0/B1/B2 are nested information
sets; the fitted families are log-ridge HARQ and LightGBM.

## Shot sequence and accessible transcript

| Seconds | On screen | Meaning |
| --- | --- | --- |
| 0–3 | Title and six company logos; SPY/QQQ in a separate band | Six primary stocks; ETF context and extension |
| 3–9 | Stock bars and option-contract cards move toward forecast origin | Options use a 120-second source-time assumption, not measured client receipt |
| 9–18 | Nested 29/69/138-predictor boxes and two model families | B1 includes B0; B2 includes B1 and a heterogeneous 69-column addition; each family fits all three sets chronologically |
| 18–26 | Forecast, subsequent realized variance and growing loss curves | Future observations score the forecast, never enter its predictors |
| 26–30 | Complete historical curves and summary | Linear B2 gain +0.623%; trees −0.115%; final 25-session window did not confirm |

The curves are cumulative sums of session-mean **QLIKE(B1) − QLIKE(B2)** from
[the public loss table](../../../artifacts/rp4_v4_b2_rv15/session_losses.csv).
They are not returns, an implied-volatility surface or an intraday price path.
All 419 historical sessions are retained in chronological order. Final-window
evidence remains separate. No models were refitted or private observations read.

## Visual production

The title card was edited with the built-in image generator from the existing
cover: preserve title, subtitle and six logos; separate SPY/QQQ; remove the
schematic IV surface, all diagrams, footer, degree, institution and date. Logos
identify the researched companies and do not imply endorsement.

The decorative background was generated with Higgsfield Seedance 2.5, 10 seconds,
1080p, no audio. Brief: locked camera, midnight navy, restrained cyan/amber
particles at the lower/right edges, clean negative space; no text, logos, numbers,
chart axes, volatility surfaces or neural-network claims. Background particles
are illustrative, not data. Exact scientific text, moving arrows and curves are
composited by [render.py](render.py); generation cannot change numerical labels.

Reference principles: [3Blue1Brown](https://www.3blue1brown.com/about/)—use motion
to explain relationships rather than move text gratuitously—and
[Apple Motion guidance](https://developer.apple.com/design/human-interface-guidelines/motion)—
purposeful, restrained motion. These are design references, not copied assets.

## Rebuild

`render.py --check` uses only Python's standard library to verify the 419-session
curve and its endpoints. Rendering additionally needs Pillow, FFmpeg, the supplied
title/background files and explicit sans/serif font paths. No scientific runtime
dependency or lockfile is changed for media production.

```sh
python docs/figures/research_motion/render.py --check
python docs/figures/research_motion/render.py --background background.mp4 --title docs/figures/research_motion/title.png --font /path/to/sans.ttf --serif-font /path/to/serif.ttf --output /path/to/new-output/overview.mp4
```

Outputs must use a new path: rendering never overwrites reviewed media. The JSON
receipt records the public source identity, endpoints and final video hash.
Font and codec versions can affect raster/video bytes; this is not a claim of
bitwise-identical video on every operating system.

The README uses a finite-play animated preview linked to the MP4. The static
title and this transcript provide a non-motion alternative. Video playback and
attachment behavior depend on the browser; see
[GitHub's media guidance](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/attaching-files).

The MP4 is 1600×900 at 24 fps, H.264/yuv420p, 30 seconds, no audio, approximately
4.55 MB. The 800×450 preview is 5 fps, 48-color GIF, approximately 7.48 MB;
it plays once rather than looping indefinitely. The enlarged MP4 is the reading
version. Production used Pillow 12.3.0 and FFmpeg 8.1.1 with Segoe UI / Georgia.

```sh
ffmpeg -i overview.mp4 -filter_complex "[0:v]fps=5,scale=800:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=48:stats_mode=diff[p];[b][p]paletteuse=dither=none" -loop -1 preview.gif
```

Visual review covered the title and each explanatory stage, the shared model
input bus, source-time wording, numerical curve endpoints and static alternative.
The entire MP4 decoded without errors. [The receipt](overview.json) and
[contract](../../../tests/contract/test_research_motion.py) bind the reviewed files
to the public source table. Checks do not constitute a new scientific evaluation.
