from __future__ import annotations

from config import load_config
from difm_client import DIFMClient, DIFMClientError
from difm_catalog import DIFMCatalog


def main() -> None:
    config = load_config()

    print("Loading config...")
    print(f"  network: {config.difm.network}")
    print(f"  stream_quality: {config.difm.stream_quality}")
    print(f"  cache file: {config.difm.channels_cache_file}")
    print(f"  listen_key set: {bool(config.difm.listen_key.strip())}")

    client = DIFMClient(config.difm)

    try:
        channels = client.fetch_channels(use_cache_fallback=True)
    except DIFMClientError as exc:
        print("FAILED to fetch DI.FM channels:")
        print(f"  {exc}")
        raise SystemExit(1)

    print()
    print(f"Fetched channels: {len(channels)}")

    catalog = DIFMCatalog(channels)
    stations = catalog.list_stations()

    print(f"Catalog stations: {len(stations)}")
    print()

    preview_count = min(15, len(stations))
    print(f"First {preview_count} stations:")
    for station in stations[:preview_count]:
        print(f"  id={station.id}")
        print(f"    name={station.name}")
        print(f"    genre_id={station.genre_id}")
        print(f"    stream_url={station.stream_url}")
        if station.description:
            print(f"    description={station.description[:120]}")
        print()

    if stations:
        sample = stations[0]
        lookup = catalog.get_station(sample.id)
        print("Lookup test:")
        print(f"  requested: {sample.id}")
        print(f"  found: {lookup is not None}")
        if lookup is not None:
            print(f"  lookup name: {lookup.name}")
            print(f"  lookup stream_url: {lookup.stream_url}")

    print()
    print("DI.FM catalog test completed successfully.")


if __name__ == "__main__":
    main()