from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from queue import Empty, Queue
from threading import Lock
from time import monotonic
from typing import Callable, Protocol

from config import EncoderConfig

try:
    import RPi.GPIO as _GPIO
except ImportError:  # pragma: no cover - exercised via bootstrap fallback tests instead.
    _GPIO = None


_TRANSITION_DELTAS = {
    (0, 1): 1,
    (1, 3): 1,
    (3, 2): 1,
    (2, 0): 1,
    (1, 0): -1,
    (3, 1): -1,
    (2, 3): -1,
    (0, 2): -1,
}
_STEPS_PER_DETENT = 4


class EncoderId(str, Enum):
    GENRE = "genre"
    STATION = "station"


@dataclass(slots=True, frozen=True)
class EncoderEvent:
    encoder_id: EncoderId
    detent_delta: int
    monotonic_time: float


class EncoderInputDevice(Protocol):
    def poll(self) -> tuple[EncoderEvent, ...]:
        ...

    def close(self) -> None:
        ...


@dataclass(slots=True)
class _EncoderChannel:
    encoder_id: EncoderId
    pin_a: int
    pin_b: int
    last_state: int
    transition_accumulator: int = 0


class GPIOEncoderInputDevice:
    def __init__(
        self,
        genre_config: EncoderConfig,
        station_config: EncoderConfig,
        *,
        time_source: Callable[[], float] = monotonic,
    ) -> None:
        if _GPIO is None:
            raise RuntimeError("RPi.GPIO is not available")

        self._gpio = _GPIO
        self._time_source = time_source
        self._queue: Queue[EncoderEvent] = Queue()
        self._error_lock = Lock()
        self._callback_error: Exception | None = None
        self._channels_by_pin: dict[int, _EncoderChannel] = {}
        self._active_pins: list[int] = []
        self._registered_encoders: set[EncoderId] = set()
        self._closed = False

        self._gpio.setmode(self._gpio.BCM)

        self._register_encoder(EncoderId.GENRE, genre_config)
        self._register_encoder(EncoderId.STATION, station_config)
        if not self._registered_encoders:
            raise RuntimeError("no encoder inputs could be initialized")

    def poll(self) -> tuple[EncoderEvent, ...]:
        self._raise_callback_error_if_any()

        events: list[EncoderEvent] = []
        while True:
            try:
                events.append(self._queue.get_nowait())
            except Empty:
                break

        self._raise_callback_error_if_any()
        return tuple(events)

    def close(self) -> None:
        if self._closed:
            return

        self._closed = True
        for pin in self._active_pins:
            try:
                self._gpio.remove_event_detect(pin)
            except RuntimeError:
                pass

        if self._active_pins:
            self._gpio.cleanup(tuple(self._active_pins))

        self._active_pins.clear()
        self._channels_by_pin.clear()

    def _register_encoder(self, encoder_id: EncoderId, config: EncoderConfig) -> None:
        if config.pin_a is None or config.pin_b is None:
            return

        pin_a = int(config.pin_a)
        pin_b = int(config.pin_b)
        if pin_a in self._channels_by_pin or pin_b in self._channels_by_pin:
            print(
                f"[pi-radio] Encoder '{encoder_id.value}' disabled: pin mapping conflicts with another encoder."
            )
            return

        try:
            self._gpio.setup(pin_a, self._gpio.IN, pull_up_down=self._gpio.PUD_UP)
            self._gpio.setup(pin_b, self._gpio.IN, pull_up_down=self._gpio.PUD_UP)

            channel = _EncoderChannel(
                encoder_id=encoder_id,
                pin_a=pin_a,
                pin_b=pin_b,
                last_state=self._read_state(pin_a, pin_b),
            )

            self._channels_by_pin[pin_a] = channel
            self._channels_by_pin[pin_b] = channel
            self._active_pins.extend((pin_a, pin_b))

            self._gpio.add_event_detect(
                pin_a,
                self._gpio.BOTH,
                callback=self._handle_gpio_edge,
            )
            self._gpio.add_event_detect(
                pin_b,
                self._gpio.BOTH,
                callback=self._handle_gpio_edge,
            )
        except Exception as exc:
            self._cleanup_encoder_resources(pin_a, pin_b)
            print(f"[pi-radio] Encoder '{encoder_id.value}' disabled: {exc}")
            return

        self._registered_encoders.add(encoder_id)

    def _handle_gpio_edge(self, pin: int) -> None:
        if self._closed:
            return

        try:
            channel = self._channels_by_pin.get(pin)
            if channel is None:
                return

            current_state = self._read_state(channel.pin_a, channel.pin_b)
            transition_delta = _TRANSITION_DELTAS.get((channel.last_state, current_state), 0)
            channel.last_state = current_state

            if transition_delta == 0:
                return

            channel.transition_accumulator += transition_delta
            if abs(channel.transition_accumulator) < _STEPS_PER_DETENT:
                return

            detent_delta = int(channel.transition_accumulator / _STEPS_PER_DETENT)
            channel.transition_accumulator -= detent_delta * _STEPS_PER_DETENT
            self._queue.put(
                EncoderEvent(
                    encoder_id=channel.encoder_id,
                    detent_delta=detent_delta,
                    monotonic_time=self._time_source(),
                )
            )
        except Exception as exc:  # pragma: no cover - hardware callback path.
            with self._error_lock:
                if self._callback_error is None:
                    self._callback_error = exc

    def _read_state(self, pin_a: int, pin_b: int) -> int:
        a_state = 1 if self._gpio.input(pin_a) else 0
        b_state = 1 if self._gpio.input(pin_b) else 0
        return (a_state << 1) | b_state

    def _raise_callback_error_if_any(self) -> None:
        with self._error_lock:
            if self._callback_error is None:
                return
            error = self._callback_error
            self._callback_error = None

        raise RuntimeError(f"encoder GPIO callback failed: {error}") from error

    def _cleanup_encoder_resources(self, pin_a: int, pin_b: int) -> None:
        for pin in (pin_a, pin_b):
            try:
                self._gpio.remove_event_detect(pin)
            except RuntimeError:
                pass

            self._channels_by_pin.pop(pin, None)
            while pin in self._active_pins:
                self._active_pins.remove(pin)

        try:
            self._gpio.cleanup((pin_a, pin_b))
        except RuntimeError:
            pass
