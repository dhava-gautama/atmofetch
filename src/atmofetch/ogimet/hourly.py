from __future__ import annotations

import logging
import time
from datetime import date, timedelta

import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm

from atmofetch._utils.coordinates import get_coord_from_string, precip_split
from atmofetch._utils.network import fetch_ogimet

logger = logging.getLogger(__name__)

_RATE_LIMIT_SECONDS = 20


def ogimet_hourly(
    date_range: tuple[str | date, str | date] | None = None,
    coords: bool = False,
    station: int | str | list[int | str] = 12330,
    precip_split_flag: bool = True,
) -> pd.DataFrame:
    """Download hourly SYNOP data from Ogimet.

    Parameters
    ----------
    date_range : ``(start, end)`` date strings or date objects.
        Defaults to last 30 days.
    coords : Whether to add Lon/Lat columns.
    station : WMO station ID(s).
    precip_split_flag : Whether to split precipitation into 6/12/24h columns.

    Returns
    -------
    DataFrame with hourly meteorological observations.
    """
    if date_range is None:
        end = date.today()
        start = end - timedelta(days=30)
    else:
        start = pd.Timestamp(date_range[0]).date()
        end = pd.Timestamp(date_range[1]).date()

    if isinstance(station, (int, str)):
        station = [station]

    # build monthly date chunks (iterate backwards like original R code)
    dates: list[date] = []
    d = start
    while d <= end:
        dates.append(d)
        # advance to first of next month
        if d.month == 12:
            d = date(d.year + 1, 1, 1)
        else:
            d = date(d.year, d.month + 1, 1)
    if dates[-1] != end:
        dates.append(end)

    all_frames: list[pd.DataFrame] = []

    for station_nr in station:
        logger.info("station: %s", station_nr)
        chunks = list(reversed(range(len(dates))))
        needs_delay = len(chunks) > 1

        if needs_delay:
            logger.info(
                "Ogimet rate-limits requests; %ds pause between queries.",
                _RATE_LIMIT_SECONDS,
            )

        for idx, i in enumerate(tqdm(chunks, desc=f"Station {station_nr}", leave=False)):
            if idx > 0 and needs_delay:
                time.sleep(_RATE_LIMIT_SECONDS)

            dt = dates[i]
            year = dt.strftime("%Y")
            month = dt.strftime("%m")
            day = dt.strftime("%d")

            if i > 0:
                ndays = (dates[i] - dates[i - 1]).days
                ndays = max(ndays, 1)
            else:
                ndays = 1

            if month == "01":
                url = (
                    f"http://ogimet.com/cgi-bin/gsynres?ind={station_nr}"
                    f"&lang=en&decoded=yes&ndays=31&ano={year}&mes=02&day=1&hora=00"
                )
            else:
                url = (
                    f"https://www.ogimet.com/cgi-bin/gsynres?ind={station_nr}"
                    f"&lang=en&decoded=yes&ndays={ndays:02d}"
                    f"&ano={year}&mes={month}&day={day}&hora=23"
                )

            try:
                html = fetch_ogimet(url)
            except Exception:
                logger.warning("Failed to fetch %s", url)
                continue

            if len(html) < 1000:
                continue

            soup = BeautifulSoup(html, "lxml")
            tables = soup.find_all("table")
            if not tables:
                continue

            # the data table is the last one
            data_table = tables[-1]
            rows = data_table.find_all("tr")
            if len(rows) < 2:
                continue

            # extract header from first row
            header_cells = rows[0].find_all(["th", "td"])
            header = [c.get_text(strip=True) for c in header_cells]
            if len(header) < 2:
                continue
            header = ["Date", "hour"] + header[1:]

            data_rows: list[list[str]] = []
            for row in rows[1:]:
                cells = row.find_all("td")
                vals = [c.get_text(strip=True) for c in cells]
                if vals:
                    data_rows.append(vals)

            if not data_rows:
                continue

            df = pd.DataFrame(data_rows)
            # trim or pad columns to match header length
            if df.shape[1] >= len(header):
                df = df.iloc[:, : len(header)]
            df.columns = header[: df.shape[1]]

            df["station_ID"] = int(station_nr)

            if coords:
                coord_table = tables[0] if len(tables) > 1 else None
                if coord_table:
                    coord_text = coord_table.get_text()
                    df["Lon"] = get_coord_from_string(coord_text, "Longitude")
                    df["Lat"] = get_coord_from_string(coord_text, "Latitude")

            all_frames.append(df)

    if not all_frames:
        return pd.DataFrame()

    result = pd.concat(all_frames, ignore_index=True)

    # clean missing markers
    result = result.replace(["--", "---", "----", "-----"], pd.NA)
    result = result.drop_duplicates()

    # parse datetime
    if "Date" in result.columns and "hour" in result.columns:
        result["Date"] = pd.to_datetime(
            result["Date"].astype(str) + " " + result["hour"].astype(str),
            format="%m/%d/%Y %H:%M",
            errors="coerce",
            utc=True,
        )
        result = result.drop(columns=["hour"], errors="ignore")

    # convert numeric columns where possible
    numeric_cols = [
        "TC",
        "TdC",
        "ffkmh",
        "Gustkmh",
        "P0hPa",
        "PseahPa",
        "PTnd",
        "Nt",
        "Nh",
        "HKm",
        "InsoD1",
        "Viskm",
        "Snowcm",
        "station_ID",
    ]
    for col in numeric_cols:
        if col in result.columns:
            result[col] = pd.to_numeric(result[col], errors="coerce")

    # split precipitation
    if precip_split_flag and "Precmm" in result.columns:
        if result["Precmm"].isna().all():
            result["pr6"] = pd.NA
            result["pr12"] = pd.NA
            result["pr24"] = pd.NA
        else:
            result["pr6"] = precip_split(result["Precmm"], pattern="/6")
            result["pr12"] = precip_split(result["Precmm"], pattern="/12")
            result["pr24"] = precip_split(result["Precmm"], pattern="/24")

    # clip to requested date range
    if "Date" in result.columns:
        mask = (result["Date"] >= pd.Timestamp(start, tz="UTC")) & (
            result["Date"] <= pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)
        )
        result = result[mask]

    # reorder columns
    lead = ["station_ID"]
    if coords:
        lead += ["Lon", "Lat"]
    lead += ["Date", "TC"]
    rest = [c for c in result.columns if c not in lead and c not in ("WW", "W1", "W2", "W3")]
    result = result[[c for c in lead + rest if c in result.columns]]

    return result.reset_index(drop=True)
