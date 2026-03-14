from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from models import Genre


@dataclass(slots=True, frozen=True)
class StationRecord:
    id: str
    name: str
    stream_url: str
    genre_id: str


class RadioCatalog:
    def __init__(self, genres: tuple[Genre, ...]) -> None:
        self._genres = genres
        self._stations_by_id: dict[str, StationRecord] = {}

        for genre in genres:
            for station in genre.stations:
                self._stations_by_id[station.id] = StationRecord(
                    id=station.id,
                    name=station.name,
                    genre_id=genre.id,
                    stream_url=self._build_fake_stream_url(genre.id, station.id),
                )

    def get_station(self, station_id: str) -> Optional[StationRecord]:
        return self._stations_by_id.get(station_id)

    def _build_fake_stream_url(self, genre_id: str, station_id: str) -> str:
        return f"fake://{genre_id}/{station_id}"