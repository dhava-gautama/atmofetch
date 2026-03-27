from __future__ import annotations

import math


def spheroid_dist(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    """Distance between two points on a spheroid using Vincenty's formula.

    Parameters
    ----------
    p1 : (lon, lat) in decimal degrees
    p2 : (lon, lat) in decimal degrees

    Returns
    -------
    Distance in kilometres.
    """
    r = 6_371_009  # mean earth radius in metres
    lon1, lat1, lon2, lat2 = (v * math.pi / 180 for v in (*p1, *p2))
    diff_long = lon2 - lon1

    num = (math.cos(lat2) * math.sin(diff_long)) ** 2 + (
        math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(diff_long)
    ) ** 2
    denom = (
        math.sin(lat1) * math.sin(lat2)
        + math.cos(lat1) * math.cos(lat2) * math.cos(diff_long)
    )
    d = math.atan2(math.sqrt(num), denom)
    return d * r / 1000
