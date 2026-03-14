from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from models import Genre, ScaleLayout


@dataclass(slots=True)
class DialState:
    target_position: float = 0.0
    display_position: float = 0.0

    active_item_id: Optional[str] = None
    snapped_item_id: Optional[str] = None

    velocity: float = 0.0
    last_active_item_id: Optional[str] = None


@dataclass(slots=True, frozen=True)
class IndicatorState:
    label: str
    is_on: bool


@dataclass(slots=True)
class UIState:
    genres: tuple[Genre, ...] = ()

    selected_genre_id: Optional[str] = None
    selected_station_id: Optional[str] = None

    genre_scale: ScaleLayout = field(default_factory=ScaleLayout)
    station_scale: ScaleLayout = field(default_factory=ScaleLayout)

    genre_dial: DialState = field(default_factory=DialState)
    station_dial: DialState = field(default_factory=DialState)

    play: bool = False
    online: bool = True

    running: bool = True
    debug: bool = False

    clock_text: str = "22:45"

    def get_selected_genre(self) -> Optional[Genre]:
        for genre in self.genres:
            if genre.id == self.selected_genre_id:
                return genre
        return None

    def get_selected_station_name(self) -> str:
        genre = self.get_selected_genre()
        if genre is None:
            return ""

        for station in genre.stations:
            if station.id == self.selected_station_id:
                return station.name
        return ""

    def get_indicators(self) -> tuple[IndicatorState, ...]:
        return (
            IndicatorState("PLAY", self.play),
            IndicatorState("ONLINE", self.online),
        )