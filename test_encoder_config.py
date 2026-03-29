from __future__ import annotations

import importlib
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import app as app_module
from config import AppConfig, EncoderConfig, EncodersConfig, InputConfig, load_config
from state import UIState


class EncoderConfigTests(unittest.TestCase):
    def test_load_config_parses_encoder_settings(self) -> None:
        toml_text = """
[input]
encoder_support_enabled = true
station_hysteresis = 12.5

[encoders.genre]
pin_a = 17
pin_b = 27
reverse_direction = true
steps_per_detent = 2
debounce_ms = 5

[encoders.station]
pin_a = 22
pin_b = 23
reverse_direction = false
steps_per_detent = 3
debounce_ms = 4

[encoders.tuning]
acceleration_enabled = false
fast_turn_window_ms = 150
fast_turn_threshold = 4
fast_turn_multiplier = 3
max_steps_per_event = 5
"""

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.toml"
            config_path.write_text(toml_text, encoding="utf-8")

            config = load_config(config_path)

        self.assertTrue(config.input.encoder_support_enabled)
        self.assertEqual(config.input.station_hysteresis, 12.5)
        self.assertEqual(config.encoders.genre.pin_a, 17)
        self.assertEqual(config.encoders.genre.pin_b, 27)
        self.assertTrue(config.encoders.genre.reverse_direction)
        self.assertEqual(config.encoders.genre.steps_per_detent, 2)
        self.assertEqual(config.encoders.genre.debounce_ms, 5)
        self.assertEqual(config.encoders.station.pin_a, 22)
        self.assertEqual(config.encoders.station.pin_b, 23)
        self.assertEqual(config.encoders.station.steps_per_detent, 3)
        self.assertFalse(config.encoders.tuning.acceleration_enabled)
        self.assertEqual(config.encoders.tuning.fast_turn_window_ms, 150)
        self.assertEqual(config.encoders.tuning.fast_turn_threshold, 4)
        self.assertEqual(config.encoders.tuning.fast_turn_multiplier, 3)
        self.assertEqual(config.encoders.tuning.max_steps_per_event, 5)

    def test_load_config_rejects_invalid_encoder_numeric_values(self) -> None:
        toml_text = """
[encoders.genre]
pin_a = 17
pin_b = 27
steps_per_detent = 0
"""

        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.toml"
            config_path.write_text(toml_text, encoding="utf-8")

            with self.assertRaises(ValueError):
                load_config(config_path)


class EncoderBootstrapFlagTests(unittest.TestCase):
    def test_bootstrap_skips_when_input_encoder_flag_is_disabled(self) -> None:
        main_module = self._import_main_module()
        config = AppConfig(
            input=InputConfig(encoder_support_enabled=False),
            encoders=EncodersConfig(
                genre=EncoderConfig(pin_a=17, pin_b=27),
                station=EncoderConfig(pin_a=22, pin_b=23),
            ),
        )

        with patch.object(main_module, "GPIOEncoderInputDevice") as gpio_input_class:
            result = main_module.bootstrap_encoder_controller(config)

        self.assertIsNone(result)
        gpio_input_class.assert_not_called()

    def test_bootstrap_uses_input_encoder_flag_as_single_source_of_truth(self) -> None:
        main_module = self._import_main_module()
        config = AppConfig(
            input=InputConfig(encoder_support_enabled=True),
            encoders=EncodersConfig(
                genre=EncoderConfig(pin_a=17, pin_b=27),
                station=EncoderConfig(pin_a=22, pin_b=23),
            ),
        )
        fake_encoder_input = object()
        fake_controller = object()

        with patch.object(
            main_module,
            "GPIOEncoderInputDevice",
            return_value=fake_encoder_input,
        ) as gpio_input_class, patch.object(
            main_module,
            "EncoderController",
            return_value=fake_controller,
        ) as controller_class:
            result = main_module.bootstrap_encoder_controller(config)

        self.assertIs(result, fake_controller)
        gpio_input_class.assert_called_once_with(
            genre_config=config.encoders.genre,
            station_config=config.encoders.station,
        )
        controller_class.assert_called_once_with(
            encoder_input=fake_encoder_input,
            config=config.encoders,
        )

    def _import_main_module(self):
        fake_pygame = types.SimpleNamespace()
        with patch.dict(sys.modules, {"pygame": fake_pygame}):
            sys.modules.pop("main", None)
            return importlib.import_module("main")


class StationHysteresisConfigTests(unittest.TestCase):
    def test_update_state_uses_configured_station_hysteresis_argument(self) -> None:
        state = UIState()
        observed_hysteresis: list[float] = []
        original_update_dial = app_module.update_dial

        def fake_update_dial(*args, **kwargs):
            if kwargs.get("dial") is state.station_dial:
                observed_hysteresis.append(kwargs["hysteresis"])

        with patch.object(app_module, "update_dial", side_effect=fake_update_dial):
            app_module.update_state(state, 0.016, station_hysteresis=12.5)

        self.assertEqual(observed_hysteresis, [12.5])


if __name__ == "__main__":
    unittest.main()
