from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable

from playback_protocol import PlaybackBackend
from playback_state import PlaybackRuntimeState
from station_selection_policy import StationSelectionPolicy


@runtime_checkable
class StationLookupCatalog(Protocol):
    def get_station(self, station_id: str) -> object | None:
        """
        Must return an object that has at least:
        - id: str
        - stream_url: str
        """


@dataclass(slots=True)
class RadioController:
    catalog: StationLookupCatalog
    backend: PlaybackBackend
    selection_policy: StationSelectionPolicy
    playback_runtime: PlaybackRuntimeState = field(
        default_factory=PlaybackRuntimeState
    )

    def __post_init__(self) -> None:
        self.backend.start()

    def update(self, state: object, dt: float) -> None:
        confirmed_station_id = self._resolve_confirmed_station_id(state, dt)

        if confirmed_station_id is not None:
            self.playback_runtime.desired_station_id = confirmed_station_id
            self._switch_to_station_if_needed(confirmed_station_id)

        snapshot = self.backend.poll()
        self.playback_runtime.apply_snapshot(snapshot)
        self._apply_snapshot_to_ui_state(state)

    def shutdown(self) -> None:
        self.backend.shutdown()

    def _resolve_confirmed_station_id(self, state: object, dt: float) -> Optional[str]:
        selected_station_id = getattr(state, "selected_station_id", None)
        station_dial = getattr(state, "station_dial", None)

        if station_dial is None:
            return None

        target_position = getattr(station_dial, "target_position", 0.0)
        display_position = getattr(station_dial, "display_position", 0.0)

        return self.selection_policy.update(
            active_station_id=selected_station_id,
            target_position=target_position,
            display_position=display_position,
            dt=dt,
        )

    def _switch_to_station_if_needed(self, station_id: str) -> None:
        if station_id == self.playback_runtime.current_station_id:
            return

        station_record = self.catalog.get_station(station_id)
        if station_record is None:
            self.playback_runtime.last_error = (
                f"Station '{station_id}' not found in playback catalog."
            )
            return

        stream_url = getattr(station_record, "stream_url", None)
        if not isinstance(stream_url, str) or not stream_url.strip():
            self.playback_runtime.last_error = (
                f"Station '{station_id}' does not provide a valid stream_url."
            )
            return

        self.playback_runtime.pending_station_id = station_id
        self.playback_runtime.last_error = None
        self.backend.play_station(station_id=station_id, stream_url=stream_url)

    def _apply_snapshot_to_ui_state(self, state: object) -> None:
        setattr(state, "play", self.playback_runtime.is_playing)
        setattr(state, "online", self.playback_runtime.is_online)