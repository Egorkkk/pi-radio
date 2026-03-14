from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Set

from playback_protocol import PlaybackSnapshot, PlaybackStatus


@dataclass(slots=True)
class FakeBackend:
    startup_buffering_seconds: float = 0.6
    fail_station_ids: Set[str] = field(default_factory=set)
    fail_url_prefixes: tuple[str, ...] = ("error://", "fail://")

    _started: bool = False
    _current_station_id: Optional[str] = None
    _current_stream_url: Optional[str] = None
    _status: PlaybackStatus = PlaybackStatus.STOPPED
    _online: bool = True
    _error_message: Optional[str] = None
    _buffering_left: float = 0.0

    def start(self) -> None:
        self._started = True
        self._status = PlaybackStatus.STOPPED
        self._online = True
        self._error_message = None
        self._buffering_left = 0.0

    def stop(self) -> None:
        self._current_station_id = None
        self._current_stream_url = None
        self._status = PlaybackStatus.STOPPED
        self._online = True
        self._error_message = None
        self._buffering_left = 0.0

    def play_station(self, station_id: str, stream_url: str) -> None:
        if not self._started:
            self.start()

        self._current_station_id = station_id
        self._current_stream_url = stream_url

        if self._should_fail(station_id, stream_url):
            self._status = PlaybackStatus.ERROR
            self._online = False
            self._error_message = (
                f"Fake backend failed to start station '{station_id}'."
            )
            self._buffering_left = 0.0
            return

        self._status = PlaybackStatus.BUFFERING
        self._online = True
        self._error_message = None
        self._buffering_left = max(self.startup_buffering_seconds, 0.0)

    def pause(self) -> None:
        if self._status == PlaybackStatus.PLAYING:
            self._status = PlaybackStatus.STOPPED

    def resume(self) -> None:
        if self._current_station_id is None or self._current_stream_url is None:
            return

        if self._status == PlaybackStatus.STOPPED:
            self._status = PlaybackStatus.BUFFERING
            self._online = True
            self._error_message = None
            self._buffering_left = max(self.startup_buffering_seconds, 0.0)

    def shutdown(self) -> None:
        self.stop()
        self._started = False

    def poll(self) -> PlaybackSnapshot:
        if self._status == PlaybackStatus.BUFFERING:
            self._advance_buffering(0.1)

        return PlaybackSnapshot(
            station_id=self._current_station_id,
            status=self._status,
            online=self._online,
            error_message=self._error_message,
        )

    def tick(self, dt: float) -> None:
        if self._status == PlaybackStatus.BUFFERING:
            self._advance_buffering(dt)

    def _advance_buffering(self, dt: float) -> None:
        self._buffering_left -= max(dt, 0.0)
        if self._buffering_left <= 0.0:
            self._buffering_left = 0.0
            self._status = PlaybackStatus.PLAYING
            self._online = True
            self._error_message = None

    def _should_fail(self, station_id: str, stream_url: str) -> bool:
        if station_id in self.fail_station_ids:
            return True

        return any(stream_url.startswith(prefix) for prefix in self.fail_url_prefixes)