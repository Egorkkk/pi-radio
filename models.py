from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True, frozen=True)
class Station:
    id: str
    name: str
    stream_ref: Optional[str] = None


@dataclass(slots=True, frozen=True)
class Genre:
    id: str
    name: str
    stations: tuple[Station, ...] = ()


@dataclass(slots=True, frozen=True)
class ScaleItem:
    id: str
    label: str
    logical_center: float
    width: float

    @property
    def logical_start(self) -> float:
        return self.logical_center - self.width / 2

    @property
    def logical_end(self) -> float:
        return self.logical_center + self.width / 2


@dataclass(slots=True, frozen=True)
class ScaleLayout:
    items: tuple[ScaleItem, ...] = ()

    def get_item_by_id(self, item_id: str) -> Optional[ScaleItem]:
        for item in self.items:
            if item.id == item_id:
                return item
        return None