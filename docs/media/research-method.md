# From market records to variance forecasts

https://github.com/user-attachments/assets/05bf1dc8-d37d-4e2e-b920-8e714880e6c4

Press Play above to watch the complete film. [Download the 4K MP4](https://github.com/mguerrero896/does-option-flow-predict-volatility/releases/download/research-method-film-2026-09/research-method-animated-4k.mp4) · [English subtitles](research-method.en.srt)

This 8-minute 33-second film follows FMP stock bars and Unusual Whales options
records through eligibility checks, nested information sets, Log Ridge and
LightGBM, and evaluation of the next fifteen minutes of realized variance.
Two separately authorized Apple price windows illustrate past inputs and the future target; each contains sixteen closes and fifteen one-minute returns.
The authorized observations preserve their timestamps and numerical transformations;
the model and metric calculations are worked examples, not new fitted predictions
or empirical performance estimates.

## Chapters

| Start | Explanation |
| --- | --- |
| 00:05 | Research question |
| 00:29 | Data sources and company universe |
| 00:57 | Eligibility and the information cutoff |
| 01:29 | Price history: closes, returns and past variance |
| 02:05 | Option state |
| 02:29 | Activity and state changes |
| 02:59 | Three nested information sets |
| 03:23 | Log Ridge |
| 04:03 | LightGBM |
| 04:33 | Chronological evaluation |
| 05:01 | Future observations and the RV15 target |
| 05:37 | QLIKE forecast loss |
| 06:07 | Paired comparisons and uncertainty |
| 06:43 | MAE and RMSE |
| 07:11 | Primary study and separate extensions |
| 07:39 | Microstructure exploration |
| 08:05 | Complete process |

## Method and sources

- [Data and research walkthrough](../RESEARCH_WALKTHROUGH.md).
- [Primary specification](../rp4/specification_v4.md) and [feature definitions](../../artifacts/rp4_v4_a1/specification.json).
- [Eligibility and grid producer](../../artifacts/rp4_code/materialize.py).
- [Interpreting activity and state changes](../B2_INTERPRETATION.md).

The 120-second source-time cutoff is an availability proxy, not measured customer
receipt. The added activity block also includes option-state changes, exposure
proxies and empty-window representation. The film shows selected filters rather
than the full executable specification. Historical evaluation and data collection
do not establish independent prospective confirmation.

## File identity and production

Rendered with Remotion in Higgsfield: 3840 × 2160, 24 frames/s, 513 seconds,
H.264 video and AAC ambient audio. English text appears on screen; the separate
SRT provides subtitles. There is no spoken narration.

The inline GitHub attachment and release download contain the same 60,631,753-byte
MP4. Ordinary repository clones do not download it.

SHA-256: `e17dd8226f439776d0429e246a2d5938f6a4e14b1864c63acb4e63e7ef9dde05`.

The [earlier results walkthrough](../figures/research_motion/README.md) and its
transcript remain available. This presentation update does not alter the study's
scientific evidence.
