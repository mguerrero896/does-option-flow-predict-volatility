"""Small deterministic checks for RP4 report signs, endpoints and input consistency."""

import json
from argparse import Namespace
from pathlib import Path
from xml.etree import ElementTree

import pytest
import report as report_module
from evaluate import CONTRASTS, FAMILIES
from report import cumulative_figure, load_window, render_report, run


def test_report_retains_adverse_sign_and_verifies_curve(tmp_path: Path) -> None:
    rows = []
    for date in ("2026-08-03", "2026-08-04"):
        row = {"session_date": date}
        for family in FAMILIES:
            row.update(
                {
                    f"loss__{family}__B0": "1",
                    f"loss__{family}__B1": "1.2",
                    f"loss__{family}__B2": "1.1",
                }
            )
        rows.append(row)
    summary = {
        "binding": {"specification_sha256": "test"},
        "N_sessions": 2,
        "N_origins": 4,
        "contrasts": [
            {
                "family": family,
                "contrast": contrast,
                "estimate": value,
                "N_sessions": 2,
                "N_origins": 4,
                "status": "NO VERIFICABLE",
                "reason": "synthetic small sample",
            }
            for family in FAMILIES
            for (contrast, _, _), value in zip(CONTRASTS, (-0.2, 0.1), strict=True)
        ],
    }
    (tmp_path / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    columns = list(rows[0])
    (tmp_path / "session_losses.csv").write_text(
        ",".join(columns) + "\n" + "\n".join(",".join(row[col] for col in columns) for row in rows),
        encoding="utf-8",
    )
    loaded = load_window(tmp_path, "test")
    windows = {"primary": loaded, "confirmation": loaded}
    svg = ElementTree.fromstring(cumulative_figure(windows, *CONTRASTS[0]))
    curves = [node for node in svg.iter() if "data-endpoint" in node.attrib]
    assert len(curves) == 4
    assert all(float(node.attrib["data-endpoint"]) == pytest.approx(-0.4) for node in curves)
    report = render_report(windows, "fixed label", "## Audit\n\nSynthetic fixture.")
    assert "-0.2" in report and "+0.1" in report
    assert "NO VERIFICABLE" in report and "capital_go=false" in report
    summary["contrasts"][0]["estimate"] = 0.2
    (tmp_path / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    with pytest.raises(ValueError, match="ESTIMATE_DOES_NOT_MATCH"):
        load_window(tmp_path, "test")


def test_report_checks_development_prefix_and_writes_once(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(report_module, "load_spec", lambda *_: {"label": "fixed label"})
    spec = tmp_path / "spec.json"
    spec.write_text("{}", encoding="utf-8")
    audit = tmp_path / "audit.md"
    audit.write_text("## Audit\n\nSynthetic only.", encoding="utf-8")
    for window, digest in (("primary", "development"), ("confirmation", "combined")):
        directory = tmp_path / window
        directory.mkdir()
        summary = {
            "binding": {
                "specification_sha256": "test",
                "panel_sha256": digest,
                "evaluator_sha256": "same-code",
                "imports_sha256": {},
            },
            "N_sessions": 0,
            "contrasts": [],
            "window": window,
            "result_label": "fixed label",
            "reason": "synthetic no sessions",
        }
        (directory / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
        (directory / "session_losses.csv").write_text("\n", encoding="utf-8")
    lineage_path = tmp_path / "lineage.json"
    lineage = {
        "development_panel_sha256": "development",
        "combined_panel_sha256": "combined",
        "spec_sha256": "test",
        "development_prefix_equal_by_keys": False,
    }
    lineage_path.write_text(json.dumps(lineage), encoding="utf-8")
    args = Namespace(
        spec=spec,
        spec_sha256="test",
        primary=tmp_path / "primary",
        confirmation=tmp_path / "confirmation",
        panel_lineage=lineage_path,
        audit=audit,
        output=tmp_path / "report.md",
        figures=tmp_path / "figures",
    )
    with pytest.raises(ValueError, match="PREFIX_PROOF_MISMATCH"):
        run(args)
    assert not args.output.exists()
    lineage["development_prefix_equal_by_keys"] = True
    lineage_path.write_text(json.dumps(lineage), encoding="utf-8")
    run(args)
    original = args.output.read_bytes()
    run(args)
    assert args.output.read_bytes() == original
    manifest = json.loads((args.figures / "report_manifest.json").read_text())
    assert manifest["models_fitted"] == 0 and not manifest["raw_or_origin_data_read"]
