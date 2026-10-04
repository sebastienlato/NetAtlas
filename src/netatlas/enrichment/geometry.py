"""WGS84 bounding areas with explicit antimeridian splitting; no search execution."""

from netatlas.enrichment.models import Boundary


def bounding_boundary(west: float, south: float, east: float, north: float) -> Boundary:
    if not south < north or west == east:
        raise ValueError("nonempty bounding area required")
    spans = [(west, east)] if west < east else [(west, 180.0), (-180.0, east)]
    polygons = []
    for left, right in spans:
        if left == right:
            continue
        # Also split very wide ordinary boxes so no segment implies the short way around Earth.
        parts = [(left, right)] if right - left <= 180 else [(left, 0.0), (0.0, right)]
        for low, high in parts:
            polygons.append(
                (((low, south), (high, south), (high, north), (low, north), (low, south)),)
            )
    return Boundary(coordinates=tuple(polygons))
