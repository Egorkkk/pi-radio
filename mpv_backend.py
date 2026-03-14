from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from config import MPVConfig
from playback_protocol import PlaybackSnapshot, PlaybackStatus


@dataclass(slots=True)
class MpvBackend:
    config: MPVConfig

    _process: subprocess.Popen[str] | None = None
    _current_station_id: Optional[str] = None
    _current_stream_url: Optional[str] = None

    _status: PlaybackStatus = PlaybackStatus.STOPPED
    _online: bool = True
    _error_message: Optional[str] = None

    _startup_deadline_monotonic: float = 0.0
    _reconnect_after_monotonic: float = 0.0
    _started: bool = False
    _paused: bool = False
    _log_path: Path = field(default_factory=lambda: Path("logs/mpv.log"))

    def start(self) -> None:
        self._started = True
        self._status = PlaybackStatus.STOPPED
        self._online = True
        self._error_message = None
        self._paused = False

    def stop(self) -> None:
        self._terminate_process()
        self._status = PlaybackStatus.STOPPED
        self._online = True
        self._error_message = None
        self._paused = False

    def play_station(self, station_id: str, stream_url: str) -> None:
        if not self._started:
            self.start()

        same_station = (
            station_id == self._current_station_id
            and stream_url == self._current_stream_url
            and self._process is not None
            and self._process.poll() is None
        )
        if same_station and self._status in (
            PlaybackStatus.BUFFERING,
            PlaybackStatus.PLAYING,
        ):
            return

        self._current_station_id = station_id
        self._current_stream_url = stream_url
        self._paused = False
        self._error_message = None
        self._online = True

        self._restart_process_for_current_station()

    def pause(self) -> None:
        # Для MVP не делаем настоящий pause через IPC.
        # Поведение максимально простое и безопасное: stop playback.
        if self._process is None:
            return

        self._paused = True
        self.stop()

    def resume(self) -> None:
        if not self._paused:
            return

        if self._current_station_id is None or self._current_stream_url is None:
            return

        self._paused = False
        self.play_station(
            station_id=self._current_station_id,
            stream_url=self._current_stream_url,
        )

    def shutdown(self) -> None:
        self._terminate_process()
        self._started = False
        self._status = PlaybackStatus.STOPPED
        self._online = True
        self._error_message = None
        self._paused = False

    def poll(self) -> PlaybackSnapshot:
        now = time.monotonic()

        if self._process is None:
            if (
                self._status == PlaybackStatus.ERROR
                and self._current_station_id is not None
                and self._current_stream_url is not None
                and not self._paused
                and now >= self._reconnect_after_monotonic
            ):
                self._restart_process_for_current_station()

            return self._snapshot()

        return_code = self._process.poll()

        if return_code is None:
            if (
                self._status == PlaybackStatus.BUFFERING
                and now >= self._startup_deadline_monotonic
            ):
                self._status = PlaybackStatus.PLAYING
                self._online = True
                self._error_message = None

            return self._snapshot()

        # Процесс завершился
        self._process = None

        if self._paused:
            self._status = PlaybackStatus.STOPPED
            self._online = True
            self._error_message = None
            return self._snapshot()

        self._status = PlaybackStatus.ERROR
        self._online = False
        self._error_message = (
            f"mpv exited with code {return_code} for station "
            f"'{self._current_station_id or 'unknown'}'. See {self._log_path}."
        )
        self._reconnect_after_monotonic = (
            now + max(self.config.reconnect_delay_seconds, 0.0)
        )

        return self._snapshot()

    def _restart_process_for_current_station(self) -> None:
        if self._current_station_id is None or self._current_stream_url is None:
            self._status = PlaybackStatus.ERROR
            self._online = False
            self._error_message = "No station selected for mpv playback."
            self._reconnect_after_monotonic = (
                time.monotonic() + max(self.config.reconnect_delay_seconds, 0.0)
            )
            return

        self._terminate_process()

        command = self._build_mpv_command(self._current_stream_url)
        log_handle = self._open_log_file()
        self._write_log_header(command)

        try:
            self._process = subprocess.Popen(
                command,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
            )
        except FileNotFoundError:
            if log_handle is not None:
                log_handle.close()
            self._process = None
            self._status = PlaybackStatus.ERROR
            self._online = False
            self._error_message = (
                f"mpv executable '{self.config.executable}' was not found."
            )
            self._append_log_line(self._error_message)
            self._reconnect_after_monotonic = (
                time.monotonic() + max(self.config.reconnect_delay_seconds, 0.0)
            )
            return
        except OSError as exc:
            if log_handle is not None:
                log_handle.close()
            self._process = None
            self._status = PlaybackStatus.ERROR
            self._online = False
            self._error_message = f"Failed to start mpv: {exc}"
            self._append_log_line(self._error_message)
            self._reconnect_after_monotonic = (
                time.monotonic() + max(self.config.reconnect_delay_seconds, 0.0)
            )
            return

        self._status = PlaybackStatus.BUFFERING
        self._online = True
        self._error_message = None
        self._startup_deadline_monotonic = (
            time.monotonic() + max(self.config.cache_seconds, 0.0)
        )

    def _build_mpv_command(self, stream_url: str) -> list[str]:
        command = [
            self.config.executable,
            "--no-video",
            "--force-window=no",
            "--msg-level=all=v",
            f"--audio-device={self.config.audio_device}",
            f"--cache-secs={self.config.cache_seconds}",
        ]

        if self.config.idle_mode:
            command.append("--idle=yes")
        else:
            command.append("--idle=no")

        command.extend(self.config.extra_args)
        command.append(stream_url)
        return command

    def _terminate_process(self) -> None:
        if self._process is None:
            return

        process = self._process
        self._process = None

        if process.poll() is None:
            try:
                process.terminate()
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2.0)
            except OSError as exc:
                self._append_log_line(f"Failed to terminate mpv cleanly: {exc}")
                return

        self._append_log_line(f"mpv process exited with code {process.returncode}")

    def _snapshot(self) -> PlaybackSnapshot:
        return PlaybackSnapshot(
            station_id=self._current_station_id,
            status=self._status,
            online=self._online,
            error_message=self._error_message,
        )

    def _open_log_file(self):
        try:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            return self._log_path.open("a", encoding="utf-8")
        except OSError as exc:
            self._append_log_line(f"Failed to open mpv log file {self._log_path}: {exc}")
            return None

    def _write_log_header(self, command: list[str]) -> None:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        self._append_log_line("")
        self._append_log_line(f"===== mpv launch {timestamp} =====")
        self._append_log_line(f"station_id={self._current_station_id}")
        self._append_log_line(f"stream_url={self._current_stream_url}")
        self._append_log_line(f"command={' '.join(command)}")

    def _append_log_line(self, line: str) -> None:
        try:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            with self._log_path.open("a", encoding="utf-8") as fh:
                fh.write(f"{line}\n")
        except OSError:
            pass
