from __future__ import annotations

import inspect
import unittest
from unittest.mock import patch

import encoder_input
from config import EncoderConfig, EncodersConfig, EncoderTuningConfig
from encoder_controller import EncoderController
from encoder_input import EncoderEvent, EncoderId


class _FakeEncoderInputDevice:
    def __init__(self, events: tuple[EncoderEvent, ...]) -> None:
        self._events = events
        self.closed = False

    def poll(self) -> tuple[EncoderEvent, ...]:
        events = self._events
        self._events = ()
        return events

    def close(self) -> None:
        self.closed = True


class _DummyState:
    def __init__(self) -> None:
        self.calls: list[str] = []


class EncoderControllerTests(unittest.TestCase):
    def test_low_level_adapter_has_no_ui_state_dependency(self) -> None:
        source = inspect.getsource(encoder_input)
        self.assertNotIn("UIState", source)

    def test_no_visible_change_occurs_before_poll_and_apply(self) -> None:
        state = _DummyState()
        controller = self._build_controller(
            events=(
                EncoderEvent(
                    encoder_id=EncoderId.GENRE,
                    detent_delta=1,
                    monotonic_time=1.0,
                ),
            )
        )

        with self._patch_move_functions():
            self.assertEqual(state.calls, [])
            controller.poll_and_apply(state)

        self.assertEqual(state.calls, ["genre_right"])

    def test_debounce_suppresses_repeated_events(self) -> None:
        state = _DummyState()
        controller = self._build_controller(
            events=(
                EncoderEvent(EncoderId.GENRE, 1, 1.000),
                EncoderEvent(EncoderId.GENRE, 1, 1.001),
            ),
            genre_config=EncoderConfig(
                pin_a=17,
                pin_b=27,
                debounce_ms=10,
            ),
        )

        with self._patch_move_functions():
            controller.poll_and_apply(state)

        self.assertEqual(state.calls, ["genre_right"])

    def test_reverse_direction_flips_semantic_dispatch(self) -> None:
        state = _DummyState()
        controller = self._build_controller(
            events=(
                EncoderEvent(EncoderId.GENRE, 1, 1.0),
            ),
            genre_config=EncoderConfig(
                pin_a=17,
                pin_b=27,
                reverse_direction=True,
            ),
        )

        with self._patch_move_functions():
            controller.poll_and_apply(state)

        self.assertEqual(state.calls, ["genre_left"])

    def test_fast_turn_acceleration_increases_move_count(self) -> None:
        state = _DummyState()
        controller = self._build_controller(
            events=(
                EncoderEvent(EncoderId.GENRE, 1, 1.000),
                EncoderEvent(EncoderId.GENRE, 1, 1.030),
                EncoderEvent(EncoderId.GENRE, 1, 1.060),
            ),
            tuning=EncoderTuningConfig(
                acceleration_enabled=True,
                fast_turn_window_ms=120,
                fast_turn_threshold=3,
                fast_turn_multiplier=2,
                max_steps_per_event=10,
            ),
        )

        with self._patch_move_functions():
            controller.poll_and_apply(state)

        self.assertEqual(state.calls, ["genre_right"] * 4)

    def test_steps_per_detent_replays_existing_move_function_multiple_times(self) -> None:
        state = _DummyState()
        controller = self._build_controller(
            events=(
                EncoderEvent(EncoderId.STATION, 1, 1.0),
            ),
            station_config=EncoderConfig(
                pin_a=22,
                pin_b=23,
                steps_per_detent=2,
            ),
        )

        with self._patch_move_functions():
            controller.poll_and_apply(state)

        self.assertEqual(state.calls, ["station_right", "station_right"])

    def test_cap_limits_per_event_movement_after_acceleration(self) -> None:
        state = _DummyState()
        controller = self._build_controller(
            events=(
                EncoderEvent(EncoderId.STATION, 1, 1.0),
            ),
            station_config=EncoderConfig(
                pin_a=22,
                pin_b=23,
                steps_per_detent=3,
            ),
            tuning=EncoderTuningConfig(
                acceleration_enabled=True,
                fast_turn_window_ms=120,
                fast_turn_threshold=1,
                fast_turn_multiplier=2,
                max_steps_per_event=4,
            ),
        )

        with self._patch_move_functions():
            controller.poll_and_apply(state)

        self.assertEqual(state.calls, ["station_right"] * 4)

    def test_negative_station_event_dispatches_to_station_left(self) -> None:
        state = _DummyState()
        controller = self._build_controller(
            events=(
                EncoderEvent(EncoderId.STATION, -1, 1.0),
            )
        )

        with self._patch_move_functions():
            controller.poll_and_apply(state)

        self.assertEqual(state.calls, ["station_left"])

    def test_shutdown_closes_input_device(self) -> None:
        device = _FakeEncoderInputDevice(())
        controller = EncoderController(
            encoder_input=device,
            config=self._build_config(),
        )

        controller.shutdown()

        self.assertTrue(device.closed)

    def _build_controller(
        self,
        *,
        events: tuple[EncoderEvent, ...],
        genre_config: EncoderConfig | None = None,
        station_config: EncoderConfig | None = None,
        tuning: EncoderTuningConfig | None = None,
    ) -> EncoderController:
        return EncoderController(
            encoder_input=_FakeEncoderInputDevice(events),
            config=self._build_config(
                genre_config=genre_config,
                station_config=station_config,
                tuning=tuning,
            ),
        )

    def _build_config(
        self,
        *,
        genre_config: EncoderConfig | None = None,
        station_config: EncoderConfig | None = None,
        tuning: EncoderTuningConfig | None = None,
    ) -> EncodersConfig:
        return EncodersConfig(
            genre=genre_config or EncoderConfig(pin_a=17, pin_b=27),
            station=station_config or EncoderConfig(pin_a=22, pin_b=23),
            tuning=tuning or EncoderTuningConfig(),
        )

    def _patch_move_functions(self):
        return patch.multiple(
            "encoder_controller",
            move_genre_left=lambda state: state.calls.append("genre_left"),
            move_genre_right=lambda state: state.calls.append("genre_right"),
            move_station_left=lambda state: state.calls.append("station_left"),
            move_station_right=lambda state: state.calls.append("station_right"),
        )


if __name__ == "__main__":
    unittest.main()
