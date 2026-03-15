from __future__ import annotations

import os
import sys

import pygame

# чтобы можно было импортировать startup_splash.py из корня проекта
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from startup_splash import draw_startup_splash


def main() -> None:
    width, height = 480, 320  # поставьте реальное разрешение экрана
    pygame.init()
    surface = pygame.Surface((width, height))
    draw_startup_splash(surface)
    pygame.image.save(surface, "pi-radio-splash.png")
    pygame.quit()
    print("Saved pi-radio-splash.png")


if __name__ == "__main__":
    main()