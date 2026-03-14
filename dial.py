from __future__ import annotations

from typing import Iterable, Optional

import layout
from models import Genre, ScaleItem, ScaleLayout, Station
from state import DialState


def build_scale_items(
    entries: Iterable[tuple[str, str]],
    item_width: float,
    step: float,
) -> ScaleLayout:
    items: list[ScaleItem] = []

    logical_center = 0.0
    for item_id, label in entries:
        items.append(
            ScaleItem(
                id=item_id,
                label=label,
                logical_center=logical_center,
                width=item_width,
            )
        )
        logical_center += step

    return ScaleLayout(items=tuple(items))


def build_genre_scale(genres: tuple[Genre, ...]) -> ScaleLayout:
    entries = [(genre.id, genre.name) for genre in genres]
    return build_scale_items(entries, layout.GENRE_ITEM_W, layout.GENRE_ITEM_W)


def build_station_scale(stations: tuple[Station, ...]) -> ScaleLayout:
    entries = [(station.id, station.name) for station in stations]
    return build_scale_items(entries, layout.STATION_ITEM_W, layout.STATION_ITEM_W)


def get_scale_bounds(scale: ScaleLayout) -> tuple[float, float]:
    if not scale.items:
        return 0.0, 0.0

    return scale.items[0].logical_center, scale.items[-1].logical_center


def clamp_target_position(target: float, scale: ScaleLayout) -> float:
    min_pos, max_pos = get_scale_bounds(scale)
    return max(min_pos, min(max_pos, target))


def nudge_target(dial: DialState, delta: float, scale: ScaleLayout) -> None:
    dial.target_position = clamp_target_position(dial.target_position + delta, scale)


def jump_to_item(dial: DialState, scale: ScaleLayout, item_id: Optional[str]) -> None:
    if item_id is None:
        return

    item = scale.get_item_by_id(item_id)
    if item is None:
        return

    dial.target_position = item.logical_center
    dial.display_position = item.logical_center
    dial.active_item_id = item.id
    dial.last_active_item_id = item.id


def logical_to_screen_x(logical_x: float, display_position: float) -> float:
    return layout.CENTER_X + (logical_x - display_position)


def find_item_by_position(scale: ScaleLayout, position: float) -> Optional[ScaleItem]:
    for item in scale.items:
        if item.logical_start <= position <= item.logical_end:
            return item
    return None


def find_active_item_with_hysteresis(
    scale: ScaleLayout,
    position: float,
    current_item_id: Optional[str],
    hysteresis: float,
) -> Optional[ScaleItem]:
    current_item = scale.get_item_by_id(current_item_id) if current_item_id else None

    if current_item is not None:
        hold_start = current_item.logical_start - hysteresis
        hold_end = current_item.logical_end + hysteresis
        if hold_start <= position <= hold_end:
            return current_item

    return find_item_by_position(scale, position)


def update_dial(
    dial: DialState,
    scale: ScaleLayout,
    dt: float,
    follow_speed: float,
    hysteresis: float,
    snap_epsilon: float = 0.01,
) -> None:
    if not scale.items:
        dial.active_item_id = None
        dial.last_active_item_id = None
        dial.target_position = 0.0
        dial.display_position = 0.0
        return

    dial.target_position = clamp_target_position(dial.target_position, scale)

    follow = min(1.0, dt * follow_speed)
    dial.display_position += (dial.target_position - dial.display_position) * follow

    if abs(dial.target_position - dial.display_position) < snap_epsilon:
        dial.display_position = dial.target_position

    active_item = find_active_item_with_hysteresis(
        scale=scale,
        position=dial.display_position,
        current_item_id=dial.active_item_id,
        hysteresis=hysteresis,
    )

    dial.last_active_item_id = dial.active_item_id
    dial.active_item_id = active_item.id if active_item else None