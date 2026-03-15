#!/usr/bin/env python3
import struct
import time

DEVICE = "/dev/input/event5"

TOUCH_X_MIN = 380
TOUCH_X_MAX = 3730
TOUCH_Y_MIN = 355
TOUCH_Y_MAX = 3840

SCREEN_W = 480
SCREEN_H = 320

# Фильтрация для теста
MOVE_THRESHOLD_PX = 6   # игнорировать сдвиги меньше этого порога
GRID_STEP_PX = 8        # округлять координаты к сетке; 1 = без округления

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

    sx = clamp(sx, 0, SCREEN_W - 1)
    sy = clamp(sy, 0, SCREEN_H - 1)

    sx = quantize(sx, GRID_STEP_PX)
    sy = quantize(sy, GRID_STEP_PX)

    sx = clamp(sx, 0, SCREEN_W - 1)
    sy = clamp(sy, 0, SCREEN_H - 1)

    return sx, sy


def main():
    print(f"Opening {DEVICE}")
    print("Press Ctrl+C to stop.\n")

    touching = False
    abs_x = None
    abs_y = None

    pending_touch = None
    pending_x = None
    pending_y = None

    last_reported_x = None
    last_reported_y = None

    with open(DEVICE, "rb", buffering=0) as f:
        while True:
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
                        is_new_press = (pending_touch is not None and pending_touch is True)

                        if is_new_press:
                            print(f"DOWN {sx:3d} {sy:3d}    raw=({abs_x:4d}, {abs_y:4d})")
                            last_reported_x = sx
                            last_reported_y = sy
                        else:
                            if last_reported_x is None or last_reported_y is None:
                                print(f"MOVE {sx:3d} {sy:3d}    raw=({abs_x:4d}, {abs_y:4d})")
                                last_reported_x = sx
                                last_reported_y = sy
                            else:
                                dx = abs(sx - last_reported_x)
                                dy = abs(sy - last_reported_y)

                                if dx >= MOVE_THRESHOLD_PX or dy >= MOVE_THRESHOLD_PX:
                                    print(f"MOVE {sx:3d} {sy:3d}    raw=({abs_x:4d}, {abs_y:4d})")
                                    last_reported_x = sx
                                    last_reported_y = sy
                    else:
                        if pending_touch is not None and pending_touch is False:
                            print(f"UP   {sx:3d} {sy:3d}    raw=({abs_x:4d}, {abs_y:4d})")
                            last_reported_x = None
                            last_reported_y = None

                pending_touch = None
                pending_x = None
                pending_y = None


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")