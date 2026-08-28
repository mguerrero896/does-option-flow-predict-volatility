"""Freeze the RP3 program's two forecasters: one command, one manifest, verified bytes.

Runs `mds650.rp3.frozen_forecasters.freeze` against the remeasured panels, which trains
the B1 and B1-plus-index LightGBM models on every pre-window row (sessions through
2026-07-17), serializes both boosters and both preprocessors, verifies the frozen index
reproduces the theta artifact's recorded statistics, and round-trips its own output from
disk before declaring success. The manifest this writes is what the preregistration's
"Phase B freeze manifest" clause refers to.

    uv run python scripts/rp3_freeze_forecasters.py --panel-root <run-dir>
"""

from __future__ import annotations

import argparse
from pathlib import Path

from mds650.rp3.frozen_forecasters import freeze

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PANEL_ROOT = ROOT / "artifacts" / "rp2_v3" / "rp2-v3-20260824-remeasure"
DEFAULT_THETA = ROOT / "artifacts" / "rp3" / "b2_index_theta.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "rp3" / "frozen"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-root", type=Path, default=DEFAULT_PANEL_ROOT)
    parser.add_argument("--theta", type=Path, default=DEFAULT_THETA)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()

    manifest = freeze(arguments.panel_root, arguments.theta, arguments.output_dir)
    models = manifest["models"]
    assert isinstance(models, dict)
    print(f"frozen: {arguments.output_dir}")
    print(
        f"  training: {manifest['training_rows']} rows, "
        f"{manifest['training_sessions']} sessions, latest "
        f"{manifest['latest_training_session']} (window end "
        f"{manifest['training_window_end']})"
    )
    for name, record in models.items():
        assert isinstance(record, dict)
        fit = record.get("fit_record", {})
        rounds = fit.get("boosting_rounds") if isinstance(fit, dict) else None
        print(f"  {name}: {record['file']} sha256={str(record['sha256'])[:16]}… rounds={rounds}")
    print(f"  manifest self_sha256={manifest['self_sha256']}")


if __name__ == "__main__":
    main()
