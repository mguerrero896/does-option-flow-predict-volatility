"""Render a public-data explainer; never loads granular observations or fits a model.

Requires Pillow and ffmpeg. Font paths and generated media are explicit inputs.
Use --check to validate the saved public curve without media dependencies.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "artifacts/rp4_v4_b2_rv15/session_losses.csv"
W, H, FPS, SECONDS = 1600, 900, 24, 30
CYAN, GOLD, WHITE, MUTED = "#87d9e4", "#edbd63", "#f2f5f7", "#a0b6c6"
FAMILIES = ("log_ridge_harq", "lightgbm_qlike")


def curves() -> tuple[list[str], list[list[float]]]:
    with SOURCE.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    dates = [row["session_date"] for row in rows]
    assert len(dates) == len(set(dates)) == 419 and dates == sorted(dates)
    series = []
    for family in FAMILIES:
        total = 0.0
        values = []
        for row in rows:
            total += float(row[f"loss__{family}__B1"]) - float(row[f"loss__{family}__B2"])
            assert math.isfinite(total)
            values.append(total)
        series.append(values)
    assert math.isclose(series[0][-1], 0.475045297159697, abs_tol=1e-12)
    assert math.isclose(series[1][-1], -0.0892063870704825, abs_tol=1e-12)
    return dates, series


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--background", type=Path)
    parser.add_argument("--title", type=Path)
    parser.add_argument("--font", type=Path)
    parser.add_argument("--serif-font", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    dates, series = curves()
    if args.check:
        print(json.dumps({"sessions": len(dates), "endpoints": [s[-1] for s in series]}))
        return
    for name in ("background", "title", "font", "serif_font", "output"):
        if getattr(args, name) is None:
            parser.error(f"--{name.replace('_', '-')} is required for rendering")
    if args.output.exists():
        parser.error("Output exists; choose a new path to preserve reviewed media")
    from PIL import Image, ImageDraw, ImageFont

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fonts = {size: ImageFont.truetype(str(args.font), size) for size in (18, 21, 24, 28, 32, 40)}
    serif = ImageFont.truetype(str(args.serif_font), 52)
    title = Image.open(args.title).convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    decoder = subprocess.Popen(
        [
            "ffmpeg",
            "-v",
            "error",
            "-stream_loop",
            "-1",
            "-i",
            str(args.background),
            "-vf",
            f"scale={W}:{H},fps={FPS}",
            "-t",
            str(SECONDS),
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "pipe:1",
        ],
        stdout=subprocess.PIPE,
    )
    encoder = subprocess.Popen(
        [
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
            "-crf",
            "20",
            "-preset",
            "medium",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(args.output),
        ],
        stdin=subprocess.PIPE,
    )
    assert decoder.stdout is not None and encoder.stdin is not None
    try:
        for index in range(SECONDS * FPS):
            raw = decoder.stdout.read(W * H * 3)
            if len(raw) != W * H * 3:
                raise RuntimeError("BACKGROUND_DECODE_INCOMPLETE")
            t = index / FPS
            frame = Image.frombytes("RGB", (W, H), raw)
            # Generated particles are decoration, not observations or a volatility surface.
            frame = Image.blend(frame, Image.new("RGB", (W, H), "#04101d"), 0.30)
            if t < 3:
                frame = title.copy()
            else:
                draw = ImageDraw.Draw(frame)

                def text(x, y, value, size=24, color=WHITE, draw=draw):
                    draw.text((x, y), value, font=fonts[size], fill=color)

                def box(x, y, width, height, lines, color=CYAN, draw=draw, text=text):
                    draw.rounded_rectangle(
                        (x, y, x + width, y + height),
                        radius=14,
                        fill="#081c2c",
                        outline=color,
                        width=2,
                    )
                    for j, value in enumerate(lines):
                        text(x + 20, y + 17 + j * 34, value, 24 if j else 28, MUTED if j else WHITE)

                def arrow(x1, y1, x2, y2, color=CYAN, speed=0.35, draw=draw, t=t):
                    draw.line((x1, y1, x2, y2), fill=color, width=2)
                    angle = math.atan2(y2 - y1, x2 - x1)
                    points = [(x2, y2)] + [
                        (x2 - 12 * math.cos(angle + a), y2 - 12 * math.sin(angle + a))
                        for a in (-0.45, 0.45)
                    ]
                    draw.polygon(points, fill=color)
                    p = (t * speed) % 1
                    x, y = x1 + (x2 - x1) * p, y1 + (y2 - y1) * p
                    draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=color)

                draw.text(
                    (65, 30), "Options Order Flow & Intraday Volatility", font=serif, fill=WHITE
                )
                text(68, 101, "AAPL · AMZN · META · MSFT · NVDA · TSLA", 24, CYAN)
                text(68, 141, "SPY / QQQ: market context and separate ETF extension", 21, MUTED)
                draw.line((65, 187, 1535, 187), fill="#365567", width=1)
                if t < 9:
                    text(65, 216, "01  /  RECORDS → AVAILABLE INFORMATION", 32, CYAN)
                    box(70, 310, 360, 155, ["Stock bars", "Price history", "FMP"], CYAN)
                    box(
                        70,
                        500,
                        360,
                        195,
                        [
                            "Options records",
                            "Underlying · call / put",
                            "Strike · expiry",
                            "Unusual Whales",
                        ],
                        GOLD,
                    )
                    arrow(440, 390, 655, 390)
                    arrow(440, 595, 655, 500, GOLD)
                    box(
                        665,
                        345,
                        730,
                        220,
                        [
                            "Forecast origin: t",
                            "Options source time ≤ t − 120 seconds",
                            "Exclude later source records",
                            "An availability assumption, not measured receipt",
                        ],
                        CYAN,
                    )
                    text(670, 616, "Align records by asset and source timestamp.", 24, MUTED)
                    text(
                        670,
                        656,
                        "Quote state + recent activity → predictor construction",
                        21,
                        MUTED,
                    )
                elif t < 18:
                    text(65, 216, "02  /  NESTED INFORMATION → TWO MODEL FAMILIES", 32, CYAN)
                    # Nested boxes encode inclusion; they are not successive neural layers.
                    box(70, 305, 640, 410, ["B2  ·  138 predictors", "B1 + mixed block"], GOLD)
                    box(95, 400, 590, 285, ["B1  ·  69 predictors", "B0 + option state"], CYAN)
                    box(120, 505, 540, 140, ["B0  ·  29 predictors", "Stock-price history"], MUTED)
                    text(
                        80,
                        748,
                        "Added B2: activity · price changes · exposure proxies · coverage",
                        21,
                        GOLD,
                    )
                    text(742, 435, "B0 / B1 / B2", 21, WHITE)
                    arrow(720, 480, 850, 480, MUTED)
                    draw.line((850, 390, 850, 560), fill=MUTED, width=2)
                    arrow(850, 390, 955, 390, CYAN)
                    arrow(850, 560, 955, 560, GOLD)
                    box(970, 330, 490, 120, ["Linear", "Log-ridge HARQ"], CYAN)
                    box(970, 500, 490, 120, ["Trees", "LightGBM · QLIKE objective"], GOLD)
                    text(970, 660, "Each family fits B0, B1 and B2.", 24)
                    text(970, 702, "Chronological expanding-window fitting", 21, MUTED)
                else:
                    text(65, 216, "03  /  FORECAST → OBSERVE → COMPARE", 32, CYAN)
                    box(70, 295, 385, 115, ["Forecast at t", "Next 15-minute variance"], CYAN)
                    arrow(462, 351, 565, 351)
                    box(575, 295, 430, 115, ["Observe after t", "Realized variance → QLIKE"], GOLD)
                    text(1040, 308, "Future observations score forecasts.", 21)
                    text(1040, 347, "They do not enter the predictors.", 21, MUTED)
                    x0, y0, x1, y1 = 125, 495, 980, 737
                    lo = min(min(s) for s in series)
                    hi = max(max(s) for s in series)

                    def position(k, value, bounds=(x0, y0, x1, y1, lo, hi)):
                        x0, y0, x1, y1, lo, hi = bounds
                        return (x0 + (x1 - x0) * k / 418, y1 - (y1 - y0) * (value - lo) / (hi - lo))

                    text(80, 446, "Cumulative QLIKE difference: B1 − B2", 24)
                    for value in (-0.1, 0.0, 0.25):
                        yy = position(0, value)[1]
                        text(65, yy - 10, f"{value:.2f}", 18, MUTED)
                    draw.line((x0, position(0, 0)[1], x1, position(0, 0)[1]), fill="#607584")
                    n = min(419, max(2, int((t - 18) / 8 * 419)))
                    for s, color in zip(series, (CYAN, GOLD), strict=True):
                        draw.line(
                            [position(k, value) for k, value in enumerate(s[:n])],
                            fill=color,
                            width=3,
                        )
                    text(x0, 760, dates[0], 18, MUTED)
                    text(x1 - 105, 760, dates[-1], 18, MUTED)
                    text(1040, 480, "419 historical sessions", 28)
                    text(1040, 536, "Linear  +0.623%", 32, CYAN)
                    text(1040, 581, "Trees   −0.115%", 32, GOLD)
                    text(1040, 636, "Mean loss reduction, not returns", 21, MUTED)
                    text(1040, 690, "Final 25-session window:", 21)
                    text(1040, 726, "no confirmation", 24, MUTED)
                text(
                    68,
                    842,
                    "Historical evidence under source-time assumptions"
                    " · no causal or trading claim",
                    18,
                    MUTED,
                )
                draw.rectangle((65, 819, 65 + 1470 * (t / SECONDS), 822), fill=CYAN)
            if index in (24, 6 * FPS, 13 * FPS, 27 * FPS):
                frame.save(args.output.parent / f"frame-{index // FPS:02d}.png")
            encoder.stdin.write(frame.tobytes())
        encoder.stdin.close()
        if encoder.wait() or decoder.wait():
            raise RuntimeError("VIDEO_ENCODER_OR_DECODER_FAILED")
    finally:
        for process in (decoder, encoder):
            if process.poll() is None:
                process.terminate()
                process.wait()
    receipt = {
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "sessions": len(dates),
        "cumulative_endpoints": [s[-1] for s in series],
        "method": "Chronological cumulative sum of session mean loss B1 minus B2",
        "new_model_fits": 0,
        "private_data_reads": 0,
        "duration_seconds": SECONDS,
        "fps": FPS,
        "fonts": [args.font.name, args.serif_font.name],
        "title_sha256": hashlib.sha256(args.title.read_bytes()).hexdigest(),
        "background_sha256": hashlib.sha256(args.background.read_bytes()).hexdigest(),
        "video_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
    }
    args.output.with_suffix(".json").write_bytes((json.dumps(receipt, indent=2) + "\n").encode())


if __name__ == "__main__":
    main()
