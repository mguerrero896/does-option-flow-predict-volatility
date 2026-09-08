"""Report figure translations change text while preserving every plotted coordinate."""

from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_translated_report_figures_preserve_all_plot_geometry() -> None:
    originals = json.loads(
        (ROOT / "docs/archive/rp4/presentation_originals/original_paths.json").read_bytes()
    )
    for version in ("v3", "v4"):
        for contrast in ("B1_over_B0", "B2_over_B1"):
            logical = f"artifacts/rp4_{version}_b4/{contrast}.svg"
            entry = originals[logical]
            old_bytes = (ROOT / entry["archive_path"]).read_bytes()
            assert hashlib.sha256(old_bytes).hexdigest() == entry["sha256"]
            old = ET.fromstring(old_bytes)
            new = ET.fromstring((ROOT / logical).read_bytes())
            assert [(e.tag, e.attrib) for e in old.iter()] == [
                (e.tag, e.attrib) for e in new.iter()
            ], logical
            assert "independent scales" in " ".join(new.itertext())
