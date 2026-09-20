from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_PROJECT_ENV = _BACKEND_ROOT / ".env"


def _read_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.is_file():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


@dataclass(frozen=True)
class KimiSettings:
    api_key: str
    base_url: str
    model: str
    max_completion_tokens: int
    source: str

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.base_url and self.model)


def _value(
    env_file: Dict[str, str],
    primary: str,
    legacy: str,
) -> str:
    return (
        os.environ.get(primary, "").strip()
        or env_file.get(primary, "").strip()
        or os.environ.get(legacy, "").strip()
        or env_file.get(legacy, "").strip()
    )


def load_kimi_settings() -> KimiSettings:
    env_file = _read_env_file(_PROJECT_ENV)

    key = _value(env_file, "ADVISOROPS_AI_API_KEY", "WORKBENCH_KIMI_API_KEY")
    base = _value(env_file, "ADVISOROPS_AI_BASE_URL", "WORKBENCH_KIMI_BASE_URL")
    model = _value(env_file, "ADVISOROPS_AI_MODEL", "WORKBENCH_KIMI_MODEL")
    max_tokens = _value(
        env_file,
        "ADVISOROPS_AI_MAX_COMPLETION_TOKENS",
        "WORKBENCH_KIMI_MAX_COMPLETION_TOKENS",
    )

    source = "unconfigured"
    if key and base and model:
        source = (
            "process_env"
            if os.environ.get("ADVISOROPS_AI_API_KEY")
            or os.environ.get("WORKBENCH_KIMI_API_KEY")
            else "advisorops_env_file"
        )

    return KimiSettings(
        api_key=key,
        base_url=base.rstrip("/"),
        model=model,
        max_completion_tokens=min(int(max_tokens or "4096"), 8192),
        source=source,
    )
