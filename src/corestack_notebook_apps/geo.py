from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any


def _iter_coordinate_pairs(coordinates: Any) -> Iterator[tuple[float, float]]:
    if (
        isinstance(coordinates, list | tuple)
        and len(coordinates) >= 2
        and isinstance(coordinates[0], int | float)
        and isinstance(coordinates[1], int | float)
    ):
        yield float(coordinates[0]), float(coordinates[1])
        return

    if isinstance(coordinates, Iterable) and not isinstance(coordinates, str | bytes):
        for item in coordinates:
            yield from _iter_coordinate_pairs(item)


def iter_geojson_lon_lat(geojson: dict[str, Any]) -> Iterator[tuple[float, float]]:
    for feature in geojson.get("features", []):
        geometry = feature.get("geometry") or {}
        yield from _iter_coordinate_pairs(geometry.get("coordinates", []))


def geojson_bounds(geojson: dict[str, Any]) -> tuple[float, float, float, float] | None:
    pairs = list(iter_geojson_lon_lat(geojson))
    if not pairs:
        return None
    longitudes = [pair[0] for pair in pairs]
    latitudes = [pair[1] for pair in pairs]
    return min(longitudes), min(latitudes), max(longitudes), max(latitudes)


def geojson_center(geojson: dict[str, Any]) -> tuple[float, float]:
    bounds = geojson_bounds(geojson)
    if bounds is None:
        return 20.5937, 78.9629
    min_lon, min_lat, max_lon, max_lat = bounds
    return (min_lat + max_lat) / 2, (min_lon + max_lon) / 2


def feature_count(geojson: dict[str, Any]) -> int:
    return len(geojson.get("features", []))


def property_values(geojson: dict[str, Any], key: str) -> list[str]:
    values: list[str] = []
    for feature in geojson.get("features", []):
        value = feature.get("properties", {}).get(key)
        if value is not None:
            values.append(str(value))
    return values

