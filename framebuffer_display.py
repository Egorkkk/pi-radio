from __future__ import annotations

import os

import pygame


class FramebufferDisplay:
    def __init__(
        self,
        *,
        width: int,
        height: int,
        fullscreen: bool,
        framebuffer_device: str,
        window_title: str,
    ) -> None:
        self._prepare_environment(framebuffer_device)
        flags = pygame.FULLSCREEN if fullscreen else 0
        self._surface = pygame.display.set_mode((width, height), flags)
        pygame.display.set_caption(window_title)

    @staticmethod
    def _prepare_environment(framebuffer_device: str) -> None:
        os.environ.setdefault("SDL_FBDEV", framebuffer_device)
        os.environ.setdefault("SDL_VIDEODRIVER", "fbcon")
        os.environ.setdefault("SDL_NOMOUSE", "1")

    @property
    def surface(self) -> pygame.Surface:
        return self._surface

    def present(self) -> None:
        pygame.display.flip()

    def shutdown(self) -> None:
        return None
