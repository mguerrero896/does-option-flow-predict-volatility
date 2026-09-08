"""Static regression gates: confirmation routing only; original arithmetic untouched."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT / "artifacts/rp4_v3_b4/audit_mz_identity.py"
AUDITOR = Path(__file__).with_name("audit_mz_identity.py")


def assignments(tree: ast.AST, name: str) -> list[str]:
    return [
        ast.dump(node.value, include_attributes=False)
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign)
        and any(isinstance(item, ast.Name) and item.id == name for item in node.targets)
    ]


def test_audit_arithmetic_remains_exactly_the_original_ast() -> None:
    original = ast.parse(ORIGINAL.read_text(encoding="utf-8"))
    current = ast.parse(AUDITOR.read_text(encoding="utf-8"))
    for name in (
        "affine",
        "nonfinite",
        "applied",
        "floor",
        "expected",
        "hit",
        "hits",
        "observed",
        "predicted",
        "scale",
        "scale_error",
        "centered",
        "slope_check",
        "intercept_check",
        "ratio",
        "losses",
        "raw_ratio",
        "raw_losses",
        "calculated",
        "raw",
        "contribution",
    ):
        assert assignments(original, name), name
        assert assignments(original, name) == assignments(current, name), name


def test_no_training_or_optimization_calls_are_added() -> None:
    tree = ast.parse(AUDITOR.read_text(encoding="utf-8"))
    forbidden = {"fit", "train", "lstsq", "minimize", "optimize", "mz_secondary"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = (
                node.func.attr
                if isinstance(node.func, ast.Attribute)
                else getattr(node.func, "id", "")
            )
            assert name not in forbidden


def test_confirmation_closure_and_resource_guards_are_explicit() -> None:
    text = AUDITOR.read_text(encoding="utf-8")
    assert "evaluation/confirmation" in text
    assert "artifacts/rp4_v3_b3/receipt.json" in text
    assert "== 25" in text and "== 9750" in text
    assert 'record["binding"]["window"] == "confirmation"' in text
    assert "DEADLINE = datetime(2026, 9, 7, 18, 25, tzinfo=UTC)" in text
    assert 'pool["num_threads"] <= 1' in text
    assert "kernel.GetPriorityClass(process_handle) == 0x4000" in text
