from __future__ import annotations

import pygame


class DesktopDisplay:
    def __init__(
        self,
        *,
        width: int,
        height: int,
        fullscreen: bool,
        window_title: str,
    ) -> None:
        flags = pygame.FULLSCREEN if fullscreen else 0
        self._surface = pygame.display.set_mode((width, height), flags)
        pygame.display.set_caption(window_title)

    @property
    def surface(self) -> pygame.Surface:
        return self._surface

    def present(self) -> None:
        pygame.display.flip()

    def shutdown(self) -> None:
        # Kept for symmetry with other display backends.
        return None
