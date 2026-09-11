"""The motion graphic must use the complete saved historical curve."""

import hashlib
import json
import runpy
import subprocess
import sys
from pathlib import Path


def test_research_motion_saved_curve() -> None:
    root = Path(__file__).resolve().parents[2]
    module = runpy.run_path(str(root / "docs/figures/research_motion/render.py"))
    dates, series = module["curves"]()
    assert (dates[0], dates[-1]) == ("2024-10-28", "2026-07-31")
    assert all(len(values) == len(dates) == 419 for values in series)
    assert series[0][-1] > 0 > series[1][-1]


def test_reviewed_research_motion_identity() -> None:
    root = Path(__file__).resolve().parents[2]
    folder = root / "docs/figures/research_motion"
    receipt = json.loads((folder / "overview.json").read_text())
    for key, filename in (
        ("video_sha256", "overview.mp4"),
        ("title_sha256", "title.png"),
        ("preview_sha256", "preview.gif"),
        ("subtitles_sha256", "overview.srt"),
        ("renderer_sha256", "render_walkthrough.py"),
        ("storyboard_sha256", "storyboard.json"),
    ):
        assert hashlib.sha256((folder / filename).read_bytes()).hexdigest() == receipt[key]
    for source, digest in receipt["sources"].items():
        assert hashlib.sha256((root / source).read_bytes()).hexdigest() == digest
    assert receipt["seconds"] == 90 and receipt["chapters"] == 8
    assert receipt["private_reads"] == receipt["new_model_fits"] == 0
    checked = subprocess.run(
        [sys.executable, str(folder / "render_walkthrough.py"), "--check"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(checked.stdout)["values"] == receipt["values"]
    subtitles = (folder / "overview.srt").read_text(encoding="utf-8")
    assert subtitles.count(" --> ") == 24
    assert "00:01:30,000" in subtitles
    assert all(suffix not in subtitles for suffix in (".csv", ".py", ".md"))
