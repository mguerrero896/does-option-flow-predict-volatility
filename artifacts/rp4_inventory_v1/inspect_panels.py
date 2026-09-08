"""Verify four RP4 input pointers using hashes and Parquet footers, never data rows.

Run with --write once to create inventory.json and COLUMNS.md; otherwise compare
the current metadata snapshot against those files without overwriting anything.
This is an inventory check, not A1, feature construction or model evaluation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from mds650.har import HAR_COLUMNS, HARQ_COLUMN
from mds650.rp2.feature_registry import registry, registry_sha256
from mds650.rp2.run_manifest import canonical_json

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RUN = Path("private-input/cae7797a616552255aa6")
STEPS = {"B0": "build-b0", "B1": "build-b1", "B2": "build-b2", "target": "build-targets"}
KEYS = {"asset", "session_date", "origin_minute"}
B1_CUSTODY = {
    "b1_quote_duplicates_dropped", "b1_post_cutoff_selected", "b1_duplicate_contracts_remaining",
}
B2_CUSTODY = {"b2_pit_violations", "b2_counting_mean_latency_s", "b2_counting_p95_latency_s"}


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def snapshot() -> dict[str, Any]:
    identity = json.loads((RUN / "run_identity.json").read_text(encoding="utf-8"))
    inputs = json.loads((RUN / "input_manifest.json").read_text(encoding="utf-8"))
    assert inputs["source_lineage_mode"] == "registered_panel_reuse", "INPUT_LINEAGE_CHANGED"
    identifying = {
        **inputs,
        "source_registered_run": {
            key: value for key, value in inputs["source_registered_run"].items()
            if key != "run_id"
        },
    }
    manifest_digest = hashlib.sha256(canonical_json(identifying).encode("utf-8")).hexdigest()
    assert manifest_digest == identity["input_manifest_sha256"], "INPUT_MANIFEST_DRIFT"
    known = registry()
    assert registry_sha256() == identity["feature_registry_sha256"], "REGISTRY_DRIFT"
    panels: dict[str, Any] = {}
    for role, step in STEPS.items():
        candidates = {
            name: expected
            for name, expected in identity["completed_steps"][step]["artifacts"].items()
            if name.endswith(".parquet")
        }
        assert len(candidates) == 1, f"AMBIGUOUS_PANEL:{role}"
        relative, expected = next(iter(candidates.items()))
        path = (RUN / relative).resolve()
        assert path.is_relative_to(RUN.resolve()), "PANEL_OUTSIDE_REGISTERED_RUN"
        actual = digest(path)
        assert actual == expected, f"PANEL_HASH_DRIFT:{role}"
        metadata, schema = pq.read_metadata(path), pq.read_schema(path)
        dates = []
        for index in range(metadata.num_row_groups):
            group = metadata.row_group(index)
            for column_index in range(group.num_columns):
                column = group.column(column_index)
                if column.path_in_schema == "session_date" and column.statistics is not None:
                    stats = column.statistics
                    if stats.has_min_max:
                        dates.append((str(stats.min), str(stats.max)))
        names = schema.names
        registered = [
            feature for name in (f"{role}_CORE", f"{role}_RICH") if name in known
            for feature in known[name].features
        ]
        assert set(registered) <= set(names), f"REGISTERED_COLUMNS_MISSING:{role}"
        histogram = [
            name for name in names
            if name.startswith(("b1_quote_age_bin_", "b2_latency_bin_"))
        ]
        extra = [name for name in names if name not in set(registered) | set(histogram) | KEYS]
        panel = {
            "relative_path": relative, "path": str(path), "sha256": actual,
            "matches_registered_hash": True, "bytes": path.stat().st_size,
            "rows_from_footer": metadata.num_rows, "columns_count": len(schema),
            "columns": [{"name": field.name, "type": str(field.type)} for field in schema],
            "session_date_min_from_footer": min(x[0] for x in dates) if dates else None,
            "session_date_max_from_footer": max(x[1] for x in dates) if dates else None,
            "registered_core_and_rich": registered,
            "histogram_columns": histogram, "outside_registry_and_keys": extra,
        }
        if role in {"B1", "B2"}:
            custody = B1_CUSTODY if role == "B1" else B2_CUSTODY
            reconstructed = [
                name for name in names if name not in KEYS | set(histogram) | custody
            ]
            assert len(reconstructed) == (34 if role == "B1" else 74)
            panel["inventory_count_reconstruction"] = reconstructed
            panel["reconstruction_status"] = "INFERRED_COUNT_NOT_OFFICIAL_FEATURE_ALLOWLIST"
            panel["excluded_custody_columns_for_reconstruction"] = sorted(custody)
        if role == "B0":
            panel["forbidden_predictor_columns"] = ["rv30", "jump30", "role", "source"]
            panel["additional_non_target_candidate"] = ["minute_bucket"]
            assert {"rv30", "jump30"} <= set(names), "B0_OUTCOME_SCHEMA_CHANGED"
            assert len(registered) == 22
        panels[role] = panel
    source_paths = [
        "src/mds650/har.py", "src/mds650/rp2/flow.py", "src/mds650/rp2/surface.py",
        "scripts/rp2_block4_b0_panel.py", "scripts/rp2_block5_surface_panel.py",
        "scripts/rp2_block6_flow_panel.py", "configs/rp2_v3_feature_sets.json",
        "docs/methodology_decisions.md",
    ]
    return {
        "schema_version": "rp4-registered-panel-inventory-v1",
        "scope": "HASHES_AND_PARQUET_FOOTERS_ONLY_NO_DATA_ROWS",
        "run_id": identity["run_id"], "run_identity_sha256": digest(RUN / "run_identity.json"),
        "input_manifest_file_sha256": digest(RUN / "input_manifest.json"),
        "input_manifest_registered_semantic_sha256": manifest_digest,
        "input_manifest_matches_registered_identity": True,
        "source_sha256": {name: digest(ROOT / name) for name in source_paths},
        "inspector_sha256": digest(Path(__file__)), "panels": panels,
        "harq_columns_in_existing_producer": [*HAR_COLUMNS, HARQ_COLUMN],
        "rp4_features_materialized": False, "a1_specification_frozen": False,
        "data_rows_decoded": 0, "target_values_decoded": 0,
        "provider_requests": 0, "model_fits": 0, "model_evaluations": 0,
        "new_grid_and_dealer_columns": "NOT_MATERIALIZED_OR_FROZEN_BY_THIS_INVENTORY",
    }


def columns_markdown(document: dict[str, Any]) -> str:
    lines = ["# RP4: columnas exactas verificadas", "",
             "Inventario previo a A1, no una especificación de modelos congelada.", ""]
    for role, panel in document["panels"].items():
        lines += [f"## {role}", "", f"Archivo: `{panel['path']}`.", "",
                  f"SHA256: `{panel['sha256']}`.", ""]
        for key, title in (
            ("registered_core_and_rich", "Registro CORE + RICH existente"),
            (
                "outside_registry_and_keys",
                "Fuera del registro y las claves; clasificar, no incluir automáticamente",
            ),
            (
                "inventory_count_reconstruction",
                "Reconstrucción del conteo solicitado; "
                "incluye diagnósticos y no es una lista oficial",
            ),
            ("histogram_columns", "Histogramas de calidad, no selección automática de predictores"),
        ):
            if panel.get(key):
                lines += [f"### {title} ({len(panel[key])})", "", "```text", *panel[key], "```", ""]
        lines += [
            "### Esquema completo (solo nombres y tipos)", "",
            "| Columna | Tipo |", "| --- | --- |",
        ]
        lines += [f"| `{field['name']}` | {field['type']} |" for field in panel["columns"]]
        lines += [""]
    lines += ["## HARQ: columnas del productor existente, no materializadas aquí", "", "```text",
              *document["harq_columns_in_existing_producer"], "```", ""]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write", action="store_true", help="Create new inventory files exclusively"
    )
    args = parser.parse_args()
    document = snapshot()
    outputs = {
        OUT / "inventory.json": json.dumps(document, indent=2, sort_keys=True) + "\n",
        OUT / "COLUMNS.md": columns_markdown(document),
    }
    if args.write:
        assert not any(path.exists() for path in outputs), "REFUSING_INVENTORY_OVERWRITE"
    for path, content in outputs.items():
        if args.write:
            with path.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(content)
        else:
            assert path.read_text(encoding="utf-8") == content, f"INVENTORY_DRIFT:{path.name}"
    print(json.dumps({"status": "PASS_METADATA_INVENTORY_ONLY", "panels_verified": len(STEPS),
                      "output_sha256": {path.name: digest(path) for path in outputs}}, indent=2))


if __name__ == "__main__":
    main()
