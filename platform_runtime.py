from __future__ import annotations

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
