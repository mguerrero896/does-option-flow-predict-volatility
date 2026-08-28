"""Validated, presence-only configuration for bounded research runs."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from mds650.errors import ResearchOnlyViolation, SecretPresenceError


def _store_root(raw: str) -> Path:
    path = Path(raw)
    return path.parent if path.name.casefold() == "data" else path


def production_data_root() -> Path:
    """Return the configured external store root or fail before touching data."""

    raw = os.environ.get("MDS650_DATA_ROOT")
    if not raw:
        raise RuntimeError("MDS650_DATA_ROOT_REQUIRED")
    return _store_root(raw)


def effective_data_root() -> Path:
    """Return a sandbox override when present, otherwise the production store."""

    override = os.environ.get("MDS650_EXTERNAL_ROOT")
    return Path(override) if override else production_data_root()


def provisional_data_root() -> Path:
    """Return the configured root or an import-safe invalid sentinel.

    Script modules use this only to declare path constants. Their entrypoints call
    :func:`effective_data_root` before I/O, which turns missing configuration into the
    explicit ``MDS650_DATA_ROOT_REQUIRED`` failure.
    """

    try:
        return effective_data_root()
    except RuntimeError:
        # ponytail: keep imports and --help side-effect free; execution validates again.
        return Path("<MDS650_DATA_ROOT_REQUIRED>")


def rp2_store_root() -> Path:
    """Return the RP2-specific override or the configured production store."""

    override = os.environ.get("MDS650_RP2_STORE_ROOT")
    return Path(override) if override else production_data_root()


class ResearchSettings(BaseSettings):
    """Environment-backed settings with fail-closed research safety.

    Notes
    -----
    Secret fields are retained as ``SecretStr`` and are exposed only through
    boolean presence checks. The default mode is research-only and disabling it
    is rejected at validation time.
    """

    unusualwhales_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="UNUSUALWHALES_API_KEY",
        repr=False,
    )
    massive_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="MASSIVE_API_KEY",
        repr=False,
    )
    fmp_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="FMP_API_KEY",
        repr=False,
    )
    research_only: bool = Field(default=True, validation_alias="MDS650_RESEARCH_ONLY")
    raw_root: Path | None = Field(default=None, validation_alias="MDS650_RAW_ROOT")

    model_config = SettingsConfigDict(
        case_sensitive=True,
        extra="ignore",
        env_file=None,
    )

    @model_validator(mode="after")
    def enforce_research_only(self) -> ResearchSettings:
        """Reject configurations that could enable external mutations.

        Raises
        ------
        ResearchOnlyViolation
            If ``MDS650_RESEARCH_ONLY`` is explicitly false.
        """
        if not self.research_only:
            raise ResearchOnlyViolation("RESEARCH_ONLY_REQUIRED")
        return self

    def secret_presence(self) -> dict[str, bool]:
        """Return provider-key presence without exposing values.

        Returns
        -------
        dict[str, bool]
            Stable environment variable names mapped to presence booleans.
        """
        return {
            "UNUSUALWHALES_API_KEY": self.unusualwhales_api_key is not None,
            "MASSIVE_API_KEY": self.massive_api_key is not None,
            "FMP_API_KEY": self.fmp_api_key is not None,
        }

    def require_provider_secrets(self) -> None:
        """Fail closed unless all three provider keys are present.

        Raises
        ------
        SecretPresenceError
            If one or more required credentials are absent. The error contains
            names only, never secret values.
        """
        missing = [name for name, present in self.secret_presence().items() if not present]
        if missing:
            raise SecretPresenceError("MISSING_PROVIDER_SECRETS:" + ",".join(missing))
