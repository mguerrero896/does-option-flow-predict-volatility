"""A reader-first 90-second public-evidence walkthrough; no fitting or private reads.

--check needs only stdlib. --frames-only writes chapter samples/contact sheet/SRT.
Rendering needs the existing Pillow and FFmpeg tools, not new dependencies.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

from render import FAMILIES, ROOT, curves

HERE = Path(__file__).resolve().parent
W, H, FPS = 1600, 900, 24
NAVY, PANEL, CYAN, GOLD, WHITE, MUTED = (
    "#04101d",
    "#0b2030",
    "#87d9e4",
    "#edbd63",
    "#f2f5f7",
    "#adc1cf",
)
PATHS = {
    "spec": "artifacts/rp4_v4_a1/specification.json",
    "stats": "artifacts/rp4_v4_b4/primary_statistics.csv",
    "primary": "artifacts/rp4_v4_b2_rv15/session_losses.csv",
    "final": "artifacts/rp4_v4_b3_rv15/session_losses.csv",
    "pit60": "artifacts/rp4_robustness_public_v1/pit_60_session_losses.csv",
    "pit300": "artifacts/rp4_robustness_public_v1/pit_300_session_losses.csv",
    "placebo": "artifacts/rp4_robustness_public_v1/placebo_log_ridge_harq_rv15_summary.csv",
}


def load_evidence():
    """An explicit allowlist prevents discovery of private or sealed input paths."""
    tables = {}
    for key, name in PATHS.items():
        with (ROOT / name).open(encoding="utf-8", newline="") as stream:
            tables[key] = json.load(stream) if key == "spec" else list(csv.DictReader(stream))
    spec, stats = tables["spec"], tables["stats"]
    primary = [r for r in stats if r["horizon_minutes"] == "15" and r["window"] == "primary"]
    assert len(primary) == 4
    by_model = {(r["family"], r["contrast"]): r for r in primary}
    for row in primary:
        estimate, low, high = (float(row[key]) for key in ("estimate", "ci_low", "ci_high"))
        assert all(math.isfinite(v) for v in (estimate, low, high)) and low <= estimate <= high
    dates, series = curves()
    assert spec["source_cutoff_seconds"] == 120
    assert [len(spec["feature_sets"][s]) for s in ("B0", "B1", "B2")] == [29, 69, 138]

    def reduction(rows, prefix="loss__log_ridge_harq__"):
        baseline = sum(float(r[f"{prefix}B1"]) for r in rows)
        delta = sum(float(r[f"{prefix}B1"]) - float(r[f"{prefix}B2"]) for r in rows)
        assert baseline > 0 and math.isfinite(delta)
        return 100 * delta / baseline

    final = [r for r in stats if r["horizon_minutes"] == "15" and r["window"] == "confirmation"]
    h1 = [r for r in final if r["contrast"] == "B1_over_B0"]
    assert len(h1) == 2 and all(r["rejected"].lower() == "false" for r in h1)
    final_linear = next(
        r for r in final if r["family"] == FAMILIES[0] and r["contrast"] == "B2_over_B1"
    )
    placebo = tables["placebo"][0]
    values = {
        "cutoff": spec["source_cutoff_seconds"],
        "b0": 29,
        "b1": 69,
        "b2": 138,
        "sessions": len(dates),
        "origins": f"{int(primary[0]['N_origins']):,}",
        "linear": f"{float(by_model[FAMILIES[0], 'B2_over_B1']['percent_reduction_mean']):.3f}",
        "trees": f"{float(by_model[FAMILIES[1], 'B2_over_B1']['percent_reduction_mean']):.3f}",
        "final_sessions": len(tables["final"]),
        "final_p": f"{float(final_linear['p_raw']):.4f}",
        "pit60": f"{reduction(tables['pit60'], ''):.3f}",
        "pit300": f"{reduction(tables['pit300'], ''):.3f}",
        "retained": f"{100 * float(placebo['mean']) / float(placebo['observed_delta']):.2f}",
    }
    assert math.isclose(reduction(tables["primary"]), float(values["linear"]), abs_tol=0.0005)
    board = json.loads((HERE / "storyboard.json").read_text(encoding="utf-8"))
    assert len(board["chapters"]) == 8 and sum(c["seconds"] for c in board["chapters"]) == 90
    for chapter in board["chapters"]:
        chapter["captions"] = [caption.format(**values) for caption in chapter["captions"]]
    return board, values, by_model, dates, series


def stamp(seconds):
    millis = round(seconds * 1000)
    return (
        f"{millis // 3600000:02}:{millis // 60000 % 60:02}:"
        f"{millis // 1000 % 60:02},{millis % 1000:03}"
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--frames-only", action="store_true")
    parser.add_argument("--font", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--background", type=Path, help="Optional still PNG; decorative only")
    parser.add_argument(
        "--title", type=Path, help="Optional title PNG shown for the first 2.5 seconds"
    )
    args = parser.parse_args()
    board, values, results, dates, series = load_evidence()
    if args.check:
        print(
            json.dumps(
                {
                    "chapters": 8,
                    "seconds": 90,
                    "values": values,
                    "endpoints": [s[-1] for s in series],
                }
            )
        )
        return
    if not args.font or not args.output_dir:
        parser.error("--font and --output-dir are required")
    if args.output_dir.exists():
        parser.error("Output directory exists; use a new exact path")
    from PIL import Image, ImageDraw, ImageFont

    fonts = {n: ImageFont.truetype(str(args.font), n) for n in (24, 32, 36, 40, 48, 56, 72)}
    background = Image.new("RGB", (W, H), NAVY)
    if args.background:
        background = (
            Image.open(args.background).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
        )
        background = Image.blend(background, Image.new("RGB", (W, H), NAVY), 0.82)
    title_card = None
    if args.title:
        title_card = Image.open(args.title).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    args.output_dir.mkdir(parents=True)

    def frame(chapter_index, local):
        if chapter_index == 0 and local < 2.5 and title_card is not None:
            return title_card.copy()
        chapter = board["chapters"][chapter_index]
        beat = min(2, int(local / chapter["seconds"] * 3))
        im = background.copy()
        d = ImageDraw.Draw(im)

        def text(x, y, content, size=36, color=WHITE):
            assert not re.search(r"\.(?:py|csv|md|json)\b", content), content
            assert d.textbbox((x, y), content, font=fonts[size])[2] <= W - 38, content
            d.text((x, y), content, font=fonts[size], fill=color)

        def wrap(x, y, content, width, size=36, color=WHITE):
            line = ""
            for word in content.split():
                proposed = f"{line} {word}".strip()
                if d.textlength(proposed, font=fonts[size]) > width:
                    text(x, y, line, size, color)
                    y += size + 9
                    line = word
                else:
                    line = proposed
            text(x, y, line, size, color)
            return y + size

        def box(x, y, w, h, title, detail="", color=CYAN):
            d.rounded_rectangle((x, y, x + w, y + h), radius=16, fill=PANEL, outline=color, width=3)
            text(x + 22, y + 18, title, 40, color)
            if detail:
                bottom = wrap(x + 22, y + 77, detail, w - 44, 32)
                assert bottom <= y + h - 8, (title, bottom)

        def arrow(x1, y1, x2, y2, color=CYAN):
            d.line((x1, y1, x2, y2), fill=color, width=4)
            angle = math.atan2(y2 - y1, x2 - x1)
            d.polygon(
                [(x2, y2)]
                + [
                    (x2 - 15 * math.cos(angle + a), y2 - 15 * math.sin(angle + a))
                    for a in (-0.5, 0.5)
                ],
                fill=color,
            )
            phase = local * 0.4 % 1
            xx, yy = x1 + (x2 - x1) * phase, y1 + (y2 - y1) * phase
            d.ellipse((xx - 6, yy - 6, xx + 6, yy + 6), fill=color)

        text(60, 28, "OPTIONS ORDER FLOW / A RESEARCH WALKTHROUGH", 24, MUTED)
        text(60, 78, chapter["title"], 56)
        text(1390, 35, f"{chapter_index + 1} / 8", 32, CYAN)
        d.line((60, 165, 1540, 165), fill="#365567", width=2)
        if chapter_index == 0:
            box(100, 225, 1400, 150, "How much movement?", "15-minute realized variance", CYAN)
            box(100, 425, 640, 160, "Not price direction", "Not a buy / sell signal", MUTED)
            box(800, 425, 700, 160, "The comparison", "History → option state → mixed B2", GOLD)
        elif chapter_index == 1:
            for k, ticker in enumerate(("AAPL", "AMZN", "META", "MSFT", "NVDA", "TSLA")):
                box(75 + 250 * k, 205, 220, 90, ticker)
            box(75, 335, 610, 200, "Stock bars / FMP", "Price and volatility history", CYAN)
            box(
                760,
                335,
                760,
                200,
                "Options / Unusual Whales",
                "Underlying · call / put · strike · expiry",
                GOLD,
            )
            text(85, 600, "SPY / QQQ: market context + separate ETF extension", 36, MUTED)
        elif chapter_index == 2:
            text(90, 230, "ELIGIBLE OPTION RECORDS", 36, CYAN)
            text(1000, 230, "FUTURE TARGET", 36, GOLD)
            d.line((90, 390, 1500, 390), fill=MUTED, width=4)
            for x, label in ((550, "t − 120 seconds"), (910, "t"), (1400, "t + 15 min")):
                d.line((x, 350, x, 430), fill=WHITE, width=3)
                text(x - (140 if x != 910 else 8), 445, label, 36)
            arrow(100, 325, 545, 325)
            arrow(920, 325, 1400, 325, GOLD)
            box(95, 535, 650, 130, "Source-time assumption", "Not measured client receipt", CYAN)
            box(
                835,
                535,
                650,
                130,
                "Score only after the origin",
                "Future data stay out of predictors",
                GOLD,
            )
        elif chapter_index == 3:
            box(70, 205, 680, 455, "B2 / 138 total", "B1 + mixed information", GOLD)
            box(95, 345, 630, 290, "B1 / 69 total", "B0 + option state", CYAN)
            box(120, 485, 580, 125, "B0 / 29 total", "Price history", MUTED)
            text(780, 245, "All three sets", 32)
            arrow(765, 375, 910, 375, MUTED)
            d.line((910, 320, 910, 530), fill=MUTED, width=3)
            arrow(910, 320, 980, 320)
            arrow(910, 530, 980, 530, GOLD)
            box(995, 225, 520, 170, "Linear", "Log-ridge HARQ", CYAN)
            box(995, 450, 520, 170, "Trees", "LightGBM / QLIKE", GOLD)
        elif chapter_index == 4:
            text(90, 210, "PAST → EXPANDING TRAINING → NEXT SESSION", 36, CYAN)
            text(620, 248, "Next evaluation", 32, GOLD)
            for row in range(3):
                y = 290 + 100 * row
                d.rounded_rectangle((100, y, 600 + row * 140, y + 62), radius=8, fill="#18516a")
                d.rounded_rectangle(
                    (620 + row * 140, y, 740 + row * 140, y + 62),
                    radius=8,
                    fill=GOLD if row == beat else "#69573a",
                )
                text(120, y + 7, "Training", 32)
            text(1110, 305, "Same origins", 36)
            text(1110, 370, "Paired losses", 36)
            text(
                100,
                610,
                f"{values['origins']} origins → asset-session means → "
                f"{values['sessions']} sessions",
                36,
                WHITE,
            )
        elif chapter_index == 5:
            text(80, 205, "HISTORICAL RV15 / PAIRED FORECAST LOSSES", 36, CYAN)
            text(520, 260, "Difference + 95% interval", 32)
            text(1230, 260, "Loss reduction", 32)

            # One shared QLIKE axis; percentages use their own baseline losses.
            def plot_x(value):
                return 540 + 660 * (value + 0.003) / 0.008

            for tick in (-0.002, 0, 0.002, 0.004):
                xx = plot_x(tick)
                d.line((xx, 310, xx, 603), fill=MUTED if tick == 0 else "#294354", width=2)
                text(xx - 45, 612, f"{tick:.3f}", 32, MUTED)
            labels = ("Linear / state", "Linear / mixed B2", "Trees / state", "Trees / mixed B2")
            for j, (family, contrast) in enumerate(
                (f, c) for f in FAMILIES for c in ("B1_over_B0", "B2_over_B1")
            ):
                if beat == 0 and contrast == "B2_over_B1":
                    continue
                row, y = results[family, contrast], 338 + 80 * j
                color = CYAN if family == FAMILIES[0] else GOLD
                text(80, y - 19, labels[j], 36, color)
                low, mid, high = (plot_x(float(row[k])) for k in ("ci_low", "estimate", "ci_high"))
                d.line((low, y, high, y), fill=color, width=5)
                for xx in (low, high):
                    d.line((xx, y - 10, xx, y + 10), fill=color, width=3)
                d.ellipse((mid - 9, y - 9, mid + 9, y + 9), fill=color)
                percent = float(row["percent_reduction_mean"])
                text(1270, y - 23, f"{percent:+.3f}%", 40, color)
            text(520, 660, "QLIKE units · positive favors the added block", 32, MUTED)
        elif chapter_index == 6:
            if beat == 0:
                box(
                    85,
                    225,
                    1430,
                    180,
                    f"Final {values['final_sessions']} sessions: no confirmation",
                    f"Linear H2 nominal p = {values['final_p']}; the first step did not pass.",
                    GOLD,
                )
                wrap(
                    95,
                    485,
                    "A short inconclusive window does not establish a zero effect"
                    "—or validate the historical gain.",
                    1400,
                    40,
                )
            elif beat == 1:
                for i, (label, number) in enumerate(
                    (
                        ("60 seconds", values["pit60"]),
                        ("120 seconds", values["linear"]),
                        ("300 seconds", values["pit300"]),
                    )
                ):
                    box(
                        85 + i * 490,
                        250,
                        450,
                        225,
                        label,
                        f"Linear B2: +{number}%",
                        CYAN if i == 1 else MUTED,
                    )
                text(95, 555, "Sensitivity to assumptions—not measured delivery latency.", 36, GOLD)
            else:
                box(
                    85,
                    225,
                    1430,
                    180,
                    f"Shuffled control: {values['retained']}% of mean gain remains",
                    "The precisely timed flow contribution is not isolated.",
                    GOLD,
                )
                text(95, 505, "Whole-session shuffling is a control, not a real-time strategy.", 36)
                text(95, 580, "Broad component ablations remain an open question.", 36, MUTED)
        else:
            if beat == 0:
                for i, (title, detail) in enumerate(
                    (
                        ("Read", "Research question + methodology"),
                        ("Trace", "Claims linked to saved evidence"),
                        ("Inspect", "Public tables + published figures"),
                    )
                ):
                    box(75 + i * 510, 265, 480, 215, title, detail, CYAN if i == beat else MUTED)
                text(90, 570, "Follow a claim to its source, not just its headline.", 40)
            elif beat == 1:
                text(80, 215, "Follow the public reproduction guide", 40, CYAN)
                for i, (title, detail) in enumerate(
                    (
                        ("Get the project", "Clone the public repository"),
                        ("Prepare", "Install the locked environment"),
                        ("Recreate", "Regenerate published figures"),
                    )
                ):
                    box(75 + i * 510, 325, 480, 225, title, detail, CYAN)
            else:
                box(
                    80,
                    235,
                    1440,
                    180,
                    "Then run public verification",
                    "Check released evidence using the reproduction guide",
                    CYAN,
                )
                wrap(
                    95,
                    495,
                    "Public checks inspect the released evidence. "
                    "A full raw-data rebuild requires licensed inputs.",
                    1400,
                    40,
                )
        d.rounded_rectangle((50, 718, 1550, 833), radius=12, fill="#071725")
        bottom = wrap(78, 732, chapter["captions"][beat], 1445, 36)
        assert bottom <= 823, (chapter_index, beat, bottom)
        text(
            60,
            853,
            "Historical research · source-time assumptions · no causal or trading claim",
            24,
            MUTED,
        )
        start = sum(c["seconds"] for c in board["chapters"][:chapter_index])
        d.rectangle((60, 701, 60 + 1480 * (start + local) / 90, 705), fill=CYAN)
        return im

    subtitles, cue, elapsed, samples = [], 1, 0, []
    for index, chapter in enumerate(board["chapters"]):
        for beat, caption in enumerate(chapter["captions"]):
            begin = elapsed + chapter["seconds"] * beat / 3
            end = elapsed + chapter["seconds"] * (beat + 1) / 3
            subtitles.append(f"{cue}\n{stamp(begin)} --> {stamp(end)}\n{caption}\n")
            cue += 1
            im = frame(index, chapter["seconds"] * (beat + 0.5) / 3)
            im.save(args.output_dir / f"chapter-{index + 1:02}-beat-{beat + 1}.png")
            if beat == 1:
                samples.append(im.resize((800, 450), Image.Resampling.LANCZOS))
        elapsed += chapter["seconds"]
    contact = Image.new("RGB", (1600, 1800), NAVY)
    for i, sample in enumerate(samples):
        contact.paste(sample, ((i % 2) * 800, (i // 2) * 450))
    contact.save(args.output_dir / "contact-sheet.png")
    (args.output_dir / "walkthrough.srt").write_bytes(("\n".join(subtitles) + "\n").encode())
    if not args.frames_only:
        target = args.output_dir / "walkthrough.mp4"
        command = [
            "ffmpeg",
            "-v",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{W}x{H}",
            "-r",
            str(FPS),
            "-i",
            "pipe:0",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(target),
        ]
        process = subprocess.Popen(command, stdin=subprocess.PIPE)
        assert process.stdin is not None
        try:
            for i, chapter in enumerate(board["chapters"]):
                for k in range(chapter["seconds"] * FPS):
                    process.stdin.write(frame(i, k / FPS).tobytes())
            process.stdin.close()
            if process.wait():
                raise RuntimeError("VIDEO_ENCODING_FAILED")
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait()
    receipt = {
        "sources": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in PATHS.values()},
        "seconds": 90,
        "fps": FPS,
        "chapters": 8,
        "values": values,
        "private_reads": 0,
        "new_model_fits": 0,
        "mode": "frames_only" if args.frames_only else "video",
        "storyboard_sha256": hashlib.sha256((HERE / "storyboard.json").read_bytes()).hexdigest(),
        "renderer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "font_sha256": hashlib.sha256(args.font.read_bytes()).hexdigest(),
    }
    if not args.frames_only:
        receipt["video_sha256"] = hashlib.sha256(target.read_bytes()).hexdigest()
    if args.title:
        receipt["title_sha256"] = hashlib.sha256(args.title.read_bytes()).hexdigest()
    (args.output_dir / "receipt.json").write_bytes((json.dumps(receipt, indent=2) + "\n").encode())
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
