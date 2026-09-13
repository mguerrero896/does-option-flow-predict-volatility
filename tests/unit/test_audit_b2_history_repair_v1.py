"""The repair comparison cannot conflate numeric change, missingness or row drift."""

import polars as pl
import pytest
from scripts.audit_b2_history_repair_v1 import feature_impact
from tests.unit.test_phase6_b2 import _frames

from mds650.phase6 import B2V2_FEATURES, build_b2v2_from_activity


def test_impact_distinguishes_changed_values_lost_rows_and_misalignment() -> None:
    activity, origins = _frames(days=23)
    before = build_b2v2_from_activity(activity, origins)
    last = before.item(-1, "origin_id")
    changed = before.with_columns(
        pl.when(pl.col("origin_id") == last)
        .then(pl.col(B2V2_FEATURES[0]) + 1)
        .otherwise(pl.col(B2V2_FEATURES[0]))
        .alias(B2V2_FEATURES[0])
    )
    result = feature_impact(before, changed)
    assert result["changed_common_rows"] == result["changed_common_cells"] == 1
    assert result["lost_complete"] == result["gained_complete"] == 0
    lost = changed.with_columns(
        pl.when(pl.col("origin_id") == last)
        .then(None)
        .otherwise(pl.col(B2V2_FEATURES[0]))
        .alias(B2V2_FEATURES[0])
    )
    assert feature_impact(before, lost)["lost_complete"] == 1
    with pytest.raises(ValueError, match="B2_REPAIR_ORIGIN_MISMATCH"):
        feature_impact(before, changed.slice(1))
