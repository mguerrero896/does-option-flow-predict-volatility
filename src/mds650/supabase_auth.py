"""Build Supabase API headers without treating modern API keys as JWTs."""

from __future__ import annotations

import base64
import binascii
import json


def api_key_headers(key: str) -> dict[str, str]:
    """Return headers for a modern ``sb_*`` key or a legacy JWT key.

    Modern publishable and secret keys are opaque API keys and belong only in
    ``apikey``. Legacy anon and service-role keys are JWTs and retain the Bearer
    header used by endpoints that inspect their embedded role claim.
    """

    value = key.strip()
    if not value:
        raise ValueError("SUPABASE_API_KEY_EMPTY")
    if value.startswith(("sb_secret_", "sb_publishable_")):
        return {"apikey": value}
    if value.startswith("sb_"):
        raise ValueError("SUPABASE_API_KEY_PREFIX_UNSUPPORTED")
    return {"apikey": value, "Authorization": f"Bearer {value}"}


def anon_api_key_headers(key: str) -> dict[str, str]:
    """Return headers only for a publishable key or a legacy JWT claiming ``anon``.

    The endpoint verifies a legacy JWT's signature; this local claim check prevents
    an elevated credential from being used for an anonymous-access measurement.
    """

    value = key.strip()
    if value.startswith("sb_publishable_"):
        return api_key_headers(value)
    if value.startswith("sb_"):
        raise ValueError("SUPABASE_ANON_KEY_ROLE_UNSAFE")

    try:
        _header, payload, _signature = value.split(".")
        encoded = payload.encode("ascii")
        decoded = base64.b64decode(
            encoded + b"=" * (-len(encoded) % 4), altchars=b"-_", validate=True
        )
        claims = json.loads(decoded)
    except (ValueError, UnicodeError, binascii.Error):
        raise ValueError("SUPABASE_ANON_KEY_INVALID") from None
    if not isinstance(claims, dict) or claims.get("role") != "anon":
        raise ValueError("SUPABASE_ANON_KEY_ROLE_UNSAFE")
    return api_key_headers(value)
