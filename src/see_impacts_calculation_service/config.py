"""Runtime configuration for the SEE impacts calculation service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _read_string(name: str, default: str) -> str:
    return os.environ.get(name, default).strip() or default


def _read_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer") from error


@dataclass(frozen=True)
class RuntimeConfig:
    """Configuration kept separate from calculation-specific CE-RISE inputs."""

    bind_address: str
    port: int
    hex_core_base_url: str
    http_timeout_secs: int
    background_project_dir: Path
    background_project_name: str
    brightway_workspace_dir: Path
    hex_core_bearer_token: str | None = None
    background_database_name: str = "bonsai"
    biosphere_database_name: str = "biosphere3"
    calculation_timeout_secs: int = 900
    max_concurrent_calculations: int = 2

    @classmethod
    def from_env(cls) -> "RuntimeConfig":
        return cls(
            bind_address=_read_string("BIND_ADDRESS", "0.0.0.0"),
            port=_read_int("PORT", 8080),
            hex_core_base_url=_read_string("HEX_CORE_BASE_URL", "http://127.0.0.1:8080").rstrip(
                "/"
            ),
            http_timeout_secs=_read_int("HTTP_TIMEOUT_SECS", 30),
            background_project_dir=Path(
                _read_string(
                    "BACKGROUND_PROJECT_DIR",
                    "data/background/projects/cerise_bonsai.c4e8a461df1485d0b80d98d3e46a35b9",
                )
            ).resolve(),
            background_project_name=_read_string(
                "BACKGROUND_PROJECT_NAME", "cerise_bonsai"
            ),
            brightway_workspace_dir=Path(
                _read_string("BRIGHTWAY_WORKSPACE_DIR", "runtime/brightway")
            ).resolve(),
            hex_core_bearer_token=os.environ.get("HEX_CORE_BEARER_TOKEN") or None,
            background_database_name=_read_string("BACKGROUND_DATABASE_NAME", "bonsai"),
            biosphere_database_name=_read_string("BIOSPHERE_DATABASE_NAME", "biosphere3"),
            calculation_timeout_secs=_read_int("CALCULATION_TIMEOUT_SECS", 900),
            max_concurrent_calculations=_read_int("MAX_CONCURRENT_CALCULATIONS", 2),
        )
