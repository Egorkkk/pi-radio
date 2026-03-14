from __future__ import annotations

import pygame

import theme


def draw_startup_splash(surface: pygame.Surface) -> None:
    pygame.font.init()

    width, height = surface.get_size()
    center_x = width // 2
    center_y = height // 2

    panel_width = min(width - 84, 396)
    panel_height = 112
    panel_rect = pygame.Rect(0, 0, panel_width, panel_height)
    panel_rect.center = (center_x, center_y)
    inner_rect = panel_rect.inflate(-16, -16)

    surface.fill(theme.BG)
    pygame.draw.line(surface, (20, 14, 10), (0, 0), (width, 0), 1)
    pygame.draw.line(surface, (5, 3, 2), (0, height - 1), (width, height - 1), 1)

    pygame.draw.rect(surface, (18, 10, 6), panel_rect, border_radius=10)
    pygame.draw.rect(surface, (58, 36, 18), panel_rect, width=1, border_radius=10)
    pygame.draw.rect(surface, (28, 16, 10), inner_rect, width=1, border_radius=8)

    pygame.draw.line(
        surface,
        (72, 44, 20),
        (panel_rect.left + 28, panel_rect.top + 14),
        (panel_rect.right - 28, panel_rect.top + 14),
        1,
    )
    pygame.draw.line(
        surface,
        (48, 28, 14),
        (panel_rect.left + 28, panel_rect.bottom - 14),
        (panel_rect.right - 28, panel_rect.bottom - 14),
        1,
    )

    font = pygame.font.SysFont("bahnschrift", 28)
    text_surface = font.render("WARMING UP...", True, theme.TEXT_BRIGHT)
    text_rect = text_surface.get_rect(center=(center_x, center_y - 2))
    surface.blit(text_surface, text_rect)
