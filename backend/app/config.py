from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SIBLING_FLOWEROLL_ENV = _PROJECT_ROOT.parent / "Floweroll" / ".env"


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


def load_kimi_settings() -> KimiSettings:
    own_key = os.environ.get("WORKBENCH_KIMI_API_KEY", "").strip()
    own_base = os.environ.get("WORKBENCH_KIMI_BASE_URL", "").strip()
    own_model = os.environ.get("WORKBENCH_KIMI_MODEL", "").strip()
    own_max = os.environ.get("WORKBENCH_KIMI_MAX_COMPLETION_TOKENS", "").strip()

    if own_key and own_base:
        return KimiSettings(
            api_key=own_key,
            base_url=own_base.rstrip("/"),
            model=own_model or "kimi-k3",
            max_completion_tokens=int(own_max or "2048"),
            source="workbench_env",
        )

    # Local development fallback only. Reuse the already-configured sibling
    # Floweroll planner without copying its secret into this repository.
    floweroll = _read_env_file(_SIBLING_FLOWEROLL_ENV)
    key = floweroll.get("FLOWEROLL_PLANNER_API_KEY", "").strip()
    base = floweroll.get("FLOWEROLL_PLANNER_BASE_URL", "").strip()
    model = floweroll.get("FLOWEROLL_PLANNER_MODEL", "").strip()
    max_tokens = floweroll.get("FLOWEROLL_PLANNER_MAX_COMPLETION_TOKENS", "").strip()

    return KimiSettings(
        api_key=key,
        base_url=base.rstrip("/"),
        model=model or "kimi-k3",
        max_completion_tokens=min(int(max_tokens or "2048"), 4096),
        source="floweroll_local_fallback" if key and base else "unconfigured",
    )
