from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from config import load_config


class EncoderConfigTests(unittest.TestCase):
    def test_load_config_parses_encoder_settings(self) -> None:
        toml_text = """
[encoders]
enabled = true

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

        self.assertTrue(config.encoders.enabled)
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
[encoders]
enabled = true

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


if __name__ == "__main__":
    unittest.main()
