from __future__ import annotations

import io
import logging
from datetime import date, datetime

import pandas as pd

from atmofetch._utils.network import fetch_text

logger = logging.getLogger(__name__)

_COUNTRY_LIST_URL = "https://www.ncei.noaa.gov/pub/data/noaa/country-list.txt"
_ISD_HISTORY_URL = "https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv"


def nearest_stations_noaa(
    country: str,
    date_query: date | None = None,
    point: tuple[float, float] | None = None,
    no_of_stations: int = 10,
) -> pd.DataFrame:
    """Find nearest NOAA ISH stations for a given country and location.

    Parameters
    ----------
    country : Country name in uppercase (e.g. ``"UNITED KINGDOM"``).
    date_query : Day for which station availability is checked.  Defaults to today.
    point : ``(longitude, latitude)`` reference point.  If *None*, the centroid
        of all matching stations is used.
    no_of_stations : How many nearest stations to return.

    Returns
    -------
    DataFrame sorted by distance with station metadata.
    """
    if date_query is None:
        date_query = date.today()

    country = country.upper()

    # --- country list ---
    country_text = fetch_text(_COUNTRY_LIST_URL)
    country_rows: list[dict[str, str]] = []
    for line in country_text.strip().splitlines()[1:]:
        ctry = line[:2].strip()
        name = line[2:].strip()
        if ctry and name:
            country_rows.append({"CTRY": ctry, "countries": name})
    countries_df = pd.DataFrame(country_rows)

    # --- station history ---
    hist_text = fetch_text(_ISD_HISTORY_URL)
    stations_df = pd.read_csv(io.StringIO(hist_text))

    merged = stations_df.merge(countries_df, on="CTRY")

    def _parse_date(val: object) -> date | None:
        s = str(int(val)) if pd.notna(val) else ""  # type: ignore[call-overload]
        if len(s) < 8:
            return None
        try:
            return datetime.strptime(s, "%Y%m%d").date()
        except ValueError:
            return None

    merged["Begin_date"] = merged["BEGIN"].apply(_parse_date)
    merged["End_date"] = merged["END"].apply(_parse_date)

    result = merged[merged["countries"] == country].copy()
    if result.empty:
        raise ValueError(
            f"No stations found for country '{country}'. "
            "Check names at https://www.ncei.noaa.gov/pub/data/noaa/country-list.txt"
        )

    mask = (result["Begin_date"].notna()) & (result["End_date"].notna())
    result = result[mask]
    result = result[(result["Begin_date"] <= date_query) & (result["End_date"] >= date_query)]
    if result.empty:
        raise ValueError(f"No stations with data on {date_query} for country '{country}'.")

    if point is None:
        point = (
            float(result["LON"].mean()),
            float(result["LAT"].mean()),
        )

    # euclidean approximation scaled to ~km
    result = result.copy()
    result["distance"] = (
        (result["LON"] - point[0]) ** 2 + (result["LAT"] - point[1]) ** 2
    ) ** 0.5 * 112.196672
    result = result.sort_values("distance").head(no_of_stations).reset_index(drop=True)
    return result
