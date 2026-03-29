from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import tomllib


DEFAULT_SETTINGS_PATH = Path("settings.toml")


@dataclass(slots=True, frozen=True)
class DIFMConfig:
    username: str = ""
    password: str = ""
    listen_key: str = ""
    network: str = "di"
    stream_quality: str = "premium_high"
    request_timeout_seconds: float = 15.0
    channels_cache_file: Path = Path("cache/difm_channels.json")


@dataclass(slots=True, frozen=True)
class MPVConfig:
    executable: str = "mpv"
    audio_device: str = "auto"
    cache_seconds: float = 8.0
    reconnect_delay_seconds: float = 3.0
    idle_mode: bool = True
    extra_args: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class PlatformConfig:
    mode: str = "desktop"
    fullscreen: bool = False
    framebuffer_device: str = "/dev/fb0"
    width: int = 480
    height: int = 320
    fps: int = 60


@dataclass(slots=True, frozen=True)
class PersistenceConfig:
    state_file: Path = Path("runtime_state.json")
    save_on_station_change: bool = True


@dataclass(slots=True, frozen=True)
class InputConfig:
    keyboard_enabled: bool = True
    encoder_support_enabled: bool = False
    touch_support_enabled: bool = True
    station_hysteresis: float = 8.0
    volume_adc_enabled: bool = False
    power_switch_support_enabled: bool = False


@dataclass(slots=True, frozen=True)
class EncoderConfig:
    pin_a: int | None = None
    pin_b: int | None = None
    reverse_direction: bool = False
    steps_per_detent: int = 1
    debounce_ms: int = 2


@dataclass(slots=True, frozen=True)
class EncoderTuningConfig:
    acceleration_enabled: bool = True
    fast_turn_window_ms: int = 120
    fast_turn_threshold: int = 3
    fast_turn_multiplier: int = 2
    max_steps_per_event: int = 3


@dataclass(slots=True, frozen=True)
class EncodersConfig:
    genre: EncoderConfig = field(default_factory=EncoderConfig)
    station: EncoderConfig = field(default_factory=EncoderConfig)
    tuning: EncoderTuningConfig = field(default_factory=EncoderTuningConfig)


@dataclass(slots=True, frozen=True)
class AppConfig:
    difm: DIFMConfig = field(default_factory=DIFMConfig)
    mpv: MPVConfig = field(default_factory=MPVConfig)
    platform: PlatformConfig = field(default_factory=PlatformConfig)
    persistence: PersistenceConfig = field(default_factory=PersistenceConfig)
    input: InputConfig = field(default_factory=InputConfig)
    encoders: EncodersConfig = field(default_factory=EncodersConfig)


def load_config(path: str | Path = DEFAULT_SETTINGS_PATH) -> AppConfig:
    config_path = Path(path)

    if not config_path.exists():
        return AppConfig()

    with config_path.open("rb") as fh:
        raw = tomllib.load(fh)

    return AppConfig(
        difm=_load_difm_config(raw.get("difm", {})),
        mpv=_load_mpv_config(raw.get("mpv", {})),
        platform=_load_platform_config(raw.get("platform", {})),
        persistence=_load_persistence_config(raw.get("persistence", {})),
        input=_load_input_config(raw.get("input", {})),
        encoders=_load_encoders_config(raw.get("encoders", {})),
    )


def _load_difm_config(data: dict[str, Any]) -> DIFMConfig:
    return DIFMConfig(
        username=str(data.get("username", "")),
        password=str(data.get("password", "")),
        listen_key=str(data.get("listen_key", "")),
        network=str(data.get("network", "di")),
        stream_quality=str(data.get("stream_quality", "premium_high")),
        request_timeout_seconds=float(data.get("request_timeout_seconds", 15.0)),
        channels_cache_file=Path(
            str(data.get("channels_cache_file", "cache/difm_channels.json"))
        ),
    )


def _load_mpv_config(data: dict[str, Any]) -> MPVConfig:
    extra_args = data.get("extra_args", ())
    if isinstance(extra_args, list):
        extra_args_tuple = tuple(str(item) for item in extra_args)
    else:
        extra_args_tuple = ()

    return MPVConfig(
        executable=str(data.get("executable", "mpv")),
        audio_device=str(data.get("audio_device", "auto")),
        cache_seconds=float(data.get("cache_seconds", 8.0)),
        reconnect_delay_seconds=float(data.get("reconnect_delay_seconds", 3.0)),
        idle_mode=bool(data.get("idle_mode", True)),
        extra_args=extra_args_tuple,
    )


def _load_platform_config(data: dict[str, Any]) -> PlatformConfig:
    return PlatformConfig(
        mode=str(data.get("mode", "desktop")),
        fullscreen=bool(data.get("fullscreen", False)),
        framebuffer_device=str(data.get("framebuffer_device", "/dev/fb0")),
        width=int(data.get("width", 480)),
        height=int(data.get("height", 320)),
        fps=int(data.get("fps", 60)),
    )


def _load_persistence_config(data: dict[str, Any]) -> PersistenceConfig:
    return PersistenceConfig(
        state_file=Path(str(data.get("state_file", "runtime_state.json"))),
        save_on_station_change=bool(data.get("save_on_station_change", True)),
    )


def _load_input_config(data: dict[str, Any]) -> InputConfig:
    return InputConfig(
        keyboard_enabled=bool(data.get("keyboard_enabled", True)),
        encoder_support_enabled=bool(data.get("encoder_support_enabled", False)),
        touch_support_enabled=bool(data.get("touch_support_enabled", False)),
        station_hysteresis=float(data.get("station_hysteresis", 8.0)),
        volume_adc_enabled=bool(data.get("volume_adc_enabled", False)),
        power_switch_support_enabled=bool(
            data.get("power_switch_support_enabled", False)
        ),
    )


def _load_encoder_config(data: dict[str, Any]) -> EncoderConfig:
    pin_a = _load_optional_int(data, "pin_a")
    pin_b = _load_optional_int(data, "pin_b")
    steps_per_detent = _load_int_with_minimum(data, "steps_per_detent", 1, 1)
    debounce_ms = _load_int_with_minimum(data, "debounce_ms", 2, 0)

    return EncoderConfig(
        pin_a=pin_a,
        pin_b=pin_b,
        reverse_direction=bool(data.get("reverse_direction", False)),
        steps_per_detent=steps_per_detent,
        debounce_ms=debounce_ms,
    )


def _load_encoder_tuning_config(data: dict[str, Any]) -> EncoderTuningConfig:
    return EncoderTuningConfig(
        acceleration_enabled=bool(data.get("acceleration_enabled", True)),
        fast_turn_window_ms=_load_int_with_minimum(
            data, "fast_turn_window_ms", 120, 0
        ),
        fast_turn_threshold=_load_int_with_minimum(
            data, "fast_turn_threshold", 3, 1
        ),
        fast_turn_multiplier=_load_int_with_minimum(
            data, "fast_turn_multiplier", 2, 1
        ),
        max_steps_per_event=_load_int_with_minimum(
            data, "max_steps_per_event", 3, 1
        ),
    )


def _load_encoders_config(data: dict[str, Any]) -> EncodersConfig:
    return EncodersConfig(
        genre=_load_encoder_config(data.get("genre", {})),
        station=_load_encoder_config(data.get("station", {})),
        tuning=_load_encoder_tuning_config(data.get("tuning", {})),
    )


def _load_optional_int(data: dict[str, Any], key: str) -> int | None:
    raw_value = data.get(key)
    if raw_value is None:
        return None
    return int(raw_value)


def _load_int_with_minimum(
    data: dict[str, Any],
    key: str,
    default: int,
    minimum: int,
) -> int:
    value = int(data.get(key, default))
    if value < minimum:
        raise ValueError(f"{key} must be >= {minimum}")
    return value
