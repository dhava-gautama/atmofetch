from __future__ import annotations

import gzip
import io
import logging

import pandas as pd

from atmofetch._utils.network import download

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.ncei.noaa.gov/pub/data/noaa/"

_COL_WIDTHS = [
    4, 6, 5, 4, 2, 2, 2, 2, 1, 6,
    7, 5, 5, 5, 4, 3, 1, 1, 4, 1,
    5, 1, 1, 1, 6, 1, 1, 1, 5, 1,
    5, 1, 5, 1,
]


def meteo_noaa_hourly(
    station: str,
    year: int | list[int] = 2019,
    fm12: bool = True,
) -> pd.DataFrame:
    """Download hourly NOAA Integrated Surface Hourly (ISH) data.

    Parameters
    ----------
    station : Station ID string (e.g. ``"037720-99999"``).
    year : Year or list of years.
    fm12 : If True, keep only FM-12 (SYNOP) records.

    Returns
    -------
    DataFrame with columns: date, year, month, day, hour, lon, lat, alt,
    t2m, dpt2m, ws, wd, slp, visibility.
    """
    if isinstance(year, int):
        year = [year]

    frames: list[pd.DataFrame] = []
    for yr in year:
        url = f"{_BASE_URL}{yr}/{station}-{yr}.gz"
        try:
            raw = download(url)
        except Exception:
            logger.warning("Failed to download %s", url)
            continue

        if len(raw) < 100:
            logger.warning("File too small for %s-%s, skipping", station, yr)
            continue

        text = gzip.decompress(raw).decode("latin-1")
        df = pd.read_fwf(io.StringIO(text), widths=_COL_WIDTHS, header=None)

        if fm12:
            df = df[df.iloc[:, 11] == "FM-12"]

        df = df.iloc[:, [3, 4, 5, 6, 9, 10, 12, 15, 18, 24, 28, 30, 32]]
        df.columns = [
            "year", "month", "day", "hour",
            "lat", "lon", "alt",
            "wd", "ws", "visibility",
            "t2m", "dpt2m", "slp",
        ]

        df["date"] = pd.to_datetime(
            df[["year", "month", "day", "hour"]].assign(minute=0, second=0),
            utc=True,
        )

        na_map = {"t2m": 9999, "dpt2m": 9999, "ws": 9999, "wd": 999, "slp": 99999, "visibility": 999999}
        for col, sentinel in na_map.items():
            df[col] = df[col].replace(sentinel, pd.NA)

        df["lon"] = df["lon"] / 1000
        df["lat"] = df["lat"] / 1000
        df["ws"] = df["ws"] / 10
        df["t2m"] = df["t2m"] / 10
        df["dpt2m"] = df["dpt2m"] / 10
        df["slp"] = df["slp"] / 10

        frames.append(df)

    if not frames:
        return pd.DataFrame()

    result = pd.concat(frames, ignore_index=True)
    result = result[
        ["date", "year", "month", "day", "hour", "lon", "lat", "alt",
         "t2m", "dpt2m", "ws", "wd", "slp", "visibility"]
    ]
    return result.sort_values("date").reset_index(drop=True)
