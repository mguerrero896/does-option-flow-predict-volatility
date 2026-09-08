"""Check the sealed prospective registration using metadata only."""

import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path

import pytest
from scripts.rp4_archive_sources import assert_historical_sha256, original_path


def test_rp4_prospective_registration_and_amendment_are_bound() -> None:
    root = Path(__file__).resolve().parents[2]
    docs = root / "docs/rp4"
    original_hash = "317530c37d2785bb0ce0bfd6a947fc034c78a02bbd5bb102fd17efe8f91b977d"
    amendment_hash = "036f81894975a1e452fb2817c7f3989ed89dd6fe601a9378587d70559d3c7bb3"
    assert_historical_sha256(docs / "prospective_confirmation_v1.md", original_hash)
    original = json.loads(
        original_path(docs / "prospective_confirmation_v1_receipt.json").read_text()
    )
    amendment = json.loads(
        original_path(docs / "prospective_confirmation_v1_amendment_1_receipt.json").read_text()
    )
    assert amendment["amendment_sha256"] == amendment_hash
    assert_historical_sha256(docs / "prospective_confirmation_v1_amendment_1.md", amendment_hash)
    for stem in ("prospective_confirmation_v1", "prospective_confirmation_v1_amendment_1"):
        for line in original_path(docs / f"{stem}.sha256").read_text().splitlines():
            expected, name = line.split("  ", 1)
            assert Path(name).name == name
            assert_historical_sha256(docs / name, expected)
    assert amendment["original_document_sha256"] == original_hash
    assert amendment["original_sealed_at_utc"] == original["registered_at_utc"]
    assert amendment["primary_unchanged"] is True
    assert original["primary_look_sessions"] == amendment["secondary_look_sessions"] == 20
    assert original["second_look_role"] == "CUMULATIVE_STABILITY_ONLY_CANNOT_RESCUE_PRIMARY"
    assert amendment["secondary_read_count_planned"] == 1
    assert amendment["secondary_at_40"] is False
    assert amendment["secondary_multiplicity"] == {
        "method": "Holm",
        "family_size": 2,
        "alpha": 0.05,
        "unavailable_p_for_adjustment_only": 1,
    }
    spec = json.loads(original_path(root / "artifacts/rp4_v4_a1/specification.json").read_text())
    for name, digest in original["source_sha256"].items():
        assert_historical_sha256(root / name, digest)
    for name, digest in original["scientific_field_sha256"].items():
        payload = json.dumps(spec[name], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        assert hashlib.sha256(payload.encode()).hexdigest() == digest, name
    assert amendment["ablated_columns"] == spec["gamma_imbalance"]["columns"]
    assert amendment["retain_dealer_columns"] == spec["dealer_columns"]
    assert amendment["remove_presence_indicators"] is True
    reduced = set(spec["feature_sets"]["B2"]) - set(amendment["ablated_columns"])
    assert len(reduced) == amendment["ablated_predictors"] == 134
    assert amendment["full_predictors"] == len(spec["feature_sets"]["B2"]) == 138
    assert amendment["bootstrap"] == spec["inference"]["bootstrap"]
    collector = amendment["collector"]
    assert collector["state"] == "Ready" and collector["enabled"] is True
    assert collector["start_boundary"] == "2026-09-09T10:00:00"
    assert collector["wake_to_run"] is False and collector["start_when_available"] is True
    assert (
        datetime.fromisoformat(original["registered_at_utc"])
        < datetime.fromisoformat(amendment["sealed_at_utc"])
        < datetime.fromisoformat(collector["next_run"])
    )
    for name in ("dry_run_before", "dry_run_after"):
        assert collector[name]["exit_code"] == 0
        result = json.loads(collector[name]["stdout"][0])
        assert result["status"] == "DRY_RUN_NO_NETWORK"
        assert result["close_grace_minutes"] == 30
        for field in ("credential_reads", "network_requests", "target_reads", "model_fits"):
            assert result[field] == 0
    assert collector["data_root_exists_after"] is False
    offsets = {"EDT/AEST": (-4, 10), "EDT/AEDT": (-4, 11), "EST/AEDT": (-5, 11)}
    offsets["EST/AEST"] = (-5, 10)
    assert {row["regime"] for row in amendment["regimes"]} == set(offsets)
    for row in amendment["regimes"]:
        ny, sydney = offsets[row["regime"]]
        hour = (10 - sydney + ny) % 24
        assert row["ny_previous_day_hour"] == hour
        assert row["hours_after_1600_close"] == hour - 16 >= 2


def test_amendment_2_registers_pooled_and_trimmed_secondaries_without_rescuing_primary() -> None:
    root = Path(__file__).resolve().parents[2]
    docs = root / "docs/rp4"
    stem = "prospective_confirmation_v1_amendment_2"
    receipt = json.loads(original_path(docs / f"{stem}_receipt.json").read_text(encoding="utf-8"))
    assert receipt["document_sha256"] == (
        "b545c36faa4a48764a3433b008d859780a2116f5275a8553b95765d3a2d50cf9"
    )
    assert_historical_sha256(docs / f"{stem}.md", receipt["document_sha256"])
    sidecar = original_path(docs / f"{stem}.sha256").read_text(encoding="utf-8").splitlines()
    assert len(sidecar) == 2
    assert {line.split("  ", 1)[1] for line in sidecar} == {
        f"{stem}.md",
        f"{stem}_receipt.json",
    }
    for line in sidecar:
        expected, name = line.split("  ", 1)
        assert Path(name).name == name
        assert_historical_sha256(docs / name, expected)
    for name, expected in receipt["source_sha256"].items():
        assert_historical_sha256(root / name, expected)
    original = json.loads(
        original_path(docs / "prospective_confirmation_v1_receipt.json").read_text()
    )
    first = json.loads(
        original_path(docs / "prospective_confirmation_v1_amendment_1_receipt.json").read_text()
    )
    assert receipt["original_sha256"] == original["document_sha256"]
    assert receipt["amendment_1_sha256"] == first["amendment_sha256"]
    assert receipt["primary_unchanged"] and receipt["primary_look_sessions"] == 20
    assert receipt["primary_family"] == original["confirmation_family"]
    assert receipt["primary_horizon_minutes"] == original["confirmation_horizon_minutes"]
    assert receipt["stability_sessions"] == 40 and receipt["stability_cannot_rescue_primary"]
    assert receipt["secondary_single_look_at_prospective_sessions"] == 20
    assert receipt["secondary_at_40"] is False
    assert receipt["bootstrap"] == first["bootstrap"]
    pooled = receipt["secondary_D"]
    assert (
        pooled["historical_sessions"] + pooled["prospective_sessions"]
        == pooled["pooled_sessions"]
        == 45
    )
    assert pooled["historical_already_observed"] and not pooled["independent_replication"]
    assert pooled["weight_per_session"] == 1 / 45
    assert pooled["historical_fits_recomputed"] is False
    assert pooled["sequence"] == original["family_sequence"]
    assert pooled["family"] == original["confirmation_family"] and pooled["horizon_minutes"] == 15
    assert pooled["alpha"] == 0.05 and pooled["alternative"] == "greater"
    assert pooled["require_positive_estimate"] and not pooled["can_rescue_primary"]
    assert pooled["in_ABC_Holm"] is False
    with original_path(root / pooled["historical_losses_source"]).open(
        encoding="utf-8", newline=""
    ) as stream:
        historical = list(csv.DictReader(stream))
    days = [row["session_date"] for row in historical]
    assert len(days) == len(set(days)) == pooled["historical_sessions"] == 25
    assert days == sorted(days) and (days[0], days[-1]) == ("2026-08-03", "2026-09-04")
    trimmed = receipt["secondary_C"]
    assert trimmed["statistic"] == "trimmed_mean_5pct" and trimmed["alternative"] == "two-sided"
    assert trimmed["family"] == "lightgbm_qlike" and trimmed["horizon_minutes"] == 15
    assert trimmed["contrast"] == "B2_over_B1" and trimmed["require_positive_estimate"]
    assert int(trimmed["sessions"] * trimmed["trim_each_tail"]) == trimmed["removed_each_tail"] == 1
    assert trimmed["retained"] == trimmed["sessions"] - 2 * trimmed["removed_each_tail"] == 18
    multiplicity = receipt["secondary_multiplicity"]
    assert multiplicity["members"] == ["A", "B", "C"] and multiplicity["family_size"] == 3
    assert multiplicity["thresholds"] == [0.05 / 3, 0.05 / 2, 0.05]
    assert multiplicity["unavailable_p_for_adjustment_only"] == 1
    assert multiplicity["global_control_claimed"] is False
    assert first["secondary_multiplicity"]["family_size"] == 2  # Historical seal remains intact.
    observed = receipt["collector_observation"]
    assert not observed["data_root_exists"] and not observed["start_scheduled_task_called"]
    assert observed["last_task_result"] == 267011 and observed["state"] == "Ready"
    assert datetime.fromisoformat(first["sealed_at_utc"]) < datetime.fromisoformat(
        receipt["sealed_at_utc"]
    )
    assert datetime.fromisoformat(receipt["sealed_at_utc"]) < datetime.fromisoformat(
        observed["next_run"]
    )
    assert (
        not receipt["prospective_data_read"]
        and receipt["new_fits"] == receipt["new_bootstraps"] == 0
    )


def test_amendment_2_rejects_coordinated_document_and_sidecar_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Change only in-memory reads; the actual sealed files are never written."""
    docs = Path(__file__).resolve().parents[2] / "docs/rp4"
    stem = "prospective_confirmation_v1_amendment_2"
    document = original_path(docs / f"{stem}.md")
    sidecar_path = original_path(docs / f"{stem}.sha256")
    original_bytes = Path.read_bytes
    original_text = Path.read_text
    content = original_bytes(document)
    changed = content.replace(b"El primario no cambia:", b"El primario cambia:", 1)
    assert content != changed
    changed_digest = hashlib.sha256(changed).hexdigest()
    sidecar = original_text(sidecar_path, encoding="utf-8").replace(
        hashlib.sha256(content).hexdigest(), changed_digest, 1
    )
    monkeypatch.setattr(
        Path, "read_bytes", lambda path: changed if path == document else original_bytes(path)
    )
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda path, *args, **kwargs: (
            sidecar if path == sidecar_path else original_text(path, *args, **kwargs)
        ),
    )
    with pytest.raises(AssertionError):
        test_amendment_2_registers_pooled_and_trimmed_secondaries_without_rescuing_primary()
