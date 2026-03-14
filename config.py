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
    network: str = "di"
    stream_quality: str = "premium"
    request_timeout_seconds: float = 15.0


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
    touch_support_enabled: bool = False
    volume_adc_enabled: bool = False
    power_switch_support_enabled: bool = False


@dataclass(slots=True, frozen=True)
class AppConfig:
    difm: DIFMConfig = field(default_factory=DIFMConfig)
    mpv: MPVConfig = field(default_factory=MPVConfig)
    platform: PlatformConfig = field(default_factory=PlatformConfig)
    persistence: PersistenceConfig = field(default_factory=PersistenceConfig)
    input: InputConfig = field(default_factory=InputConfig)


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
    )


def _load_difm_config(data: dict[str, Any]) -> DIFMConfig:
    return DIFMConfig(
        username=str(data.get("username", "")),
        password=str(data.get("password", "")),
        network=str(data.get("network", "di")),
        stream_quality=str(data.get("stream_quality", "premium")),
        request_timeout_seconds=float(data.get("request_timeout_seconds", 15.0)),
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
        volume_adc_enabled=bool(data.get("volume_adc_enabled", False)),
        power_switch_support_enabled=bool(
            data.get("power_switch_support_enabled", False)
        ),
    )