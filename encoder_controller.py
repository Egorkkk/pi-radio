from __future__ import annotations

from collections import deque

from app import (
    move_genre_left,
    move_genre_right,
    move_station_left,
    move_station_right,
)
from config import EncoderConfig, EncodersConfig
from encoder_input import EncoderEvent, EncoderId, EncoderInputDevice
from state import UIState


class EncoderController:
    def __init__(
        self,
        encoder_input: EncoderInputDevice,
        config: EncodersConfig,
    ) -> None:
        self._encoder_input = encoder_input
        self._config = config
        self._last_accepted_event_time: dict[EncoderId, float | None] = {
            EncoderId.GENRE: None,
            EncoderId.STATION: None,
        }
        self._recent_detent_times: dict[EncoderId, deque[float]] = {
            EncoderId.GENRE: deque(),
            EncoderId.STATION: deque(),
        }

    def poll_and_apply(self, state: UIState) -> None:
        for event in self._encoder_input.poll():
            self._apply_event(event, state)

    def shutdown(self) -> None:
        self._encoder_input.close()

    def _apply_event(self, event: EncoderEvent, state: UIState) -> None:
        encoder_config = self._get_encoder_config(event.encoder_id)
        if event.detent_delta == 0:
            return

        if self._is_debounced(event, encoder_config):
            return

        self._last_accepted_event_time[event.encoder_id] = event.monotonic_time

        detent_delta = event.detent_delta
        if encoder_config.reverse_direction:
            detent_delta *= -1

        semantic_steps = abs(detent_delta) * encoder_config.steps_per_detent
        semantic_steps = self._apply_acceleration(
            encoder_id=event.encoder_id,
            detent_count=abs(event.detent_delta),
            event_time=event.monotonic_time,
            semantic_steps=semantic_steps,
        )
        semantic_steps = min(semantic_steps, self._config.tuning.max_steps_per_event)
        if semantic_steps <= 0:
            return

        if detent_delta > 0:
            self._apply_positive_direction(event.encoder_id, state, semantic_steps)
        else:
            self._apply_negative_direction(event.encoder_id, state, semantic_steps)

    def _is_debounced(self, event: EncoderEvent, config: EncoderConfig) -> bool:
        last_event_time = self._last_accepted_event_time[event.encoder_id]
        if last_event_time is None:
            return False

        minimum_interval_seconds = config.debounce_ms / 1000.0
        return (event.monotonic_time - last_event_time) < minimum_interval_seconds

    def _apply_acceleration(
        self,
        *,
        encoder_id: EncoderId,
        detent_count: int,
        event_time: float,
        semantic_steps: int,
    ) -> int:
        recent_times = self._recent_detent_times[encoder_id]
        window_seconds = self._config.tuning.fast_turn_window_ms / 1000.0

        while recent_times and (event_time - recent_times[0]) > window_seconds:
            recent_times.popleft()

        for _ in range(detent_count):
            recent_times.append(event_time)

        if not self._config.tuning.acceleration_enabled:
            return semantic_steps

        if len(recent_times) < self._config.tuning.fast_turn_threshold:
            return semantic_steps

        return semantic_steps * self._config.tuning.fast_turn_multiplier

    def _get_encoder_config(self, encoder_id: EncoderId) -> EncoderConfig:
        if encoder_id == EncoderId.GENRE:
            return self._config.genre
        return self._config.station

    def _apply_positive_direction(
        self,
        encoder_id: EncoderId,
        state: UIState,
        semantic_steps: int,
    ) -> None:
        if encoder_id == EncoderId.GENRE:
            for _ in range(semantic_steps):
                move_genre_right(state)
            return

        for _ in range(semantic_steps):
            move_station_right(state)

    def _apply_negative_direction(
        self,
        encoder_id: EncoderId,
        state: UIState,
        semantic_steps: int,
    ) -> None:
        if encoder_id == EncoderId.GENRE:
            for _ in range(semantic_steps):
                move_genre_left(state)
            return

        for _ in range(semantic_steps):
            move_station_left(state)
