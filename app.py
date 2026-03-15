from __future__ import annotations

import layout
from dial import build_genre_scale, build_station_scale, jump_to_item, nudge_target, update_dial
from models import Genre
from sample_data import build_sample_genres
from state import UIState


GENRE_INPUT_STEP = 22.0
STATION_INPUT_STEP = 24.0

GENRE_FOLLOW_SPEED = 10.0
STATION_FOLLOW_SPEED = 12.0

GENRE_HYSTERESIS = 6.0
STATION_HYSTERESIS = 8.0


def create_initial_state(genres: tuple[Genre, ...] | None = None) -> UIState:
    if genres is None:
        genres = build_sample_genres()

    initial_genre_id = genres[0].id if genres else None
    initial_station_id = genres[0].stations[0].id if genres and genres[0].stations else None

    state = UIState(
        genres=genres,
        selected_genre_id=initial_genre_id,
        selected_station_id=initial_station_id,
        play=False,
        online=True,
        running=True,
        debug=False,
    )

    initialize_scales(state)
    return state


def initialize_scales(state: UIState) -> None:
    state.genre_scale = build_genre_scale(state.genres)
    jump_to_item(state.genre_dial, state.genre_scale, state.selected_genre_id)

    genre = state.get_selected_genre()
    stations = genre.stations if genre else ()
    state.station_scale = build_station_scale(stations)
    jump_to_item(state.station_dial, state.station_scale, state.selected_station_id)


def rebuild_station_scale_for_selected_genre(state: UIState) -> None:
    genre = state.get_selected_genre()
    stations = genre.stations if genre else ()

    state.station_scale = build_station_scale(stations)

    first_station_id = stations[0].id if stations else None
    state.selected_station_id = first_station_id
    jump_to_item(state.station_dial, state.station_scale, first_station_id)


def update_state(state: UIState, dt: float) -> None:
    update_dial(
        dial=state.genre_dial,
        scale=state.genre_scale,
        dt=dt,
        follow_speed=GENRE_FOLLOW_SPEED,
        hysteresis=GENRE_HYSTERESIS,
    )

    active_genre_id = state.genre_dial.active_item_id
    if active_genre_id != state.selected_genre_id:
        state.selected_genre_id = active_genre_id
        rebuild_station_scale_for_selected_genre(state)

    update_dial(
        dial=state.station_dial,
        scale=state.station_scale,
        dt=dt,
        follow_speed=STATION_FOLLOW_SPEED,
        hysteresis=STATION_HYSTERESIS,
    )

    state.selected_station_id = state.station_dial.active_item_id


def move_genre_left(state: UIState) -> None:
    nudge_target(state.genre_dial, -GENRE_INPUT_STEP, state.genre_scale)


def move_genre_right(state: UIState) -> None:
    nudge_target(state.genre_dial, GENRE_INPUT_STEP, state.genre_scale)


def move_station_left(state: UIState) -> None:
    nudge_target(state.station_dial, -STATION_INPUT_STEP, state.station_scale)


def move_station_right(state: UIState) -> None:
    nudge_target(state.station_dial, STATION_INPUT_STEP, state.station_scale)


def drag_genre_by_pixels(state: UIState, delta_x: float) -> None:
    # Positive finger motion should make the scale move right under the fixed cursor.
    nudge_target(state.genre_dial, -delta_x, state.genre_scale)


def drag_station_by_pixels(state: UIState, delta_x: float) -> None:
    # Positive finger motion should make the scale move right under the fixed cursor.
    nudge_target(state.station_dial, -delta_x, state.station_scale)


def toggle_debug(state: UIState) -> None:
    state.debug = not state.debug
