from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

from config import PlatformConfig
from framebuffer_display import FramebufferDisplay
from platform_runtime import prepare_display_environment


class DisplayEnvironmentTests(unittest.TestCase):
    def test_pi_mode_selects_dummy_before_pygame_initialization(self) -> None:
        config = PlatformConfig(mode="pi", framebuffer_device="/dev/fb7")

        with patch.dict(os.environ, {}, clear=True):
            prepare_display_environment(config)
            self.assertEqual(os.environ["SDL_VIDEODRIVER"], "dummy")
            self.assertEqual(os.environ["SDL_FBDEV"], "/dev/fb7")
            self.assertEqual(os.environ["SDL_NOMOUSE"], "1")


class FramebufferDisplayTests(unittest.TestCase):
    def tearDown(self) -> None:
        pygame.quit()

    def test_present_writes_bgrx_pixels_and_respects_stride(self) -> None:
        pygame.init()
        with tempfile.TemporaryDirectory() as temp_dir:
            framebuffer_path = Path(temp_dir) / "fb-test"
            framebuffer_path.write_bytes(bytes(24))

            with patch.object(
                FramebufferDisplay,
                "_read_and_validate_geometry",
                return_value=12,
            ):
                display = FramebufferDisplay(
                    width=2,
                    height=2,
                    fullscreen=True,
                    framebuffer_device=str(framebuffer_path),
                    window_title="test",
                )

            display.surface.set_at((0, 0), (255, 0, 0))
            display.surface.set_at((1, 0), (0, 255, 0))
            display.surface.set_at((0, 1), (0, 0, 255))
            display.surface.set_at((1, 1), (255, 255, 255))
            display.present()
            display.shutdown()

            contents = framebuffer_path.read_bytes()

        self.assertEqual(contents[0:8], b"\x00\x00\xff\x00\x00\xff\x00\x00")
        self.assertEqual(contents[8:12], bytes(4))
        self.assertEqual(contents[12:20], b"\xff\x00\x00\x00\xff\xff\xff\x00")


if __name__ == "__main__":
    unittest.main()
