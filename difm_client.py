from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from config import DIFMConfig


_AUDIOADDICT_AUTH_HEADER = "Basic ZXBoZW1lcm9uOmRheWVpcGgwbmVAcHA="
_BATCH_UPDATE_URL_TEMPLATE = (
    "https://api.audioaddict.com/v1/{network}/mobile/batch_update"
)
_CHANNELS_URL_TEMPLATE = "https://api.audioaddict.com/v1/{network}/channels.json"


@dataclass(slots=True, frozen=True)
class DIFMChannel:
    id: int
    key: str
    name: str
    asset_url: Optional[str]
    description: Optional[str]
    stream_url: str


class DIFMClientError(RuntimeError):
    pass


class DIFMClient:
    def __init__(self, config: DIFMConfig) -> None:
        self._config = config

    def fetch_channels(self, use_cache_fallback: bool = True) -> list[DIFMChannel]:
        if not self._config.listen_key.strip():
            raise DIFMClientError(
                "DIFM listen_key is empty. Put your premium listen_key in settings.toml."
            )

        try:
            channels = self._fetch_channels_from_batch_update()
            self._save_channels_cache(channels)
            return channels
        except DIFMClientError:
            if use_cache_fallback:
                cached = self._load_channels_cache()
                if cached:
                    return cached
            raise

    def _fetch_channels_from_batch_update(self) -> list[DIFMChannel]:
        batch_data = self._get_json(
            _BATCH_UPDATE_URL_TEMPLATE.format(network=self._config.network),
            headers={
                "Authorization": _AUDIOADDICT_AUTH_HEADER,
                "Accept-Encoding": "identity",
            },
            query={
                "stream_set_key": self._config.stream_quality,
            },
        )

        if not isinstance(batch_data, dict):
            raise DIFMClientError("Unexpected DI.FM batch_update response shape.")

        filters = batch_data.get("channel_filters")
        stream_sets = batch_data.get("stream_sets")

        if not isinstance(filters, list) or not isinstance(stream_sets, list):
            raise DIFMClientError("DI.FM batch_update response is missing expected data.")

        all_channels = self._extract_all_filter_channels(filters)
        stream_channels = self._extract_stream_channels(stream_sets)

        if not all_channels or not stream_channels:
            raise DIFMClientError("DI.FM batch_update returned no usable channels.")

        stream_by_id: dict[int, dict[str, Any]] = {}
        for item in stream_channels:
            channel_id = item.get("id")
            if isinstance(channel_id, int):
                stream_by_id[channel_id] = item

        result: list[DIFMChannel] = []
        for channel in all_channels:
            channel_id = channel.get("id")
            key = channel.get("key")
            name = channel.get("name")

            if not isinstance(channel_id, int):
                continue
            if not isinstance(key, str) or not key.strip():
                continue
            if not isinstance(name, str) or not name.strip():
                continue

            stream_info = stream_by_id.get(channel_id)
            stream_url = self._build_stream_url(
                channel_key=key,
                stream_info=stream_info,
            )

            asset_url = _optional_str(
                channel.get("asset_url") or channel.get("images", {}).get("default")
                if isinstance(channel.get("images"), dict)
                else channel.get("asset_url")
            )
            description = _optional_str(channel.get("description"))

            result.append(
                DIFMChannel(
                    id=channel_id,
                    key=key,
                    name=name,
                    asset_url=asset_url,
                    description=description,
                    stream_url=stream_url,
                )
            )

        if not result:
            raise DIFMClientError("No DI.FM channels could be parsed from batch_update.")

        result.sort(key=lambda item: item.name.lower())
        return result

    def _build_stream_url(
        self,
        *,
        channel_key: str,
        stream_info: Optional[dict[str, Any]],
    ) -> str:
        if isinstance(stream_info, dict):
            streams = stream_info.get("streams")
            if isinstance(streams, list):
                for stream in streams:
                    if not isinstance(stream, dict):
                        continue
                    raw_url = stream.get("url")
                    if isinstance(raw_url, str) and raw_url.strip():
                        return self._append_listen_key(raw_url)

        playlist_url = (
            f"https://listen.di.fm/{self._config.stream_quality}/"
            f"{channel_key}.pls"
        )
        return self._append_listen_key(playlist_url)

    def _append_listen_key(self, url: str) -> str:
        listen_key = self._config.listen_key.strip()
        if not listen_key:
            return url

        parsed = urllib.parse.urlparse(url)

        existing_query = parsed.query.strip()
        if not existing_query:
            new_query = listen_key
        else:
            query_parts = [part for part in existing_query.split("&") if part]
            query_parts = [part for part in query_parts if part != listen_key]
            query_parts.append(listen_key)
            new_query = "&".join(query_parts)

        return urllib.parse.urlunparse(parsed._replace(query=new_query))

    def _extract_all_filter_channels(self, filters: list[Any]) -> list[dict[str, Any]]:
        for item in filters:
            if not isinstance(item, dict):
                continue
            if item.get("name") != "All":
                continue
            channels = item.get("channels")
            if isinstance(channels, list):
                return [entry for entry in channels if isinstance(entry, dict)]
        return []

    def _extract_stream_channels(self, stream_sets: list[Any]) -> list[dict[str, Any]]:
        for stream_set in stream_sets:
            if not isinstance(stream_set, dict):
                continue
            streamlist = stream_set.get("streamlist")
            if not isinstance(streamlist, dict):
                continue
            channels = streamlist.get("channels")
            if isinstance(channels, list):
                return [entry for entry in channels if isinstance(entry, dict)]
        return []

    def _get_json(
        self,
        url: str,
        *,
        headers: Optional[dict[str, str]] = None,
        query: Optional[dict[str, str]] = None,
    ) -> Any:
        final_url = url
        if query:
            final_url = f"{url}?{urllib.parse.urlencode(query)}"

        request = urllib.request.Request(final_url)
        request.add_header("User-Agent", "pi-radio/0.1")
        request.add_header("Accept", "application/json")
        if headers:
            for key, value in headers.items():
                request.add_header(key, value)

        try:
            with urllib.request.urlopen(
                request,
                timeout=self._config.request_timeout_seconds,
            ) as response:
                payload = response.read()
        except urllib.error.HTTPError as exc:
            raise DIFMClientError(
                f"DI.FM HTTP error {exc.code} while requesting catalog."
            ) from exc
        except urllib.error.URLError as exc:
            raise DIFMClientError(
                f"DI.FM network error while requesting catalog: {exc}"
            ) from exc
        except OSError as exc:
            raise DIFMClientError(
                f"DI.FM request failed with OS error: {exc}"
            ) from exc

        try:
            return json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DIFMClientError(
                "Failed to decode DI.FM JSON response."
            ) from exc

    def _save_channels_cache(self, channels: list[DIFMChannel]) -> None:
        cache_path = self._config.channels_cache_file
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [
            {
                "id": channel.id,
                "key": channel.key,
                "name": channel.name,
                "asset_url": channel.asset_url,
                "description": channel.description,
                "stream_url": channel.stream_url,
            }
            for channel in channels
        ]
        cache_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_channels_cache(self) -> list[DIFMChannel]:
        cache_path = self._config.channels_cache_file
        if not cache_path.exists():
            return []

        try:
            raw = json.loads(cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []

        if not isinstance(raw, list):
            return []

        result: list[DIFMChannel] = []
        for item in raw:
            if not isinstance(item, dict):
                continue

            channel_id = item.get("id")
            key = item.get("key")
            name = item.get("name")
            stream_url = item.get("stream_url")

            if not isinstance(channel_id, int):
                continue
            if not isinstance(key, str) or not key.strip():
                continue
            if not isinstance(name, str) or not name.strip():
                continue
            if not isinstance(stream_url, str) or not stream_url.strip():
                continue

            result.append(
                DIFMChannel(
                    id=channel_id,
                    key=key,
                    name=name,
                    asset_url=_optional_str(item.get("asset_url")),
                    description=_optional_str(item.get("description")),
                    stream_url=stream_url,
                )
            )

        return result


def _optional_str(value: object) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        return None

    value = value.strip()
    return value or None