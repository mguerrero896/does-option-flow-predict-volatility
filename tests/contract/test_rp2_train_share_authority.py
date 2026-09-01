"""One effective chronological split default for every RP2 CLI producer."""

from __future__ import annotations

import ast
from pathlib import Path

from mds650.rp2 import panel

REPO = Path(__file__).resolve().parents[2]
AUTHORITY = REPO / "src" / "mds650" / "rp2" / "panel.py"
RUNNER = REPO / "scripts" / "run_rp2_v3_pipeline.py"
CLI_PRODUCERS = (
    "rp2_block3_target_panel.py",
    "rp2_block4_b0_panel.py",
    "rp2_block7_dml.py",
    "rp2_block8_ladder.py",
    "rp2_block9_generalization.py",
    "rp2_block10_inference.py",
    "rp2_block11_economics.py",
    "rp2_block11b_forward_economics.py",
    "rp2_block12_prospective_design.py",
    "rp2_ext1_mechanism_utility.py",
    "rp2_ext1_directional_v2.py",
    "rp2_ext12_level4_and_tensor.py",
)
PRODUCTION_PATHS = (
    *sorted((REPO / "src" / "mds650" / "rp2").rglob("*.py")),
    *sorted((REPO / "scripts").glob("rp2*.py")),
    RUNNER,
)


def _definitions(path: Path) -> list[str]:
    definitions: list[str] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        if any(
            isinstance(target, ast.Name) and target.id == "DEFAULT_TRAIN_SHARE"
            for target in targets
        ):
            definitions.append(path.relative_to(REPO).as_posix())
    return definitions


def _cli_defaults(path: Path) -> list[str]:
    defaults: list[str] = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        if not isinstance(node.args[0], ast.Constant) or node.args[0].value != "--train-share":
            continue
        default = next(
            (keyword.value for keyword in node.keywords if keyword.arg == "default"),
            None,
        )
        defaults.append(ast.unparse(default) if default is not None else "<missing>")
    return defaults


def test_rp2_train_share_has_one_definition_and_every_cli_uses_it() -> None:
    """A future producer cannot drift from the split hashed by the pipeline manifest."""
    definitions = [
        definition for path in PRODUCTION_PATHS for definition in _definitions(path)
    ]

    assert definitions == ["src/mds650/rp2/panel.py"]
    assert panel.DEFAULT_TRAIN_SHARE == 0.6
    assert '"train_share": DEFAULT_TRAIN_SHARE' in RUNNER.read_text(encoding="utf-8")
    cli_paths = [path for path in PRODUCTION_PATHS if _cli_defaults(path)]
    assert {path.name for path in cli_paths} == set(CLI_PRODUCERS)
    for path in cli_paths:
        assert _cli_defaults(path) == ["DEFAULT_TRAIN_SHARE"], path.name
