from __future__ import annotations

import math
import os
from time import perf_counter

import pygame

import layout
import theme
from dial import logical_to_screen_x, nearest_wrapped_position
from state import UIState


PROFILE_ENV_VAR = "PI_RADIO_RENDER_PROFILE"
PROFILE_INTERVAL_ENV_VAR = "PI_RADIO_RENDER_PROFILE_INTERVAL"


def _env_flag(name: str) -> bool:
    value = os.getenv(name, "")
    return value.lower() not in {"", "0", "false", "no", "off"}


class RenderProfiler:
    def __init__(self) -> None:
        self.enabled = _env_flag(PROFILE_ENV_VAR)
        self.interval_frames = max(1, self._read_interval())
        self._rendered_frames = 0
        self._skipped_frames = 0
        self._section_totals: dict[str, float] = {}
        self._section_maxima: dict[str, float] = {}

    def _read_interval(self) -> int:
        raw_value = os.getenv(PROFILE_INTERVAL_ENV_VAR, "120")
        try:
            return int(raw_value)
        except ValueError:
            return 120

    def mark(self) -> float:
        if not self.enabled:
            return 0.0
        return perf_counter()

    def end_section(self, name: str, started_at: float) -> None:
        if not self.enabled:
            return

        elapsed = perf_counter() - started_at
        self._section_totals[name] = self._section_totals.get(name, 0.0) + elapsed
        current_max = self._section_maxima.get(name, 0.0)
        if elapsed > current_max:
            self._section_maxima[name] = elapsed

    def finish_render(self, frame_started_at: float) -> None:
        if not self.enabled:
            return

        self.end_section("frame", frame_started_at)
        self._rendered_frames += 1

    def record_present(self, elapsed: float) -> None:
        if not self.enabled:
            return

        self._section_totals["present"] = self._section_totals.get("present", 0.0) + elapsed
        current_max = self._section_maxima.get("present", 0.0)
        if elapsed > current_max:
            self._section_maxima["present"] = elapsed
        self._emit_if_due()

    def record_skipped_frame(self) -> None:
        if not self.enabled:
            return

        self._skipped_frames += 1
        self._emit_if_due()

    def _emit_if_due(self) -> None:
        total_frames = self._rendered_frames + self._skipped_frames
        if total_frames == 0 or total_frames % self.interval_frames != 0:
            return

        rendered_frames = max(1, self._rendered_frames)
        parts = [
            f"frames={total_frames}",
            f"rendered={self._rendered_frames}",
            f"skipped={self._skipped_frames}",
        ]

        ordered_sections = (
            "frame",
            "background",
            "center_panel",
            "genre_scale",
            "station_scale",
            "foreground",
            "debug",
            "present",
        )
        for name in ordered_sections:
            total = self._section_totals.get(name)
            if total is None:
                continue
            average_ms = (total / rendered_frames) * 1000.0
            max_ms = self._section_maxima.get(name, 0.0) * 1000.0
            parts.append(f"{name}_avg={average_ms:.2f}ms")
            parts.append(f"{name}_max={max_ms:.2f}ms")

        print("[pi-radio][render-profile] " + " ".join(parts))
        self._rendered_frames = 0
        self._skipped_frames = 0
        self._section_totals.clear()
        self._section_maxima.clear()


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

        self.profiler = RenderProfiler()

        self._genre_glass_rect = pygame.Rect(
            layout.GENRE_GLASS_X,
            layout.GENRE_GLASS_Y,
            layout.GENRE_GLASS_W,
            layout.GENRE_GLASS_H,
        )
        self._station_glass_rect = pygame.Rect(
            layout.STATION_GLASS_X,
            layout.STATION_GLASS_Y,
            layout.STATION_GLASS_W,
            layout.STATION_GLASS_H,
        )
        self._genre_clip_rect = pygame.Rect(
            layout.GENRE_GLASS_X + 6,
            layout.GENRE_GLASS_Y + 4,
            layout.GENRE_GLASS_W - 12,
            layout.GENRE_GLASS_H - 8,
        )
        self._station_clip_rect = pygame.Rect(
            layout.STATION_GLASS_X + 6,
            layout.STATION_GLASS_Y + 4,
            layout.STATION_GLASS_W - 12,
            layout.STATION_GLASS_H - 8,
        )

        self._fit_cache: dict[tuple[int, str, int], str] = {}
        self._text_cache: dict[tuple[int, str, tuple[int, int, int], int | None], pygame.Surface] = {}
        self._depth_overlay_cache: dict[tuple[int, int], pygame.Surface] = {}
        self._station_texture_cache: dict[int, pygame.Surface] = {}

        self._background_layer = self._build_background_layer()
        self._foreground_layer = self._build_foreground_layer()
        self._last_render_signature: tuple[object, ...] | None = None

    def needs_render(self, state: UIState) -> bool:
        return self._build_render_signature(state) != self._last_render_signature

    def note_skipped_frame(self) -> None:
        self.profiler.record_skipped_frame()

    def note_present_duration(self, elapsed: float) -> None:
        self.profiler.record_present(elapsed)

    def render(self, surface: pygame.Surface, state: UIState) -> None:
        frame_started_at = self.profiler.mark()

        section_started_at = self.profiler.mark()
        surface.blit(self._background_layer, (0, 0))
        self.profiler.end_section("background", section_started_at)

        section_started_at = self.profiler.mark()
        self._draw_center_panel_content(surface, state)
        self.profiler.end_section("center_panel", section_started_at)

        section_started_at = self.profiler.mark()
        self._draw_genre_scale(surface, state)
        self.profiler.end_section("genre_scale", section_started_at)

        section_started_at = self.profiler.mark()
        self._draw_station_scale(surface, state)
        self.profiler.end_section("station_scale", section_started_at)

        section_started_at = self.profiler.mark()
        surface.blit(self._foreground_layer, (0, 0))
        self.profiler.end_section("foreground", section_started_at)

        if state.debug:
            section_started_at = self.profiler.mark()
            self._draw_debug(surface, state)
            self.profiler.end_section("debug", section_started_at)

        self._last_render_signature = self._build_render_signature(state)
        self.profiler.finish_render(frame_started_at)

    def _build_render_signature(self, state: UIState) -> tuple[object, ...]:
        return (
            state.clock_text,
            state.selected_genre_id,
            state.selected_station_id,
            state.play,
            state.online,
            state.debug,
            state.genre_dial.target_position,
            state.genre_dial.display_position,
            state.station_dial.target_position,
            state.station_dial.display_position,
            id(state.genre_scale.items),
            id(state.station_scale.items),
        )

    def _with_clip(self, surface: pygame.Surface, rect: pygame.Rect) -> pygame.Rect:
        old_clip = surface.get_clip()
        surface.set_clip(rect)
        return old_clip

    def _restore_clip(self, surface: pygame.Surface, old_clip: pygame.Rect) -> None:
        surface.set_clip(old_clip)

    def _build_background_layer(self) -> pygame.Surface:
        surface = pygame.Surface((layout.SCREEN_W, layout.SCREEN_H)).convert()
        self._draw_background(surface)
        self._draw_scale_glass(surface, self._genre_glass_rect, radius=7)
        self._draw_scale_glass(surface, self._station_glass_rect, radius=7)
        self._draw_center_panel_chrome(surface)
        pygame.draw.line(
            surface,
            theme.AMBER_DIM,
            (layout.SCALE_LEFT, layout.GENRE_BASELINE_Y),
            (layout.SCALE_RIGHT, layout.GENRE_BASELINE_Y),
            1,
        )
        pygame.draw.line(
            surface,
            theme.AMBER,
            (layout.SCALE_LEFT, layout.STATION_BASELINE_Y),
            (layout.SCALE_RIGHT, layout.STATION_BASELINE_Y),
            2,
        )
        return surface

    def _build_foreground_layer(self) -> pygame.Surface:
        surface = pygame.Surface((layout.SCREEN_W, layout.SCREEN_H), pygame.SRCALPHA).convert_alpha()
        self._blit_depth_overlay(surface, self._genre_glass_rect)
        self._blit_depth_overlay(surface, self._station_glass_rect)
        self._draw_cursor_segments(surface)
        return surface

    def _draw_background(self, surface: pygame.Surface) -> None:
        surface.fill(theme.BG)
        pygame.draw.line(surface, (20, 14, 10), (0, 0), (layout.SCREEN_W, 0), 1)
        pygame.draw.line(surface, (5, 3, 2), (0, layout.SCREEN_H - 1), (layout.SCREEN_W, layout.SCREEN_H - 1), 1)

    def _draw_scale_glass(self, surface: pygame.Surface, rect: pygame.Rect, radius: int) -> None:
        pygame.draw.rect(surface, theme.GLASS_MID, rect, border_radius=radius)
        pygame.draw.rect(surface, (56, 34, 18), rect, width=1, border_radius=radius)
        pygame.draw.line(
            surface,
            theme.GLASS_HIGHLIGHT,
            (rect.left + 10, rect.top + 8),
            (rect.right - 10, rect.top + 8),
            1,
        )
        pygame.draw.line(
            surface,
            (18, 10, 6),
            (rect.left + 8, rect.bottom - 8),
            (rect.right - 8, rect.bottom - 8),
            1,
        )

    def _draw_center_panel_chrome(self, surface: pygame.Surface) -> None:
        rect = pygame.Rect(
            layout.INFO_PANEL_X,
            layout.INFO_PANEL_Y,
            layout.INFO_PANEL_W,
            layout.INFO_PANEL_H,
        )
        inner = rect.inflate(-16, -16)

        pygame.draw.rect(surface, (18, 10, 6), rect, border_radius=10)
        pygame.draw.rect(surface, (58, 36, 18), rect, width=1, border_radius=10)
        pygame.draw.rect(surface, (28, 16, 10), inner, width=1, border_radius=8)

        pygame.draw.line(
            surface,
            (72, 44, 20),
            (rect.left + 28, layout.INFO_DECOR_LINE_Y_TOP),
            (rect.right - 28, layout.INFO_DECOR_LINE_Y_TOP),
            1,
        )
        pygame.draw.line(
            surface,
            (48, 28, 14),
            (rect.left + 28, layout.INFO_DECOR_LINE_Y_BOTTOM),
            (rect.right - 28, layout.INFO_DECOR_LINE_Y_BOTTOM),
            1,
        )
        pygame.draw.line(
            surface,
            (90, 54, 22),
            (rect.left + 18, rect.centery),
            (rect.left + 34, rect.centery),
            1,
        )
        pygame.draw.line(
            surface,
            (90, 54, 22),
            (rect.right - 34, rect.centery),
            (rect.right - 18, rect.centery),
            1,
        )

    def _draw_center_panel_content(self, surface: pygame.Surface, state: UIState) -> None:
        clock_surf = self._get_text_surface(
            text=state.clock_text,
            font=self.font_clock,
            color=theme.TEXT_BRIGHT,
        )
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

            text_surf = self._get_text_surface(
                text=ind.label,
                font=self.font_small,
                color=theme.TEXT_MAIN,
            )
            surface.blit(text_surf, (x, layout.INDICATORS_Y))

    def _draw_genre_scale(self, surface: pygame.Surface, state: UIState) -> None:
        old_clip = self._with_clip(surface, self._genre_clip_rect)

        for item, screen_x in self._iter_visible_scale_items(
            scale=state.genre_scale,
            display_position=state.genre_dial.display_position,
            margin=100,
        ):
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
        old_clip = self._with_clip(surface, self._station_clip_rect)

        self._draw_station_texture_ticks(surface, state)

        for item, screen_x in self._iter_visible_scale_items(
            scale=state.station_scale,
            display_position=state.station_dial.display_position,
            margin=180,
        ):
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

    def _iter_visible_scale_items(self, scale, display_position: float, margin: int):
        if not scale.items:
            return

        left_edge = layout.SCALE_LEFT - margin
        right_edge = layout.SCALE_RIGHT + margin
        period = scale.period if len(scale.items) > 1 else 0.0

        for item in scale.items:
            if period <= 0.0:
                logical_centers = (item.logical_center,)
            else:
                nearest_center = nearest_wrapped_position(item.logical_center, display_position, period)
                logical_centers = (
                    nearest_center - period,
                    nearest_center,
                    nearest_center + period,
                )

            for logical_center in logical_centers:
                screen_x = logical_to_screen_x(logical_center, display_position)
                if left_edge <= screen_x <= right_edge:
                    yield item, screen_x

    def _draw_station_texture_ticks(self, surface: pygame.Surface, state: UIState) -> None:
        offset = state.station_dial.display_position % 16
        offset_px = math.ceil(offset) % 16
        texture = self._get_station_texture_surface(offset_px)
        surface.blit(texture, self._station_clip_rect.topleft)

    def _get_station_texture_surface(self, offset_px: int) -> pygame.Surface:
        cached = self._station_texture_cache.get(offset_px)
        if cached is not None:
            return cached

        texture = pygame.Surface(self._station_clip_rect.size, pygame.SRCALPHA).convert_alpha()
        spacing = 16
        half_count = layout.SCALE_WIDTH // (2 * spacing) + 4

        short_top = layout.STATION_BASELINE_Y - 12
        medium_top = layout.STATION_BASELINE_Y - 18
        long_top = layout.STATION_BASELINE_Y - 24

        for i in range(-half_count, half_count + 1):
            tick_x = layout.CENTER_X + i * spacing - offset_px
            if not (self._station_clip_rect.left <= tick_x <= self._station_clip_rect.right):
                continue

            local_dx = abs(tick_x - layout.CENTER_X)
            local_x = int(tick_x) - self._station_clip_rect.left

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
                texture,
                color,
                (local_x, top - self._station_clip_rect.top),
                (local_x, layout.STATION_TICK_BOTTOM - self._station_clip_rect.top),
                width,
            )

        self._station_texture_cache[offset_px] = texture
        return texture

    def _blit_depth_overlay(self, surface: pygame.Surface, rect: pygame.Rect) -> None:
        overlay = self._get_depth_overlay(rect.size)
        surface.blit(overlay, rect.topleft)

    def _get_depth_overlay(self, size: tuple[int, int]) -> pygame.Surface:
        cached = self._depth_overlay_cache.get(size)
        if cached is not None:
            return cached

        width, height = size
        overlay = pygame.Surface(size, pygame.SRCALPHA).convert_alpha()

        max_edge_alpha = 210
        max_top_bottom_alpha = 70
        facet_alpha = 110
        facet_w = 42

        for x in range(width):
            nx = abs((x / max(1, width - 1)) * 2 - 1)
            alpha = int((nx ** 1.5) * max_edge_alpha)
            pygame.draw.line(
                overlay,
                (0, 0, 0, alpha),
                (x, 0),
                (x, height),
                1,
            )

        for y in range(height):
            ny = abs((y / max(1, height - 1)) * 2 - 1)
            alpha = int((ny ** 2.0) * max_top_bottom_alpha)
            pygame.draw.line(
                overlay,
                (0, 0, 0, alpha),
                (0, y),
                (width, y),
                1,
            )

        for x in range(facet_w):
            alpha = int((1 - x / max(1, facet_w)) * facet_alpha)
            pygame.draw.line(
                overlay,
                (0, 0, 0, alpha),
                (x, 0),
                (x, height),
                1,
            )
            pygame.draw.line(
                overlay,
                (0, 0, 0, alpha),
                (width - 1 - x, 0),
                (width - 1 - x, height),
                1,
            )

        pygame.draw.line(
            overlay,
            (36, 20, 10),
            (10, 6),
            (10, height - 6),
            1,
        )
        pygame.draw.line(
            overlay,
            (36, 20, 10),
            (width - 10, 6),
            (width - 10, height - 6),
            1,
        )

        self._depth_overlay_cache[size] = overlay
        return overlay

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
            text_surf = self.font_debug.render(line, True, theme.DEBUG)
            surface.blit(text_surf, (6, y))
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
        rendered = self._get_text_surface(
            text=text,
            font=font,
            color=color,
            max_width=max_width,
        )
        x = int(center_x - rendered.get_width() // 2)
        surface.blit(rendered, (x, y))

    def _get_text_surface(
        self,
        *,
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        max_width: int | None = None,
    ) -> pygame.Surface:
        cache_key = (id(font), text, color, max_width)
        cached = self._text_cache.get(cache_key)
        if cached is not None:
            return cached

        rendered_text = text
        if max_width is not None:
            rendered_text = self._fit_text(text, font, max_width)

        rendered = font.render(rendered_text, True, color)
        self._text_cache[cache_key] = rendered
        return rendered

    def _fit_text(self, text: str, font: pygame.font.Font, max_width: int) -> str:
        cache_key = (id(font), text, max_width)
        cached = self._fit_cache.get(cache_key)
        if cached is not None:
            return cached

        if font.size(text)[0] <= max_width:
            self._fit_cache[cache_key] = text
            return text

        suffix = "…"
        stripped = text
        while stripped:
            candidate = stripped + suffix
            if font.size(candidate)[0] <= max_width:
                self._fit_cache[cache_key] = candidate
                return candidate
            stripped = stripped[:-1]

        self._fit_cache[cache_key] = suffix
        return suffix
