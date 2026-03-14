from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from difm_client import DIFMChannel


@dataclass(slots=True, frozen=True)
class DIFMStationRecord:
    id: str
    name: str
    stream_url: str
    genre_id: str
    external_key: str
    description: Optional[str] = None
    asset_url: Optional[str] = None


class DIFMCatalog:
    def __init__(self, channels: list[DIFMChannel]) -> None:
        self._stations_by_id: dict[str, DIFMStationRecord] = {}
        self._stations: list[DIFMStationRecord] = []

        for channel in channels:
            station = DIFMStationRecord(
                id=f"difm:{channel.key}",
                name=channel.name,
                stream_url=channel.stream_url,
                genre_id="difm",
                external_key=channel.key,
                description=channel.description,
                asset_url=channel.asset_url,
            )
            self._stations.append(station)
            self._stations_by_id[station.id] = station

    def get_station(self, station_id: str) -> Optional[DIFMStationRecord]:
        return self._stations_by_id.get(station_id)

    def list_stations(self) -> tuple[DIFMStationRecord, ...]:
        return tuple(self._stations)