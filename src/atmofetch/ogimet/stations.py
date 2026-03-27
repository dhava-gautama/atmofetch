from __future__ import annotations

import logging
import re
from datetime import date

import pandas as pd

from atmofetch._utils.network import fetch_ogimet

logger = logging.getLogger(__name__)


def stations_ogimet(
    country: str = "United Kingdom",
    date_query: date | None = None,
) -> pd.DataFrame:
    """List all SYNOP stations for a country from Ogimet.

    Parameters
    ----------
    country : Country name (e.g. ``"United Kingdom"``).
    date_query : Day to query. Defaults to today.

    Returns
    -------
    DataFrame with columns: wmo_id, station_names, lon, lat, alt.
    """
    if date_query is None:
        date_query = date.today()

    country_url = country.replace(" ", "+")
    year = date_query.strftime("%Y")
    month = date_query.strftime("%m")
    day = date_query.strftime("%d")

    url = (
        f"http://ogimet.com/cgi-bin/gsynres?lang=en&state={country_url}"
        f"&osum=no&fmt=html&ord=REV&ano={year}&mes={month}&day={day}"
        f"&hora=06&ndays=1&Send=send"
    )

    html = fetch_ogimet(url)
    if not html or len(html) < 100:
        raise RuntimeError(
            f"No data returned for country '{country}'. "
            "Check names at https://ogimet.com/display_stations.php"
        )

    return _parse_station_list(html, country)


def nearest_stations_ogimet(
    country: str | list[str] = "United Kingdom",
    date_query: date | None = None,
    point: tuple[float, float] = (2.0, 50.0),
    no_of_stations: int = 10,
) -> pd.DataFrame:
    """Find nearest SYNOP stations from Ogimet for a given location.

    Parameters
    ----------
    country : Country name(s).
    date_query : Day to query. Defaults to today.
    point : ``(longitude, latitude)`` reference point.
    no_of_stations : Number of nearest stations to return.

    Returns
    -------
    DataFrame with columns: wmo_id, station_names, lon, lat, alt, distance.
    """
    if len(point) != 2:
        raise ValueError("point must have exactly two coordinates (lon, lat)")
    if date_query is None:
        date_query = date.today()

    if isinstance(country, str):
        country = [country]

    frames: list[pd.DataFrame] = []
    for c in country:
        try:
            df = stations_ogimet(country=c, date_query=date_query)
            if df is not None and not df.empty:
                frames.append(df)
        except Exception:
            logger.warning("Failed to get stations for country '%s'", c)

    if not frames:
        raise RuntimeError("No station data retrieved for any of the specified countries.")

    result = pd.concat(frames, ignore_index=True)

    # compute distances (euclidean approximation scaled to km)
    result["distance"] = (
        (result["lon"] - point[0]) ** 2 + (result["lat"] - point[1]) ** 2
    ) ** 0.5 * 112.196672
    result = result.sort_values("distance").head(no_of_stations).reset_index(drop=True)
    return result


def _parse_station_list(html: str, country: str) -> pd.DataFrame:
    """Parse the Ogimet station list HTML response."""
    parts = html.split("Decoded synops since")
    if len(parts) < 2:
        raise RuntimeError(f"Unexpected response format for country '{country}'")

    entries = parts[1:]
    records: list[dict] = []

    for entry in entries:
        snippet = entry[:400]
        m_lat = re.search(r"Lat=([\d-]+)", snippet)
        m_lon = re.search(r"Lon=([\d-]+)", snippet)
        m_alt = re.search(r"Alt=([\d]+)", snippet)

        if not (m_lat and m_lon and m_alt):
            continue

        lat_raw = m_lat.group(1)
        lon_raw = m_lon.group(1)
        alt = int(m_alt.group(1))

        # parse DMS-style coordinates
        lat = _parse_dms_coord(lat_raw, snippet, "lat")
        lon = _parse_dms_coord(lon_raw, snippet, "lon")

        # extract WMO ID — usually a 5-digit number near the coordinates
        wmo_match = re.search(r"\b(\d{5})\b", snippet[snippet.find(str(alt)) :])
        wmo_id = wmo_match.group(1) if wmo_match else ""

        # extract station name (after " - ")
        name_match = re.search(r" - ([^'\"<]+)", snippet)
        station_name = name_match.group(1).strip() if name_match else ""

        records.append(
            {
                "wmo_id": wmo_id,
                "station_names": station_name,
                "lon": lon,
                "lat": lat,
                "alt": alt,
            }
        )

    return pd.DataFrame(records)


def _parse_dms_coord(raw: str, context: str, coord_type: str) -> float:
    """Parse a DMS coordinate string like '5210' to decimal degrees."""
    raw = raw.lstrip("-")
    if len(raw) >= 4:
        if coord_type == "lon":
            deg = int(raw[:3]) if len(raw) >= 5 else int(raw[:2])
            minutes = int(raw[-2:])
        else:
            deg = int(raw[:2])
            minutes = int(raw[2:4])
        value = deg + (minutes / 100) * 1.6667
    else:
        value = float(raw)

    # determine hemisphere from context
    if coord_type == "lat":
        if "S" in context[: context.find("Lon") if "Lon" in context else 100]:
            value *= -1
    else:
        if (
            "W" in context[context.find("Lon") : context.find("Lon") + 50]
            if "Lon" in context
            else False
        ):
            value *= -1

    return value
