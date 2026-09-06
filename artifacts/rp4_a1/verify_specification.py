"""A1 metadata-only integrity and predictor-boundary check; no data-row reads."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main() -> None:
    freeze = json.loads((ROOT / "artifacts/rp4_a1/freeze.json").read_text())
    for key in ("specification", "document"):
        item = freeze[key]
        assert sha256(ROOT / item["path"]) == item["sha256"], f"RP4_FREEZE_DRIFT:{key}"
    spec = json.loads((ROOT / freeze["specification"]["path"]).read_text())
    assert spec["specification_md_sha256"] == freeze["document"]["sha256"]
    sets = spec["feature_sets"]
    assert [len(sets[k]) for k in ("B0", "B1", "B2")] == [29, 71, 136]
    assert set(sets["B0"]) < set(sets["B1"]) < set(sets["B2"])
    forbidden = {"rv30", "jump30", "minute_bucket", "role", "source"}
    forbidden.update(x for xs in spec["excluded_registered_predictors"].values() for x in xs)
    for names in sets.values():
        assert len(names) == len(set(names)), "RP4_DUPLICATE_FEATURE"
        assert not forbidden.intersection(names), "RP4_FORBIDDEN_PREDICTOR"
    assert len(spec["grid_columns"]) == 25
    assert set(spec["missing_allowed"]) == set(spec["grid_columns"])
    assert spec["source_cutoff_seconds"] == 120
    assert spec["purge_minutes"] == spec["embargo_minutes"] == 60
    inventory = json.loads((ROOT / "artifacts/rp4_inventory_v1/inventory.json").read_text())
    for role, item in inventory["panels"].items():
        assert sha256(Path(item["path"])) == item["sha256"], f"RP4_INPUT_DRIFT:{role}"
    print(json.dumps({"status": "PASS_A1", "registered_panels": 4,
                      "feature_counts": {k: len(v) for k, v in sets.items()},
                      "specification_sha256": freeze["specification"]["sha256"],
                      "target_values_read": 0, "model_evaluations": 0}))


if __name__ == "__main__":
    main()
