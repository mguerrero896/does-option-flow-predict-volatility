# Research method film

[Watch or download the original-quality MP4](https://github.com/mguerrero896/does-option-flow-predict-volatility/releases/download/research-method-film-2026-09/research-method-4k.mp4) · [English subtitles](research-method.en.srt)

The 125-second film explains the RP4 v4 method: FMP stock bars and Unusual Whales
options records, eligibility, nested B0/B1/B2 inputs, chronological fitting,
ridge and LightGBM, and the next 15 minutes of realized variance. It is a conceptual
animation; illustrated records and moving cells are not empirical observations.
It contains no new evaluation results or performance estimates.

The 120-second source-time cutoff is an availability proxy, not observed customer
receipt. B2 mixes activity, option-state changes, exposure proxies and empty-window
representation. Chronological fitting does not establish independent prospective
confirmation. Research only. Not investment advice.

## Sources

- [Data and research walkthrough](../RESEARCH_WALKTHROUGH.md).
- [Frozen v4 specification](../rp4/specification_v4.md) and [feature definitions](../../artifacts/rp4_v4_a1/specification.json).
- [Eligibility and grid producer](../../artifacts/rp4_code/materialize.py).
- [B2 interpretation](../B2_INTERPRETATION.md).

The film shows selected examples of filters, not a complete executable specification.

## File identity and production

Made with Higgsfield. English captions are embedded; the separate SRT provides
editable subtitle text. The soundtrack is quiet synthesized ambience, with no
spoken narration. The output is 3840×2160 at 24 frames/s, H.264 video with AAC audio.
The first 5 seconds use the original cover scaled to 4K; the remaining 120 seconds
retain the native 4K film. The original body frames and audio packets were preserved.
Full video and audio decoding checks passed before upload.

The MP4 is hosted as a GitHub release asset, so ordinary clones do not download
its 37,448,361 bytes. This delivery preserves its bytes without regeneration.

SHA-256: `7ebcf684d6f4f3db222ff04ba785c42872d3774a5c5aa8fee1b81295e3d6c0cd`.

The [previous results walkthrough](../figures/research_motion/README.md) remains
available with its original transcript and sources.
