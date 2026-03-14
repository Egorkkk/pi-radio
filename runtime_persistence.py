from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


@dataclass(slots=True, frozen=True)
class PersistedRuntimeState:
    last_genre_id: Optional[str] = None
    last_station_id: Optional[str] = None


class RuntimePersistence:
    def __init__(self, state_file: str | Path) -> None:
        self._state_file = Path(state_file)

    def load(self) -> PersistedRuntimeState:
        if not self._state_file.exists():
            return PersistedRuntimeState()

        try:
            raw = json.loads(self._state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return PersistedRuntimeState()

        if not isinstance(raw, dict):
            return PersistedRuntimeState()

        return PersistedRuntimeState(
            last_genre_id=_as_optional_str(raw.get("last_genre_id")),
            last_station_id=_as_optional_str(raw.get("last_station_id")),
        )

    def save(
        self,
        *,
        last_genre_id: Optional[str],
        last_station_id: Optional[str],
    ) -> None:
        state = PersistedRuntimeState(
            last_genre_id=last_genre_id,
            last_station_id=last_station_id,
        )

        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        self._state_file.write_text(
            json.dumps(asdict(state), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def _as_optional_str(value: object) -> Optional[str]:
    if value is None:
        return None

    if not isinstance(value, str):
        return None

    value = value.strip()
    return value or None