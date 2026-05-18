from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PUBLIC_API_BASE_URL = "https://geoserver.core-stack.org/api/v1"
API_KEY_NAMES = (
    "PUBLIC_API_X_API_KEY",
    "CORESTACK_API_KEY",
    "CORE_STACK_API_KEY",
    "corestsack-api-key",
)


def read_env_file(path: Path) -> dict[str, str]:
    """Read a simple dotenv file without requiring shell-safe key names."""
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


@dataclass(frozen=True)
class CoreStackSettings:
    public_api_base_url: str = DEFAULT_PUBLIC_API_BASE_URL
    public_api_key: str | None = None

    @classmethod
    def from_env(cls, env_file: str | Path = ".env") -> CoreStackSettings:
        env_path = Path(env_file)
        file_values = read_env_file(env_path)

        api_key = None
        for key_name in API_KEY_NAMES:
            api_key = os.environ.get(key_name) or file_values.get(key_name)
            if api_key:
                break

        base_url = (
            os.environ.get("PUBLIC_API_BASE_URL")
            or file_values.get("PUBLIC_API_BASE_URL")
            or DEFAULT_PUBLIC_API_BASE_URL
        )

        return cls(public_api_base_url=base_url.rstrip("/"), public_api_key=api_key)

    @property
    def has_public_api_key(self) -> bool:
        return bool(self.public_api_key)

