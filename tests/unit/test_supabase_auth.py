from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path

import pytest

from mds650.supabase_auth import anon_api_key_headers, api_key_headers

REPO = Path(__file__).resolve().parents[2]


def _legacy_jwt(role: str) -> str:
    payload = base64.urlsafe_b64encode(
        json.dumps({"role": role}, separators=(",", ":")).encode()
    ).rstrip(b"=")
    return f"header.{payload.decode()}.signature"


@pytest.mark.parametrize("prefix", ["sb_secret_", "sb_publishable_"])
def test_modern_api_keys_are_never_sent_as_bearer(prefix: str) -> None:
    key = f"{prefix}example"
    assert api_key_headers(key) == {"apikey": key}


def test_legacy_jwt_keeps_both_headers() -> None:
    key = "header.payload.signature"
    assert api_key_headers(key) == {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }


@pytest.mark.parametrize("key", ["", "  ", "sb_future_example"])
def test_invalid_or_unknown_modern_key_fails_closed(key: str) -> None:
    with pytest.raises(ValueError, match="SUPABASE_API_KEY"):
        api_key_headers(key)


def test_publishable_key_is_valid_for_anonymous_probe() -> None:
    assert anon_api_key_headers(" sb_publishable_example ") == {
        "apikey": "sb_publishable_example"
    }


def test_legacy_anon_jwt_is_valid_for_anonymous_probe() -> None:
    key = _legacy_jwt("anon")
    assert anon_api_key_headers(key) == {
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }


@pytest.mark.parametrize(
    "key",
    [
        "",
        "not-a-jwt",
        "sb_secret_example",
        "sb_future_example",
        _legacy_jwt("authenticated"),
        _legacy_jwt("service_role"),
    ],
)
def test_anonymous_probe_rejects_unverified_or_elevated_keys(key: str) -> None:
    with pytest.raises(ValueError, match="SUPABASE_ANON_KEY"):
        anon_api_key_headers(key)


def test_access_posture_rejects_elevated_key_before_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = REPO / "scripts" / "verify_access_posture.py"
    spec = importlib.util.spec_from_file_location("verify_access_posture_auth_test", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(
        module.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: pytest.fail("network reached with an elevated key"),
    )

    with pytest.raises(ValueError, match="SUPABASE_ANON_KEY_ROLE_UNSAFE"):
        module._get("https://example.invalid", "sb_secret_example")


def test_access_posture_main_reports_an_unsafe_key_without_a_traceback(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    script = REPO / "scripts" / "verify_access_posture.py"
    spec = importlib.util.spec_from_file_location("verify_access_posture_main_test", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv(module.KEY_VARIABLE, "sb_secret_example")
    monkeypatch.setattr(
        module.urllib.request,
        "urlopen",
        lambda *_args, **_kwargs: pytest.fail("network reached with an elevated key"),
    )

    assert module.main() == 2
    assert capsys.readouterr().err.strip() == (
        "ACCESS_POSTURE_UNVERIFIED: SUPABASE_ANON_KEY_ROLE_UNSAFE"
    )


def test_supabase_consumers_use_the_shared_header_builders() -> None:
    consumers = {
        "scripts/load_supabase_datasets.py": "api_key_headers",
        "scripts/publish_rp2_v3_supabase.py": "api_key_headers",
        "scripts/sync_supabase_catalog.py": "api_key_headers",
        "scripts/sync_supabase_rp2_blocks.py": "api_key_headers",
        "scripts/upload_gated_data.py": "api_key_headers",
        "scripts/verify_access_posture.py": "anon_api_key_headers",
    }
    for relative, builder in consumers.items():
        source = (REPO / relative).read_text(encoding="utf-8")
        assert f"{builder}(" in source, f"{relative} bypasses {builder}"
        assert "Bearer {key}" not in source, f"{relative} rebuilt auth headers directly"
