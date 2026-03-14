from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Protocol


class PlaybackStatus(str, Enum):
    STOPPED = "stopped"
    BUFFERING = "buffering"
    PLAYING = "playing"
    ERROR = "error"


@dataclass(slots=True, frozen=True)
class PlaybackSnapshot:
    station_id: Optional[str]
    status: PlaybackStatus
    online: bool
    error_message: Optional[str] = None

    @property
    def is_playing(self) -> bool:
        return self.status == PlaybackStatus.PLAYING

    @property
    def is_error(self) -> bool:
        return self.status == PlaybackStatus.ERROR


class PlaybackBackend(Protocol):
    def start(self) -> None:
        """Initialize backend resources if needed."""

    def stop(self) -> None:
        """Stop playback but keep backend ready for reuse."""

    def play_station(self, station_id: str, stream_url: str) -> None:
        """Start playback for the given station."""

    def pause(self) -> None:
        """Pause playback if supported."""

    def resume(self) -> None:
        """Resume playback if supported."""

    def shutdown(self) -> None:
        """Fully release backend resources."""

    def poll(self) -> PlaybackSnapshot:
        """Return current backend state snapshot."""