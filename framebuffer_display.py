from __future__ import annotations

from pathlib import Path
from typing import BinaryIO

import pygame


class FramebufferDisplay:
    """Render with pygame in memory and copy complete frames to a Linux fbdev."""

    _BYTES_PER_PIXEL = 4
    _RGBX_MASKS = (0x00FF0000, 0x0000FF00, 0x000000FF, 0)

    def __init__(
        self,
        *,
        width: int,
        height: int,
        fullscreen: bool,
        framebuffer_device: str,
        window_title: str,
    ) -> None:
        # A tiny dummy display provides pygame's event queue and a pixel format
        # for Surface.convert*(). It is never used for physical output.
        flags = pygame.HIDDEN
        pygame.display.set_mode((1, 1), flags)
        pygame.display.set_caption(window_title)

        self._framebuffer: BinaryIO | None = None

        try:
            self._width = width
            self._height = height
            self._row_bytes = width * self._BYTES_PER_PIXEL
            self._stride = self._read_and_validate_geometry(
                framebuffer_device=framebuffer_device,
                width=width,
                height=height,
            )
            self._surface = pygame.Surface(
                (width, height),
                depth=32,
                masks=self._RGBX_MASKS,
            )
            self._framebuffer = open(framebuffer_device, "r+b", buffering=0)
        except Exception:
            pygame.display.quit()
            raise

        _ = fullscreen  # Physical fbdev output always occupies the framebuffer.

    @property
    def surface(self) -> pygame.Surface:
        return self._surface

    def present(self) -> None:
        framebuffer = self._framebuffer
        if framebuffer is None:
            raise RuntimeError("framebuffer display is shut down")

        pixels = self._surface.get_buffer().raw
        framebuffer.seek(0)

        if self._stride == self._row_bytes:
            self._write_all(framebuffer, pixels)
            return

        for y in range(self._height):
            start = y * self._row_bytes
            self._write_all(framebuffer, pixels[start : start + self._row_bytes])
            framebuffer.seek(self._stride - self._row_bytes, 1)

    def shutdown(self) -> None:
        if self._framebuffer is not None:
            self._framebuffer.close()
            self._framebuffer = None
        pygame.display.quit()

    @classmethod
    def _read_and_validate_geometry(
        cls,
        *,
        framebuffer_device: str,
        width: int,
        height: int,
    ) -> int:
        device_name = Path(framebuffer_device).name
        sysfs_dir = Path("/sys/class/graphics") / device_name

        try:
            virtual_size_text = (sysfs_dir / "virtual_size").read_text(
                encoding="ascii"
            ).strip()
            virtual_width, virtual_height = (
                int(value) for value in virtual_size_text.split(",", maxsplit=1)
            )
            bits_per_pixel = int(
                (sysfs_dir / "bits_per_pixel").read_text(encoding="ascii").strip()
            )
            stride = int((sysfs_dir / "stride").read_text(encoding="ascii").strip())
        except (OSError, ValueError) as exc:
            raise RuntimeError(
                f"failed to read geometry for {framebuffer_device} from {sysfs_dir}: {exc}"
            ) from exc

        if bits_per_pixel != 32:
            raise RuntimeError(
                f"unsupported framebuffer format: expected 32 bpp, got {bits_per_pixel}"
            )
        if virtual_width < width or virtual_height < height:
            raise RuntimeError(
                "configured display size "
                f"{width}x{height} exceeds framebuffer {virtual_width}x{virtual_height}"
            )
        row_bytes = width * cls._BYTES_PER_PIXEL
        if stride < row_bytes:
            raise RuntimeError(
                f"framebuffer stride {stride} is smaller than a {row_bytes}-byte row"
            )

        return stride

    @staticmethod
    def _write_all(framebuffer: BinaryIO, data: bytes) -> None:
        view = memoryview(data)
        while view:
            written = framebuffer.write(view)
            if written is None or written <= 0:
                raise OSError("framebuffer write made no progress")
            view = view[written:]
