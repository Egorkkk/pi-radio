from __future__ import annotations

import pygame

import layout
import theme
from dial import logical_to_screen_x
from state import UIState


class UIRenderer:
    def __init__(self) -> None:
        pygame.font.init()

        self.font_small = pygame.font.SysFont("consolas", layout.FONT_SMALL)
        self.font_genre = pygame.font.SysFont("bahnschrift", layout.FONT_GENRE)
        self.font_station = pygame.font.SysFont("bahnschrift", layout.FONT_STATION)
        self.font_station_small = pygame.font.SysFont("bahnschrift", layout.FONT_STATION_SMALL)
        self.font_clock = pygame.font.SysFont("consolas", layout.FONT_CLOCK)
        self.font_center_title = pygame.font.SysFont("bahnschrift", layout.FONT_CENTER_TITLE)
        self.font_debug = pygame.font.SysFont("consolas", 12)

    def render(self, surface: pygame.Surface, state: UIState) -> None:
        self._draw_background(surface)

        self._draw_scale_glass(
            surface,
            layout.GENRE_GLASS_X,
            layout.GENRE_GLASS_Y,
            layout.GENRE_GLASS_W,
            layout.GENRE_GLASS_H,
            radius=7,
        )
        self._draw_scale_glass(
            surface,
            layout.STATION_GLASS_X,
            layout.STATION_GLASS_Y,
            layout.STATION_GLASS_W,
            layout.STATION_GLASS_H,
            radius=7,
        )

        self._draw_center_panel(surface, state)

        self._draw_genre_scale(surface, state)
        self._draw_station_scale(surface, state)

        self._draw_depth_overlay(
            surface,
            pygame.Rect(layout.GENRE_GLASS_X, layout.GENRE_GLASS_Y, layout.GENRE_GLASS_W, layout.GENRE_GLASS_H),
        )
        self._draw_depth_overlay(
            surface,
            pygame.Rect(layout.STATION_GLASS_X, layout.STATION_GLASS_Y, layout.STATION_GLASS_W, layout.STATION_GLASS_H),
        )

        self._draw_cursor_segments(surface)

        if state.debug:
            self._draw_debug(surface, state)

    def _with_clip(self, surface: pygame.Surface, rect: pygame.Rect) -> pygame.Rect:
        old_clip = surface.get_clip()
        surface.set_clip(rect)
        return old_clip

    def _restore_clip(self, surface: pygame.Surface, old_clip: pygame.Rect) -> None:
        surface.set_clip(old_clip)

    def _draw_background(self, surface: pygame.Surface) -> None:
        surface.fill(theme.BG)
        pygame.draw.line(surface, (20, 14, 10), (0, 0), (layout.SCREEN_W, 0), 1)
        pygame.draw.line(surface, (5, 3, 2), (0, layout.SCREEN_H - 1), (layout.SCREEN_W, layout.SCREEN_H - 1), 1)

    def _draw_scale_glass(self, surface: pygame.Surface, x: int, y: int, w: int, h: int, radius: int) -> None:
        r = pygame.Rect(x, y, w, h)
        pygame.draw.rect(surface, theme.GLASS_MID, r, border_radius=radius)
        pygame.draw.rect(surface, (56, 34, 18), r, width=1, border_radius=radius)
        pygame.draw.line(surface, theme.GLASS_HIGHLIGHT, (r.left + 10, r.top + 8), (r.right - 10, r.top + 8), 1)
        pygame.draw.line(surface, (18, 10, 6), (r.left + 8, r.bottom - 8), (r.right - 8, r.bottom - 8), 1)

    def _draw_center_panel(self, surface: pygame.Surface, state: UIState) -> None:
        r = pygame.Rect(
            layout.INFO_PANEL_X,
            layout.INFO_PANEL_Y,
            layout.INFO_PANEL_W,
            layout.INFO_PANEL_H,
        )
        inner = r.inflate(-16, -16)

        pygame.draw.rect(surface, (18, 10, 6), r, border_radius=10)
        pygame.draw.rect(surface, (58, 36, 18), r, width=1, border_radius=10)
        pygame.draw.rect(surface, (28, 16, 10), inner, width=1, border_radius=8)

        pygame.draw.line(
            surface,
            (72, 44, 20),
            (r.left + 28, layout.INFO_DECOR_LINE_Y_TOP),
            (r.right - 28, layout.INFO_DECOR_LINE_Y_TOP),
            1,
        )
        pygame.draw.line(
            surface,
            (48, 28, 14),
            (r.left + 28, layout.INFO_DECOR_LINE_Y_BOTTOM),
            (r.right - 28, layout.INFO_DECOR_LINE_Y_BOTTOM),
            1,
        )

        pygame.draw.line(
            surface,
            (90, 54, 22),
            (r.left + 18, r.centery),
            (r.left + 34, r.centery),
            1,
        )
        pygame.draw.line(
            surface,
            (90, 54, 22),
            (r.right - 34, r.centery),
            (r.right - 18, r.centery),
            1,
        )

        clock_surf = self.font_clock.render(state.clock_text, True, theme.TEXT_BRIGHT)
        surface.blit(clock_surf, (layout.CENTER_X - clock_surf.get_width() // 2, layout.CLOCK_Y - 2))

        station_name = state.get_selected_station_name() or "—"
        self._draw_clipped_label(
            surface=surface,
            text=station_name,
            font=self.font_center_title,
            color=theme.TEXT_BRIGHT,
            center_x=layout.CENTER_X,
            y=layout.STATION_NAME_Y - 2,
            max_width=330,
        )

        self._draw_indicators(surface, state)

    def _draw_indicators(self, surface: pygame.Surface, state: UIState) -> None:
        indicators = state.get_indicators()
        if not indicators:
            return

        gap = 92
        total_w = (len(indicators) - 1) * gap
        start_x = layout.CENTER_X - total_w // 2

        for idx, ind in enumerate(indicators):
            x = start_x + idx * gap
            dot_x = x - 14
            dot_y = layout.INDICATORS_Y + 7

            pygame.draw.circle(
                surface,
                theme.STATUS_ON if ind.is_on else theme.STATUS_OFF,
                (dot_x, dot_y),
                3,
            )

            text_surf = self.font_small.render(ind.label, True, theme.TEXT_MAIN)
            surface.blit(text_surf, (x, layout.INDICATORS_Y))

    def _draw_genre_scale(self, surface: pygame.Surface, state: UIState) -> None:
        clip_rect = pygame.Rect(
            layout.GENRE_GLASS_X + 6,
            layout.GENRE_GLASS_Y + 4,
            layout.GENRE_GLASS_W - 12,
            layout.GENRE_GLASS_H - 8,
        )
        old_clip = self._with_clip(surface, clip_rect)

        pygame.draw.line(
            surface,
            theme.AMBER_DIM,
            (layout.SCALE_LEFT, layout.GENRE_BASELINE_Y),
            (layout.SCALE_RIGHT, layout.GENRE_BASELINE_Y),
            1,
        )

        for item in state.genre_scale.items:
            screen_x = logical_to_screen_x(item.logical_center, state.genre_dial.display_position)

            if screen_x < layout.SCALE_LEFT - 100 or screen_x > layout.SCALE_RIGHT + 100:
                continue

            is_active = item.id == state.genre_dial.active_item_id
            tick_h = layout.GENRE_TICK_LONG_H if is_active else layout.GENRE_TICK_MEDIUM_H
            tick_color = theme.AMBER_BRIGHT if is_active else theme.AMBER

            pygame.draw.line(
                surface,
                tick_color,
                (int(screen_x), layout.GENRE_BASELINE_Y - tick_h),
                (int(screen_x), layout.GENRE_BASELINE_Y),
                1 if not is_active else 2,
            )

            self._draw_clipped_label(
                surface=surface,
                text=item.label,
                font=self.font_genre,
                color=theme.TEXT_BRIGHT if is_active else theme.TEXT_MAIN,
                center_x=screen_x,
                y=layout.GENRE_LABEL_Y,
                max_width=92,
            )

        self._restore_clip(surface, old_clip)

    def _draw_station_scale(self, surface: pygame.Surface, state: UIState) -> None:
        clip_rect = pygame.Rect(
            layout.STATION_GLASS_X + 6,
            layout.STATION_GLASS_Y + 4,
            layout.STATION_GLASS_W - 12,
            layout.STATION_GLASS_H - 8,
        )
        old_clip = self._with_clip(surface, clip_rect)

        pygame.draw.line(
            surface,
            theme.AMBER,
            (layout.SCALE_LEFT, layout.STATION_BASELINE_Y),
            (layout.SCALE_RIGHT, layout.STATION_BASELINE_Y),
            2,
        )

        self._draw_station_texture_ticks(surface, state)

        for item in state.station_scale.items:
            screen_x = logical_to_screen_x(item.logical_center, state.station_dial.display_position)

            if screen_x < layout.SCALE_LEFT - 180 or screen_x > layout.SCALE_RIGHT + 180:
                continue

            is_active = item.id == state.station_dial.active_item_id

            marker_top = layout.STATION_BASELINE_Y - 22
            pygame.draw.line(
                surface,
                theme.AMBER_BRIGHT if is_active else theme.AMBER,
                (int(screen_x), marker_top),
                (int(screen_x), layout.STATION_TICK_BOTTOM),
                2 if is_active else 1,
            )

            font = self.font_station_small if len(item.label) > 14 else self.font_station
            color = theme.TEXT_BRIGHT if is_active else theme.TEXT_MAIN

            self._draw_clipped_label(
                surface=surface,
                text=item.label,
                font=font,
                color=color,
                center_x=screen_x,
                y=layout.STATION_LABEL_Y,
                max_width=150,
            )

        self._restore_clip(surface, old_clip)

    def _draw_station_texture_ticks(self, surface: pygame.Surface, state: UIState) -> None:
        spacing = 16
        offset = state.station_dial.display_position % spacing
        half_count = layout.SCALE_WIDTH // (2 * spacing) + 4

        short_top = layout.STATION_BASELINE_Y - 12
        medium_top = layout.STATION_BASELINE_Y - 18
        long_top = layout.STATION_BASELINE_Y - 24

        for i in range(-half_count, half_count + 1):
            tick_x = layout.CENTER_X + i * spacing - offset

            if not (layout.SCALE_LEFT <= tick_x <= layout.SCALE_RIGHT):
                continue

            local_dx = abs(tick_x - layout.CENTER_X)

            if local_dx < 10:
                top = long_top
                color = theme.AMBER_BRIGHT
                width = 2
            elif local_dx < 42:
                top = medium_top
                color = theme.AMBER
                width = 1
            else:
                top = short_top
                color = theme.AMBER_DIM
                width = 1

            pygame.draw.line(
                surface,
                color,
                (int(tick_x), top),
                (int(tick_x), layout.STATION_TICK_BOTTOM),
                width,
            )

    def _draw_depth_overlay(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)

        max_edge_alpha = 210
        max_top_bottom_alpha = 70
        facet_alpha = 110
        facet_w = 42

        for x in range(rect.width):
            nx = abs((x / max(1, rect.width - 1)) * 2 - 1)
            alpha = int((nx ** 1.5) * max_edge_alpha)
            pygame.draw.line(
                overlay,
                (0, 0, 0, alpha),
                (x, 0),
                (x, rect.height),
                1,
            )

        for y in range(rect.height):
            ny = abs((y / max(1, rect.height - 1)) * 2 - 1)
            alpha = int((ny ** 2.0) * max_top_bottom_alpha)
            pygame.draw.line(
                overlay,
                (0, 0, 0, alpha),
                (0, y),
                (rect.width, y),
                1,
            )

        for x in range(facet_w):
            a = int((1 - x / max(1, facet_w)) * facet_alpha)

            pygame.draw.line(
                overlay,
                (0, 0, 0, a),
                (x, 0),
                (x, rect.height),
                1,
            )
            pygame.draw.line(
                overlay,
                (0, 0, 0, a),
                (rect.width - 1 - x, 0),
                (rect.width - 1 - x, rect.height),
                1,
            )

        surface.blit(overlay, rect.topleft)

        pygame.draw.line(
            surface,
            (36, 20, 10),
            (rect.left + 10, rect.top + 6),
            (rect.left + 10, rect.bottom - 6),
            1,
        )
        pygame.draw.line(
            surface,
            (36, 20, 10),
            (rect.right - 10, rect.top + 6),
            (rect.right - 10, rect.bottom - 6),
            1,
        )

    def _draw_cursor_segments(self, surface: pygame.Surface) -> None:
        x = layout.CURSOR_X
        w = layout.CURSOR_SEGMENT_W

        pygame.draw.line(
            surface,
            theme.CURSOR_BRIGHT,
            (x, layout.TOP_CURSOR_Y1),
            (x, layout.TOP_CURSOR_Y2),
            w,
        )
        pygame.draw.line(
            surface,
            theme.CURSOR_BRIGHT,
            (x, layout.BOTTOM_CURSOR_Y1),
            (x, layout.BOTTOM_CURSOR_Y2),
            w,
        )

    def _draw_debug(self, surface: pygame.Surface, state: UIState) -> None:
        lines = [
            f"genre target={state.genre_dial.target_position:.1f}",
            f"genre display={state.genre_dial.display_position:.1f}",
            f"genre active={state.genre_dial.active_item_id}",
            f"station target={state.station_dial.target_position:.1f}",
            f"station display={state.station_dial.display_position:.1f}",
            f"station active={state.station_dial.active_item_id}",
        ]

        y = 4
        for line in lines:
            s = self.font_debug.render(line, True, theme.DEBUG)
            surface.blit(s, (6, y))
            y += 14

    def _draw_clipped_label(
        self,
        surface: pygame.Surface,
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        center_x: float,
        y: int,
        max_width: int,
    ) -> None:
        rendered = font.render(text, True, color)

        if rendered.get_width() > max_width:
            clipped_text = self._fit_text(text, font, max_width)
            rendered = font.render(clipped_text, True, color)

        x = int(center_x - rendered.get_width() // 2)
        surface.blit(rendered, (x, y))

    def _fit_text(self, text: str, font: pygame.font.Font, max_width: int) -> str:
        if font.size(text)[0] <= max_width:
            return text

        suffix = "…"
        stripped = text

        while stripped:
            candidate = stripped + suffix
            if font.size(candidate)[0] <= max_width:
                return candidate
            stripped = stripped[:-1]

        return suffix
