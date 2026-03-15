#!/usr/bin/env python3
from __future__ import annotations

import struct
import threading
import time

import pygame

from config import load_config
from platform_runtime import create_display_backend

WINDOW_TITLE = "Pi Radio Touch Overlay Test"

DEVICE = "/dev/input/event5"

TOUCH_X_MIN = 380
TOUCH_X_MAX = 3730
TOUCH_Y_MIN = 355
TOUCH_Y_MAX = 3840

SCREEN_W = 480
SCREEN_H = 320

MOVE_THRESHOLD_PX = 4
GRID_STEP_PX = 4
CIRCLE_RADIUS = 14

EVENT_FORMAT = "llHHi"
EVENT_SIZE = struct.calcsize(EVENT_FORMAT)

EV_SYN = 0x00
EV_KEY = 0x01
EV_ABS = 0x03

SYN_REPORT = 0
BTN_TOUCH = 330
ABS_X = 0
ABS_Y = 1


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def map_range(v, in_min, in_max, out_min, out_max):
    if in_max == in_min:
        return out_min
    return int((v - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)


def quantize(v, step):
    if step <= 1:
        return v
    return int(round(v / step) * step)


def touch_to_screen(abs_x, abs_y):
    ax = clamp(abs_x, TOUCH_X_MIN, TOUCH_X_MAX)
    ay = clamp(abs_y, TOUCH_Y_MIN, TOUCH_Y_MAX)

    sx = map_range(ax, TOUCH_X_MIN, TOUCH_X_MAX, 0, SCREEN_W - 1)
    sy = map_range(ay, TOUCH_Y_MAX, TOUCH_Y_MIN, 0, SCREEN_H - 1)

    sx = clamp(quantize(sx, GRID_STEP_PX), 0, SCREEN_W - 1)
    sy = clamp(quantize(sy, GRID_STEP_PX), 0, SCREEN_H - 1)
    return sx, sy


class TouchState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.running = True
        self.touching = False
        self.x = SCREEN_W // 2
        self.y = SCREEN_H // 2

    def set_pos(self, touching: bool, x: int, y: int) -> None:
        with self.lock:
            self.touching = touching
            self.x = x
            self.y = y

    def snapshot(self):
        with self.lock:
            return self.touching, self.x, self.y


def touch_reader(state: TouchState) -> None:
    touching = False
    abs_x = None
    abs_y = None

    pending_touch = None
    pending_x = None
    pending_y = None

    last_reported_x = None
    last_reported_y = None

    with open(DEVICE, "rb", buffering=0) as f:
        while state.running:
            data = f.read(EVENT_SIZE)
            if len(data) != EVENT_SIZE:
                time.sleep(0.001)
                continue

            _, _, ev_type, ev_code, ev_value = struct.unpack(EVENT_FORMAT, data)

            if ev_type == EV_KEY and ev_code == BTN_TOUCH:
                pending_touch = bool(ev_value)
            elif ev_type == EV_ABS:
                if ev_code == ABS_X:
                    pending_x = ev_value
                elif ev_code == ABS_Y:
                    pending_y = ev_value
            elif ev_type == EV_SYN and ev_code == SYN_REPORT:
                changed = False

                if pending_touch is not None and pending_touch != touching:
                    touching = pending_touch
                    changed = True
                if pending_x is not None:
                    abs_x = pending_x
                    changed = True
                if pending_y is not None:
                    abs_y = pending_y
                    changed = True

                if changed and abs_x is not None and abs_y is not None:
                    sx, sy = touch_to_screen(abs_x, abs_y)

                    if touching:
                        if last_reported_x is None or last_reported_y is None:
                            state.set_pos(True, sx, sy)
                            last_reported_x, last_reported_y = sx, sy
                        else:
                            dx = abs(sx - last_reported_x)
                            dy = abs(sy - last_reported_y)
                            if dx >= MOVE_THRESHOLD_PX or dy >= MOVE_THRESHOLD_PX:
                                state.set_pos(True, sx, sy)
                                last_reported_x, last_reported_y = sx, sy
                    else:
                        state.set_pos(False, sx, sy)
                        last_reported_x = None
                        last_reported_y = None

                pending_touch = None
                pending_x = None
                pending_y = None


def bootstrap_display():
    config = load_config()
    pygame.init()
    pygame.mixer.quit()
    return create_display_backend(
        platform_config=config.platform,
        window_title=WINDOW_TITLE,
    )


def main() -> None:
    display_backend = bootstrap_display()
    surface = display_backend.surface

    font = pygame.font.SysFont("consolas", 20)
    clock = pygame.time.Clock()

    state = TouchState()
    thread = threading.Thread(target=touch_reader, args=(state,), daemon=True)
    thread.start()

    try:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    return

            touching, x, y = state.snapshot()

            surface.fill((0, 0, 0))
            pygame.draw.rect(surface, (40, 40, 40), (0, 0, SCREEN_W, SCREEN_H // 4), 1)
            pygame.draw.rect(surface, (40, 40, 40), (0, SCREEN_H * 3 // 4, SCREEN_W, SCREEN_H // 4), 1)

            surface.blit(font.render("TOP TOUCH ZONE", True, (120, 120, 120)), (12, 12))
            surface.blit(font.render("BOTTOM TOUCH ZONE", True, (120, 120, 120)), (12, SCREEN_H - 32))
            surface.blit(font.render(f"x={x} y={y} touching={touching}", True, (200, 200, 200)), (12, SCREEN_H // 2 - 10))

            color = (0, 255, 0) if touching else (80, 120, 80)
            pygame.draw.circle(surface, color, (x, y), CIRCLE_RADIUS)

            display_backend.present()
            clock.tick(30)
    finally:
        state.running = False
        display_backend.shutdown()
        pygame.quit()


if __name__ == "__main__":
    main()