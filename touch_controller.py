from __future__ import annotations

import layout
from app import drag_genre_by_pixels, drag_station_by_pixels
from state import UIState
from touch_debug import log_touch
from touch_input import TouchInputDevice, TouchSample


TOP_ZONE = "top"
BOTTOM_ZONE = "bottom"
IGNORED_ZONE = "ignored"


class TouchDragController:
    def __init__(
        self,
        touch_input: TouchInputDevice,
        drag_threshold_px: int = 4,
    ) -> None:
        self._touch_input = touch_input
        self._drag_threshold_px = max(0, drag_threshold_px)

        self._touch_active = False
        self._zone: str | None = None
        self._start_x = 0
        self._last_x = 0
        self._drag_started = False

    def poll_and_apply(self, state: UIState) -> None:
        for sample in self._touch_input.poll():
            self._apply_sample(sample, state)

    def shutdown(self) -> None:
        self._touch_input.close()

    def _apply_sample(self, sample: TouchSample, state: UIState) -> None:
        if sample.touching:
            if not self._touch_active:
                self._begin_touch(sample)
                return

            self._continue_touch(sample, state)
            return

        if self._touch_active:
            self._reset_gesture()

    def _begin_touch(self, sample: TouchSample) -> None:
        self._touch_active = True
        self._zone = self._classify_zone(sample.y)
        self._start_x = sample.x
        self._last_x = sample.x
        self._drag_started = False
        gesture_state = "ignored" if self._zone == IGNORED_ZONE else "active"
        log_touch(
            f"touch down: screen=({sample.x},{sample.y}) zone={self._zone} gesture={gesture_state}"
        )

    def _continue_touch(self, sample: TouchSample, state: UIState) -> None:
        if self._zone == IGNORED_ZONE:
            self._last_x = sample.x
            return

        if not self._drag_started:
            drag_distance = sample.x - self._start_x
            if abs(drag_distance) < self._drag_threshold_px:
                self._last_x = sample.x
                return

            self._drag_started = True
            self._apply_drag_delta(drag_distance, state)
            self._last_x = sample.x
            return

        drag_delta = sample.x - self._last_x
        if drag_delta == 0:
            return

        self._apply_drag_delta(drag_delta, state)
        self._last_x = sample.x

    def _apply_drag_delta(self, drag_delta: int, state: UIState) -> None:
        log_touch(f"touch drag accepted: zone={self._zone} dx={drag_delta}")
        if self._zone == TOP_ZONE:
            drag_genre_by_pixels(state, drag_delta)
        elif self._zone == BOTTOM_ZONE:
            drag_station_by_pixels(state, drag_delta)

    def _reset_gesture(self) -> None:
        log_touch(
            f"touch up: zone={self._zone} drag_started={self._drag_started}"
        )
        self._touch_active = False
        self._zone = None
        self._start_x = 0
        self._last_x = 0
        self._drag_started = False

    def _classify_zone(self, y: int) -> str:
        top_limit = layout.SCREEN_H // 4
        bottom_start = layout.SCREEN_H * 3 // 4

        if y < top_limit:
            return TOP_ZONE
        if y >= bottom_start:
            return BOTTOM_ZONE
        return IGNORED_ZONE
