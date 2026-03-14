from __future__ import annotations

import pygame

import layout
from app import (
    create_initial_state,
    move_genre_left,
    move_genre_right,
    move_station_left,
    move_station_right,
    toggle_debug,
    update_state,
)
from fake_backend import FakeBackend
from radio_catalog import RadioCatalog
from radio_controller import RadioController
from renderer import UIRenderer
from station_selection_policy import StationSelectionPolicy


WINDOW_TITLE = "Vintage Radio UI MVP"
FPS = 60


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


def main() -> None:
    pygame.init()

    screen = pygame.display.set_mode((layout.SCREEN_W, layout.SCREEN_H))
    pygame.display.set_caption(WINDOW_TITLE)

    clock = pygame.time.Clock()
    renderer = UIRenderer()
    state = create_initial_state()

    catalog = RadioCatalog(state.genres)
    backend = FakeBackend()
    selection_policy = StationSelectionPolicy(
        settle_epsilon=1.0,
        settle_time=0.30,
    )
    controller = RadioController(
        catalog=catalog,
        backend=backend,
        selection_policy=selection_policy,
    )

    try:
        while state.running:
            dt = clock.tick(FPS) / 1000.0

            handle_events(state)
            update_state(state, dt)
            controller.update(state, dt)
            renderer.render(screen, state)

            pygame.display.flip()
    finally:
        controller.shutdown()
        pygame.quit()


if __name__ == "__main__":
    main()