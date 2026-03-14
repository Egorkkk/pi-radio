from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from playback_protocol import PlaybackSnapshot, PlaybackStatus


@dataclass(slots=True)
class PlaybackRuntimeState:
    desired_station_id: Optional[str] = None
    pending_station_id: Optional[str] = None
    current_station_id: Optional[str] = None

    is_playing: bool = False
    is_online: bool = True

    last_error: Optional[str] = None

    def reset(self) -> None:
        self.desired_station_id = None
        self.pending_station_id = None
        self.current_station_id = None
        self.is_playing = False
        self.is_online = True
        self.last_error = None

    def apply_snapshot(self, snapshot: PlaybackSnapshot) -> None:
        self.current_station_id = snapshot.station_id
        self.is_playing = snapshot.status == PlaybackStatus.PLAYING
        self.is_online = snapshot.online
        self.last_error = snapshot.error_message

        if snapshot.status == PlaybackStatus.ERROR:
            self.pending_station_id = None
        elif snapshot.status in (PlaybackStatus.PLAYING, PlaybackStatus.STOPPED):
            self.pending_station_id = None

    @property
    def has_error(self) -> bool:
        return self.last_error is not None