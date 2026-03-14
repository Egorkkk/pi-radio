from __future__ import annotations

from config import load_config
from difm_catalog import DIFMCatalog
from difm_client import DIFMClient, DIFMClientError
from difm_genre_map import load_difm_genre_map
from radio_catalog import RadioCatalog


def main() -> None:
    config = load_config()
    genre_map = load_difm_genre_map("difm_genres.txt")

    print("Loading DI.FM channels...")
    client = DIFMClient(config.difm)

    try:
        channels = client.fetch_channels(use_cache_fallback=True)
    except DIFMClientError as exc:
        print("FAILED to fetch DI.FM channels:")
        print(f"  {exc}")
        raise SystemExit(1)

    print(f"Fetched channels: {len(channels)}")
    print()

    difm_catalog = DIFMCatalog(channels)
    radio_catalog = RadioCatalog.from_difm(
        difm_catalog=difm_catalog,
        genre_map=genre_map,
    )

    genres = radio_catalog.list_genres()
    stations = radio_catalog.list_stations()

    print(f"Radio catalog genres: {len(genres)}")
    print(f"Radio catalog stations with at least one mapped genre: {len(stations)}")
    print()

    print("Genres summary:")
    for genre in genres:
        station_count = len(radio_catalog.get_stations_for_genre(genre.id))
        print(f"  {genre.id:16}  {genre.name:12}  stations={station_count}")

    print()

    mapped_station_ids = {station.id for station in stations}
    unmapped_channels = [
        channel
        for channel in channels
        if f"difm:{channel.key}" not in mapped_station_ids
    ]

    print(f"Unmapped DI.FM channels: {len(unmapped_channels)}")
    print()

    preview_count = min(40, len(unmapped_channels))
    if preview_count > 0:
        print(f"First {preview_count} unmapped channels:")
        for channel in unmapped_channels[:preview_count]:
            print(f"  {channel.key:24}  {channel.name}")
        print()

    print("Sample mapped stations:")
    for station in stations[:20]:
        print(
            f"  {station.id:28}  {station.name:32}  genres={', '.join(station.genre_ids)}"
        )

    print()
    ui_genres = radio_catalog.build_ui_genres()
    print(f"UI genres built: {len(ui_genres)}")
    if ui_genres:
        first_genre = ui_genres[0]
        print(f"First UI genre: {first_genre.id} / {first_genre.name}")
        print(f"Stations in first UI genre: {len(first_genre.stations)}")
        for station in first_genre.stations[:10]:
            print(f"  {station.id:24}  {station.name}")

    print()
    print("Genre map test completed successfully.")


if __name__ == "__main__":
    main()