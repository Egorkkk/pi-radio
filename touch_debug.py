from __future__ import annotations

import os
import time
from pathlib import Path


TOUCH_DEBUG_ENV = "PI_RADIO_TOUCH_DEBUG"
TOUCH_DEBUG_RAW_ENV = "PI_RADIO_TOUCH_DEBUG_RAW"
TOUCH_LOG_PATH = Path("logs/touch.log")


def touch_debug_enabled() -> bool:
    return _env_flag(TOUCH_DEBUG_ENV)


def touch_raw_debug_enabled() -> bool:
    return touch_debug_enabled() and _env_flag(TOUCH_DEBUG_RAW_ENV)


def touch_log_path() -> Path:
    return TOUCH_LOG_PATH


def log_touch(message: str) -> None:
    if not touch_debug_enabled():
        return

    _append_log_line(message)


def log_touch_raw(message: str) -> None:
    if not touch_raw_debug_enabled():
        return

    _append_log_line(f"[raw] {message}")


def log_touch_session_start() -> None:
    if not touch_debug_enabled():
        return

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    _append_log_line("")
    _append_log_line(f"===== touch debug start {timestamp} =====")
    _append_log_line(f"log_path={TOUCH_LOG_PATH} append=true raw_enabled={touch_raw_debug_enabled()}")


def _append_log_line(message: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    try:
        TOUCH_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with TOUCH_LOG_PATH.open("a", encoding="utf-8") as fh:
            fh.write(f"{timestamp} {message}\n")
    except OSError:
        pass


def _env_flag(name: str) -> bool:
    value = os.getenv(name, "")
    return value.lower() not in {"", "0", "false", "no", "off"}
