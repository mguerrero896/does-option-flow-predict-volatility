"""The motion graphic must use the complete saved historical curve."""

import hashlib
import json
import runpy
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
        ("background_sha256", "background.mp4"),
    ):
        assert hashlib.sha256((folder / filename).read_bytes()).hexdigest() == receipt[key]
    assert (
        hashlib.sha256((root / receipt["source"]).read_bytes()).hexdigest()
        == receipt["source_sha256"]
    )
    # Reviewed title, all three stages, exact curves and finite-play preview.
    assert hashlib.sha256((folder / "preview.gif").read_bytes()).hexdigest() == (
        "a9256f283c11bca6961e7a58da8c390ce794c77f5a1561068add8a228a709199"
    )
