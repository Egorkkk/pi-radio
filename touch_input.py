from __future__ import annotations

import os
import select
import struct
from dataclasses import dataclass

import layout
from touch_debug import log_touch, log_touch_raw


DEFAULT_TOUCH_DEVICE = "/dev/input/event5"

TOUCH_X_MIN = 380
TOUCH_X_MAX = 3730
TOUCH_Y_MIN = 355
TOUCH_Y_MAX = 3840

EVENT_FORMAT = "llHHi"
EVENT_SIZE = struct.calcsize(EVENT_FORMAT)
READ_CHUNK_SIZE = EVENT_SIZE * 32

EV_SYN = 0x00
EV_KEY = 0x01
EV_ABS = 0x03

SYN_REPORT = 0
BTN_TOUCH = 330
ABS_X = 0
ABS_Y = 1


@dataclass(slots=True, frozen=True)
class TouchSample:
    touching: bool
    x: int
    y: int


class TouchInputDevice:
    def __init__(self, device_path: str = DEFAULT_TOUCH_DEVICE) -> None:
        self.device_path = device_path
        self._fd = os.open(device_path, os.O_RDONLY | os.O_NONBLOCK)
        self._buffer = bytearray()

        self._touching = False
        self._abs_x: int | None = None
        self._abs_y: int | None = None

        self._pending_touch: bool | None = None
        self._pending_x: int | None = None
        self._pending_y: int | None = None

    def close(self) -> None:
        if self._fd < 0:
            return

        os.close(self._fd)
        self._fd = -1

    def poll(self) -> tuple[TouchSample, ...]:
        if self._fd < 0:
            return ()

        samples: list[TouchSample] = []

        while True:
            readable, _, _ = select.select([self._fd], [], [], 0.0)
            if not readable:
                break

            try:
                chunk = os.read(self._fd, READ_CHUNK_SIZE)
            except BlockingIOError:
                break

            if not chunk:
                break

            log_touch(
                f"touch input read: device={self.device_path} events={len(chunk) // EVENT_SIZE}"
            )
            self._buffer.extend(chunk)

            while len(self._buffer) >= EVENT_SIZE:
                event_bytes = self._buffer[:EVENT_SIZE]
                del self._buffer[:EVENT_SIZE]

                _, _, ev_type, ev_code, ev_value = struct.unpack(EVENT_FORMAT, event_bytes)
                sample = self._process_event(ev_type, ev_code, ev_value)
                if sample is not None:
                    samples.append(sample)

        return tuple(samples)

    def _process_event(self, ev_type: int, ev_code: int, ev_value: int) -> TouchSample | None:
        if ev_type == EV_KEY and ev_code == BTN_TOUCH:
            log_touch_raw(f"BTN_TOUCH value={ev_value}")
            self._pending_touch = bool(ev_value)
            return None

        if ev_type == EV_ABS:
            if ev_code == ABS_X:
                log_touch_raw(f"ABS_X value={ev_value}")
                self._pending_x = ev_value
            elif ev_code == ABS_Y:
                log_touch_raw(f"ABS_Y value={ev_value}")
                self._pending_y = ev_value
            return None

        if ev_type != EV_SYN or ev_code != SYN_REPORT:
            return None

        log_touch_raw("SYN_REPORT")

        changed = False

        if self._pending_touch is not None and self._pending_touch != self._touching:
            self._touching = self._pending_touch
            changed = True

        if self._pending_x is not None:
            self._abs_x = self._pending_x
            changed = True

        if self._pending_y is not None:
            self._abs_y = self._pending_y
            changed = True

        self._pending_touch = None
        self._pending_x = None
        self._pending_y = None

        if not changed or self._abs_x is None or self._abs_y is None:
            return None

        x, y = normalize_touch(self._abs_x, self._abs_y)
        log_touch(
            f"touch sample emitted: touching={self._touching} abs=({self._abs_x},{self._abs_y}) screen=({x},{y})"
        )
        return TouchSample(touching=self._touching, x=x, y=y)


def normalize_touch(abs_x: int, abs_y: int) -> tuple[int, int]:
    clamped_x = _clamp(abs_x, TOUCH_X_MIN, TOUCH_X_MAX)
    clamped_y = _clamp(abs_y, TOUCH_Y_MIN, TOUCH_Y_MAX)

    screen_x = _map_range(clamped_x, TOUCH_X_MIN, TOUCH_X_MAX, 0, layout.SCREEN_W - 1)
    screen_y = _map_range(clamped_y, TOUCH_Y_MAX, TOUCH_Y_MIN, 0, layout.SCREEN_H - 1)

    return (
        _clamp(screen_x, 0, layout.SCREEN_W - 1),
        _clamp(screen_y, 0, layout.SCREEN_H - 1),
    )


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def _map_range(
    value: int,
    input_min: int,
    input_max: int,
    output_min: int,
    output_max: int,
) -> int:
    if input_max == input_min:
        return output_min

    return int(
        (value - input_min) * (output_max - output_min) / (input_max - input_min)
        + output_min
    )
