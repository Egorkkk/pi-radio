from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


_GENRE_HEADER_RE = re.compile(r"^\s*(\d+)\.\s*(.+?)\s*:\s*$")


@dataclass(slots=True, frozen=True)
class GenreMapEntry:
    id: str
    name: str
    channel_keys: tuple[str, ...] = ()


@dataclass(slots=True, frozen=True)
class DIFMGenreMap:
    genres: tuple[GenreMapEntry, ...]

    def get_genre_ids_for_channel_name(self, channel_name: str) -> tuple[str, ...]:
        normalized = _normalize_channel_name(channel_name)
        matched: list[str] = []

        for genre in self.genres:
            if normalized in genre.channel_keys:
                matched.append(genre.id)

        return tuple(matched)

    def list_genres(self) -> tuple[GenreMapEntry, ...]:
        return self.genres


def load_difm_genre_map(path: str | Path) -> DIFMGenreMap:
    map_path = Path(path)

    if not map_path.exists():
        return DIFMGenreMap(genres=())

    raw_text = map_path.read_text(encoding="utf-8")
    return parse_difm_genre_map_text(raw_text)


def parse_difm_genre_map_text(text: str) -> DIFMGenreMap:
    genres: list[GenreMapEntry] = []

    current_genre_id: str | None = None
    current_genre_name: str | None = None
    current_channels: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        header_match = _GENRE_HEADER_RE.match(line)
        if header_match:
            if current_genre_id is not None and current_genre_name is not None:
                genres.append(
                    GenreMapEntry(
                        id=current_genre_id,
                        name=current_genre_name,
                        channel_keys=_dedupe_preserve_order(current_channels),
                    )
                )

            _, genre_name = header_match.groups()
            current_genre_name = genre_name.strip()
            current_genre_id = _slugify_genre_name(current_genre_name)
            current_channels = []
            continue

        if current_genre_id is None:
            continue

        current_channels.append(_normalize_channel_name(line))

    if current_genre_id is not None and current_genre_name is not None:
        genres.append(
            GenreMapEntry(
                id=current_genre_id,
                name=current_genre_name,
                channel_keys=_dedupe_preserve_order(current_channels),
            )
        )

    return DIFMGenreMap(genres=tuple(genres))


def _slugify_genre_name(name: str) -> str:
    slug = name.strip().lower()
    slug = slug.replace("&", " and ")
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug or "genre"


def _normalize_channel_name(name: str) -> str:
    normalized = name.strip().lower()
    normalized = normalized.replace("&", " and ")
    normalized = normalized.replace(":", "")
    normalized = normalized.replace(".", "")
    normalized = normalized.replace("-", " ")
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _dedupe_preserve_order(items: list[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []

    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)

    return tuple(result)