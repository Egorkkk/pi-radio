from __future__ import annotations

from time import perf_counter

import pygame

import layout
from app import (
    create_initial_state,
    initialize_scales,
    move_genre_left,
    move_genre_right,
    move_station_left,
    move_station_right,
    toggle_debug,
    update_state,
)
from config import load_config
from difm_catalog import DIFMCatalog
from difm_client import DIFMClient, DIFMClientError
from difm_genre_map import load_difm_genre_map
from mpv_backend import MpvBackend
from platform_runtime import create_display_backend
from radio_catalog import RadioCatalog
from radio_controller import RadioController
from renderer import UIRenderer
from runtime_persistence import RuntimePersistence
from sample_data import build_sample_genres
from station_selection_policy import StationSelectionPolicy


WINDOW_TITLE = "Vintage Radio UI MVP"


def handle_events(state) -> None:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            state.running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                state.running = False

            elif event.key == pygame.K_a:
                move_genre_left(state)
            elif event.key == pygame.K_d:
                move_genre_right(state)

            elif event.key == pygame.K_LEFT:
                move_station_left(state)
            elif event.key == pygame.K_RIGHT:
                move_station_right(state)

            elif event.key == pygame.K_F1:
                toggle_debug(state)


def apply_persisted_selection(state, persisted_state) -> None:
    if persisted_state.last_genre_id is None:
        return

    genre_ids = {genre.id for genre in state.genres}
    if persisted_state.last_genre_id not in genre_ids:
        return

    state.selected_genre_id = persisted_state.last_genre_id
    initialize_scales(state)

    if persisted_state.last_station_id is None:
        return

    selected_genre = state.get_selected_genre()
    if selected_genre is None:
        return

    station_ids = {station.id for station in selected_genre.stations}
    if persisted_state.last_station_id not in station_ids:
        return

    state.selected_station_id = persisted_state.last_station_id
    initialize_scales(state)


def save_runtime_selection(persistence: RuntimePersistence, state, enabled: bool) -> None:
    if not enabled:
        return

    persistence.save(
        last_genre_id=state.selected_genre_id,
        last_station_id=state.selected_station_id,
    )


def build_runtime_catalog(config) -> RadioCatalog:
    client = DIFMClient(config.difm)
    channels = client.fetch_channels(use_cache_fallback=True)
    difm_catalog = DIFMCatalog(channels)
    genre_map = load_difm_genre_map("difm_genres.txt")
    return RadioCatalog.from_difm(
        difm_catalog=difm_catalog,
        genre_map=genre_map,
    )


def build_runtime_genres(config):
    try:
        catalog = build_runtime_catalog(config)
        ui_genres = catalog.build_ui_genres()
        if ui_genres:
            return catalog, ui_genres
    except DIFMClientError as exc:
        print(f"[pi-radio] DI.FM catalog load failed: {exc}")
    except OSError as exc:
        print(f"[pi-radio] Failed to load runtime genre map/catalog: {exc}")

    fallback_genres = build_sample_genres()
    fallback_catalog = RadioCatalog(
        genres=(),
        stations=(),
    )
    return fallback_catalog, fallback_genres


def bootstrap_ui(config, persisted_state, initial_genres):
    pygame.init()
    pygame.mixer.quit()
    display_backend = create_display_backend(
        platform_config=config.platform,
        window_title=WINDOW_TITLE,
    )

    renderer = UIRenderer()
    state = create_initial_state(initial_genres)
    apply_persisted_selection(state, persisted_state)

    renderer.render(display_backend.surface, state)
    display_backend.present()
    return display_backend, renderer, state


def replace_state_genres(state, runtime_genres, persisted_state) -> None:
    state.genres = runtime_genres

    if runtime_genres:
        state.selected_genre_id = runtime_genres[0].id
        first_station_id = runtime_genres[0].stations[0].id if runtime_genres[0].stations else None
        state.selected_station_id = first_station_id
    else:
        state.selected_genre_id = None
        state.selected_station_id = None

    initialize_scales(state)
    apply_persisted_selection(state, persisted_state)


def main() -> None:
    config = load_config()
    persistence = RuntimePersistence(config.persistence.state_file)
    persisted_state = persistence.load()
    catalog, runtime_genres = build_runtime_genres(config)

    display_backend, renderer, state = bootstrap_ui(
        config,
        persisted_state,
        runtime_genres,
    )

    clock = pygame.time.Clock()

    backend = MpvBackend(config=config.mpv)
    selection_policy = StationSelectionPolicy(
        settle_epsilon=1.0,
        settle_time=0.30,
    )
    controller = RadioController(
        catalog=catalog,
        backend=backend,
        selection_policy=selection_policy,
    )

    last_saved_genre_id = state.selected_genre_id
    last_saved_station_id = state.selected_station_id

    try:
        while state.running:
            dt = clock.tick(config.platform.fps) / 1000.0

            handle_events(state)
            update_state(state, dt)
            controller.update(state, dt)
            should_present = renderer.needs_render(state)
            if should_present:
                renderer.render(display_backend.surface, state)
            else:
                renderer.note_skipped_frame()

            if (
                state.selected_genre_id != last_saved_genre_id
                or state.selected_station_id != last_saved_station_id
            ):
                save_runtime_selection(
                    persistence=persistence,
                    state=state,
                    enabled=config.persistence.save_on_station_change,
                )
                last_saved_genre_id = state.selected_genre_id
                last_saved_station_id = state.selected_station_id

            if should_present:
                present_started_at = perf_counter()
                display_backend.present()
                renderer.note_present_duration(perf_counter() - present_started_at)
    finally:
        save_runtime_selection(
            persistence=persistence,
            state=state,
            enabled=config.persistence.save_on_station_change,
        )
        controller.shutdown()
        display_backend.shutdown()
        pygame.quit()


if __name__ == "__main__":
    main()
