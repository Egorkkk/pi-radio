from __future__ import annotations

import math
from typing import Iterable, Optional

import layout
from models import Genre, ScaleItem, ScaleLayout, Station
from state import DialState


REBASE_PERIOD_THRESHOLD = 4.0


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

    period = logical_center if items else 0.0
    return ScaleLayout(items=tuple(items), period=period)


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


def get_scale_period(scale: ScaleLayout) -> float:
    if len(scale.items) <= 1:
        return 0.0
    return scale.period


def clamp_target_position(target: float, scale: ScaleLayout) -> float:
    if not scale.items:
        return 0.0
    if len(scale.items) == 1:
        return scale.items[0].logical_center
    return target


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


def nearest_wrapped_position(logical_x: float, reference_position: float, period: float) -> float:
    if period <= 0.0:
        return logical_x

    turns = math.floor(((reference_position - logical_x) / period) + 0.5)
    return logical_x + turns * period


def find_item_by_position(scale: ScaleLayout, position: float) -> Optional[ScaleItem]:
    period = get_scale_period(scale)
    closest_item: Optional[ScaleItem] = None
    closest_distance: Optional[float] = None

    for item in scale.items:
        logical_center = nearest_wrapped_position(item.logical_center, position, period)
        logical_start = logical_center - item.width / 2
        logical_end = logical_center + item.width / 2

        if logical_start <= position <= logical_end:
            distance = abs(position - logical_center)
            if closest_distance is None or distance < closest_distance:
                closest_item = item
                closest_distance = distance

    return closest_item


def find_active_item_with_hysteresis(
    scale: ScaleLayout,
    position: float,
    current_item_id: Optional[str],
    hysteresis: float,
) -> Optional[ScaleItem]:
    period = get_scale_period(scale)
    current_item = scale.get_item_by_id(current_item_id) if current_item_id else None

    if current_item is not None:
        logical_center = nearest_wrapped_position(current_item.logical_center, position, period)
        hold_start = logical_center - current_item.width / 2 - hysteresis
        hold_end = logical_center + current_item.width / 2 + hysteresis
        if hold_start <= position <= hold_end:
            return current_item

    return find_item_by_position(scale, position)


def rebase_dial_positions(dial: DialState, scale: ScaleLayout) -> None:
    period = get_scale_period(scale)
    if period <= 0.0:
        return

    max_abs_position = max(abs(dial.target_position), abs(dial.display_position))
    if max_abs_position < period * REBASE_PERIOD_THRESHOLD:
        return

    turns = math.floor((dial.display_position / period) + 0.5)
    if turns == 0:
        return

    shift = turns * period
    dial.target_position -= shift
    dial.display_position -= shift


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

    if len(scale.items) == 1:
        item = scale.items[0]
        dial.active_item_id = item.id
        dial.last_active_item_id = item.id
        dial.target_position = item.logical_center
        dial.display_position = item.logical_center
        return

    dial.target_position = clamp_target_position(dial.target_position, scale)

    follow = min(1.0, dt * follow_speed)
    dial.display_position += (dial.target_position - dial.display_position) * follow

    if abs(dial.target_position - dial.display_position) < snap_epsilon:
        dial.display_position = dial.target_position

    rebase_dial_positions(dial, scale)

    active_item = find_active_item_with_hysteresis(
        scale=scale,
        position=dial.display_position,
        current_item_id=dial.active_item_id,
        hysteresis=hysteresis,
    )

    dial.last_active_item_id = dial.active_item_id
    dial.active_item_id = active_item.id if active_item else None
