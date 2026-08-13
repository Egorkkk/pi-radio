from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from config import PlatformConfig


class DisplayBackend(Protocol):
    @property
    def surface(self): ...

    def present(self) -> None: ...

    def shutdown(self) -> None: ...


@dataclass(slots=True, frozen=True)
class RuntimeBootstrap:
    display_backend: DisplayBackend


def prepare_display_environment(platform_config: PlatformConfig) -> None:
    """Select SDL's driver before pygame initializes its video subsystem."""
    if platform_config.mode.lower() != "pi":
        return

    os.environ["SDL_FBDEV"] = platform_config.framebuffer_device
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_NOMOUSE"] = "1"


def create_display_backend(
    *,
    platform_config: PlatformConfig,
    window_title: str,
) -> DisplayBackend:
    if platform_config.mode.lower() == "pi":
        from framebuffer_display import FramebufferDisplay

        return FramebufferDisplay(
            width=platform_config.width,
            height=platform_config.height,
            fullscreen=platform_config.fullscreen,
            framebuffer_device=platform_config.framebuffer_device,
            window_title=window_title,
        )

    from desktop_display import DesktopDisplay

    return DesktopDisplay(
        width=platform_config.width,
        height=platform_config.height,
        fullscreen=platform_config.fullscreen,
        window_title=window_title,
    )
