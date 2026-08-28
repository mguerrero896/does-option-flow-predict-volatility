"""The public environment template documents active names without secret values."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / ".env.example"

REQUIRED = {
    "FMP_API_KEY",
    "MASSIVE_API_KEY",
    "UNUSUAL_WHALES_API_KEY",
    "UNUSUALWHALES_API_KEY",
    "SUPABASE_SERVICE_KEY",
    "SUPABASE_ANON_KEY",
    "MDS650_RESEARCH_ONLY",
    "MDS650_DATA_ROOT",
    "MDS650_EVIDENCE_ROOT",
    "MDS650_EXTERNAL_ROOT",
    "MDS650_RAW_ROOT",
    "MDS650_BULK_ROOT",
    "MDS650_RP2_STORE_ROOT",
    "MDS650_REPO_ROOT",
    "MDS650_AUDIT_OUT_DIR",
    "MDS650_AUDIT_RAW_ROOT",
    "MDS650_FMP_API_KEY",
    "MDS650_MASSIVE_BASE_URL",
}


def test_template_covers_active_configuration_without_secret_values() -> None:
    entries = {
        name: value
        for line in TEMPLATE.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
        for name, value in [line.split("=", 1)]
    }
    assert entries.keys() >= REQUIRED
    for secret in (
        "FMP_API_KEY",
        "MASSIVE_API_KEY",
        "UNUSUAL_WHALES_API_KEY",
        "UNUSUALWHALES_API_KEY",
        "SUPABASE_SERVICE_KEY",
        "SUPABASE_ANON_KEY",
        "MDS650_FMP_API_KEY",
    ):
        assert entries[secret] == ""
