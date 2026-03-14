from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from difm_catalog import DIFMCatalog, DIFMStationRecord
from difm_genre_map import DIFMGenreMap
from models import Genre, Station


@dataclass(slots=True, frozen=True)
class StationRecord:
    id: str
    name: str
    stream_url: str
    genre_ids: tuple[str, ...]
    external_key: Optional[str] = None
    description: Optional[str] = None
    asset_url: Optional[str] = None
    homepage_url: Optional[str] = None
    codec: Optional[str] = None
    bitrate: Optional[int] = None


@dataclass(slots=True, frozen=True)
class GenreRecord:
    id: str
    name: str
    station_ids: tuple[str, ...]


class RadioCatalog:
    def __init__(
        self,
        genres: tuple[GenreRecord, ...],
        stations: tuple[StationRecord, ...],
    ) -> None:
        self._genres = genres
        self._stations = stations
        self._genres_by_id: dict[str, GenreRecord] = {genre.id: genre for genre in genres}
        self._stations_by_id: dict[str, StationRecord] = {
            station.id: station for station in stations
        }

    @classmethod
    def from_difm(
        cls,
        difm_catalog: DIFMCatalog,
        genre_map: DIFMGenreMap,
    ) -> RadioCatalog:
        difm_stations = difm_catalog.list_stations()

        grouped_station_ids: dict[str, list[str]] = {
            genre.id: [] for genre in genre_map.list_genres()
        }
        stations: list[StationRecord] = []

        for station in difm_stations:
            genre_ids = cls._resolve_genre_ids_for_station(
                station=station,
                genre_map=genre_map,
            )
            if not genre_ids:
                continue

            record = StationRecord(
                id=station.id,
                name=station.name,
                stream_url=station.stream_url,
                genre_ids=genre_ids,
                external_key=station.external_key,
                description=station.description,
                asset_url=station.asset_url,
                homepage_url=_build_station_homepage(station),
            )
            stations.append(record)

            for genre_id in genre_ids:
                grouped_station_ids.setdefault(genre_id, []).append(record.id)

        genres: list[GenreRecord] = []
        for genre_entry in genre_map.list_genres():
            station_ids = tuple(grouped_station_ids.get(genre_entry.id, ()))
            if not station_ids:
                continue

            genres.append(
                GenreRecord(
                    id=genre_entry.id,
                    name=genre_entry.name,
                    station_ids=station_ids,
                )
            )

        return cls(
            genres=tuple(genres),
            stations=tuple(stations),
        )

    @staticmethod
    def _resolve_genre_ids_for_station(
        station: DIFMStationRecord,
        genre_map: DIFMGenreMap,
    ) -> tuple[str, ...]:
        matched_by_name = genre_map.get_genre_ids_for_channel_name(station.name)
        if matched_by_name:
            return matched_by_name

        matched_by_key = genre_map.get_genre_ids_for_channel_name(station.external_key)
        return matched_by_key

    def get_genre(self, genre_id: str) -> GenreRecord | None:
        return self._genres_by_id.get(genre_id)

    def get_station(self, station_id: str) -> StationRecord | None:
        return self._stations_by_id.get(station_id)

    def get_stations_for_genre(self, genre_id: str) -> tuple[StationRecord, ...]:
        genre = self.get_genre(genre_id)
        if genre is None:
            return ()

        result: list[StationRecord] = []
        for station_id in genre.station_ids:
            station = self.get_station(station_id)
            if station is not None:
                result.append(station)

        return tuple(result)

    def build_ui_genres(self) -> tuple[Genre, ...]:
        ui_genres: list[Genre] = []

        for genre in self._genres:
            station_records = self.get_stations_for_genre(genre.id)
            ui_stations = tuple(
                Station(
                    id=station.id,
                    name=station.name.upper(),
                    stream_ref=station.stream_url,
                )
                for station in station_records
            )

            ui_genres.append(
                Genre(
                    id=genre.id,
                    name=genre.name.upper(),
                    stations=ui_stations,
                )
            )

        return tuple(ui_genres)

    def list_genres(self) -> tuple[GenreRecord, ...]:
        return self._genres

    def list_stations(self) -> tuple[StationRecord, ...]:
        return self._stations


def _build_station_homepage(station: DIFMStationRecord) -> Optional[str]:
    if not station.external_key.strip():
        return None
    return f"https://www.di.fm/{station.external_key}"