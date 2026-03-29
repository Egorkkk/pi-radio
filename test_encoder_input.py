from __future__ import annotations

import unittest
from unittest.mock import patch

import encoder_input
from config import EncoderConfig
from encoder_input import GPIOEncoderInputDevice


class _FakeGPIO:
    BCM = "BCM"
    IN = "IN"
    PUD_UP = "PUD_UP"
    BOTH = "BOTH"

    def __init__(self, *, failing_pins: set[int]) -> None:
        self.failing_pins = set(failing_pins)
        self.added_event_detect: list[int] = []
        self.removed_event_detect: list[int] = []
        self.cleaned_up: list[tuple[int, ...]] = []
        self.mode: str | None = None

    def setmode(self, mode: str) -> None:
        self.mode = mode

    def setup(self, pin: int, mode: str, pull_up_down: str | None = None) -> None:
        _ = (pin, mode, pull_up_down)

    def input(self, pin: int) -> int:
        _ = pin
        return 0

    def add_event_detect(self, pin: int, edge: str, callback) -> None:
        _ = (edge, callback)
        if pin in self.failing_pins:
            raise RuntimeError(f"failed pin {pin}")
        self.added_event_detect.append(pin)

    def remove_event_detect(self, pin: int) -> None:
        self.removed_event_detect.append(pin)

    def cleanup(self, pins) -> None:
        self.cleaned_up.append(tuple(pins))


class EncoderInputPartialInitTests(unittest.TestCase):
    def test_failed_encoder_init_does_not_disable_other_encoder(self) -> None:
        genre_config = EncoderConfig(pin_a=17, pin_b=27)
        station_config = EncoderConfig(pin_a=22, pin_b=23)

        for failing_pin, expected_active in ((17, [22, 23]), (22, [17, 27])):
            fake_gpio = _FakeGPIO(failing_pins={failing_pin})
            with self.subTest(failing_pin=failing_pin):
                with patch.object(encoder_input, "_GPIO", fake_gpio):
                    device = GPIOEncoderInputDevice(
                        genre_config=genre_config,
                        station_config=station_config,
                    )
                    self.assertEqual(device._active_pins, expected_active)
                    self.assertEqual(device.poll(), ())
                    device.close()

            failed_pair = (17, 27) if failing_pin == 17 else (22, 23)
            self.assertIn(failed_pair, fake_gpio.cleaned_up)


if __name__ == "__main__":
    unittest.main()
