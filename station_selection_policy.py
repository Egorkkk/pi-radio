from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class StationSelectionPolicy:
    settle_epsilon: float = 1.0
    settle_time: float = 0.30

    stable_station_id: Optional[str] = None
    stable_for_seconds: float = 0.0
    last_confirmed_station_id: Optional[str] = None

    def reset(self) -> None:
        self.stable_station_id = None
        self.stable_for_seconds = 0.0
        self.last_confirmed_station_id = None

    def update(
        self,
        active_station_id: Optional[str],
        target_position: float,
        display_position: float,
        dt: float,
    ) -> Optional[str]:
        if active_station_id is None:
            self.stable_station_id = None
            self.stable_for_seconds = 0.0
            return None

        if active_station_id != self.stable_station_id:
            self.stable_station_id = active_station_id
            self.stable_for_seconds = 0.0
        else:
            self.stable_for_seconds += max(dt, 0.0)

        is_settled = abs(target_position - display_position) <= self.settle_epsilon
        held_long_enough = self.stable_for_seconds >= self.settle_time

        if not is_settled or not held_long_enough:
            return None

        if active_station_id == self.last_confirmed_station_id:
            return None

        self.last_confirmed_station_id = active_station_id
        return active_station_id