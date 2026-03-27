from __future__ import annotations

import logging
import re
import time
from datetime import date, timedelta

import pandas as pd
from bs4 import BeautifulSoup
from tqdm import tqdm

from atmofetch._utils.coordinates import get_coord_from_string
from atmofetch._utils.network import fetch_ogimet

logger = logging.getLogger(__name__)

_RATE_LIMIT_SECONDS = 20


def ogimet_daily(
    date_range: tuple[str | date, str | date] | None = None,
    coords: bool = False,
    station: int | str | list[int | str] = 12330,
    hour: int = 6,
) -> pd.DataFrame:
    """Download daily SYNOP summaries from Ogimet.

    Parameters
    ----------
    date_range : ``(start, end)`` dates. Defaults to last 30 days.
    coords : Whether to add Lon/Lat columns.
    station : WMO station ID(s).
    hour : UTC hour for the daily report (default 6).

    Returns
    -------
    DataFrame with daily meteorological summaries.
    """
    if date_range is None:
        end = date.today()
        start = end - timedelta(days=30)
    else:
        start = pd.Timestamp(date_range[0]).date()
        end = pd.Timestamp(date_range[1]).date()

    if isinstance(station, (int, str)):
        station = [station]

    # monthly date anchors
    dates: list[date] = []
    d = start
    while d <= end:
        dates.append(d)
        if d.month == 12:
            d = date(d.year + 1, 1, 1)
        else:
            d = date(d.year, d.month + 1, 1)
    if dates[-1] != end:
        dates.append(end)

    all_frames: list[pd.DataFrame] = []

    for station_nr in station:
        logger.info("station: %s (daily reports at %02d UTC)", station_nr, hour)
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

            url = (
                f"https://www.ogimet.com/cgi-bin/gsynres?lang=en&ind={station_nr}"
                f"&ndays=32&ano={year}&mes={month}&day={day}"
                f"&hora={hour}&ord=REV&Send=Send"
            )

            try:
                html = fetch_ogimet(url)
            except Exception:
                logger.warning("Failed to fetch %s", url)
                continue

            if len(html) < 500:
                logger.warning("Response too small from %s", url)
                continue

            soup = BeautifulSoup(html, "lxml")
            tables = soup.find_all("table")
            if not tables:
                continue

            data_table = tables[-1]
            rows = data_table.find_all("tr")
            if len(rows) < 3:
                continue

            # check for "No valid data"
            first_text = rows[0].get_text()
            if "No valid data" in first_text:
                logger.info("No valid data for station %s on %s", station_nr, dt)
                continue

            # parse the two-row header using colspan
            all_col_names = _build_column_names_from_rows(rows[0], rows[1])
            if all_col_names is None:
                logger.warning("Could not parse column names for station %s", station_nr)
                continue

            # strip trailing junk columns (e.g. "Dailyweathersummary" spans 8 empty cols)
            col_names = [c for c in all_col_names if "Dailyweather" not in c]
            n_cols = len(col_names)

            data_rows: list[list[str]] = []
            for row in rows[2:]:
                cells = row.find_all("td")
                vals = [c.get_text(strip=True) for c in cells]
                if vals:
                    data_rows.append(vals[:n_cols])

            if not data_rows:
                continue

            df = pd.DataFrame(data_rows)
            if df.shape[1] >= n_cols:
                df = df.iloc[:, :n_cols]
            df.columns = col_names[: df.shape[1]]

            df["station_ID"] = int(station_nr)

            # fix date: append year
            if "Date" in df.columns:
                _fix_date_column(df, year)

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

    # clean missing
    result = result.replace(["--", "---", "----", "-----"], pd.NA)
    result = result.drop_duplicates()

    # convert numeric columns
    num_cols = [
        "TemperatureCMax", "TemperatureCMin", "TemperatureCAvg", "TdAvgC",
        "HrAvg", "WindkmhInt", "WindkmhGust", "PresslevHp", "Precmm",
        "TotClOct", "lowClOct", "VisKm", "station_ID",
    ]
    for col in num_cols:
        if col in result.columns:
            result[col] = pd.to_numeric(result[col], errors="coerce")

    # parse date
    if "Date" in result.columns:
        result["Date"] = pd.to_datetime(result["Date"], format="%m/%d/%Y", errors="coerce")
        mask = (result["Date"] >= pd.Timestamp(start)) & (result["Date"] <= pd.Timestamp(end))
        result = result[mask]

    # reorder
    lead = ["station_ID"]
    if coords:
        lead += ["Lon", "Lat"]
    lead += ["Date", "TemperatureCAvg"]
    rest = [c for c in result.columns if c not in lead]
    result = result[[c for c in lead + rest if c in result.columns]]

    # deduplicate on station + date
    if "Date" in result.columns:
        result = result.drop_duplicates(subset=["station_ID", "Date"], keep="first")

    return result.reset_index(drop=True)


def _build_column_names_from_rows(
    header_row_el: object,
    sub_row_el: object,
) -> list[str] | None:
    """Build flat column names from a two-row HTML header using colspan."""
    cells1 = header_row_el.find_all(["th", "td"])
    cells2 = sub_row_el.find_all(["th", "td"])

    # expand row 1 using colspan
    expanded: list[tuple[str, int]] = []
    for c in cells1:
        text = re.sub(r"[^A-Za-z0-9]", "", c.get_text(strip=True))
        span = int(c.get("colspan", 1))
        expanded.append((text, span))

    sub_texts = [re.sub(r"[^A-Za-z0-9]", "", c.get_text(strip=True)) for c in cells2]

    names: list[str] = []
    sub_idx = 0
    for parent, span in expanded:
        if span == 1:
            names.append(parent)
        else:
            for _ in range(span):
                if sub_idx < len(sub_texts):
                    names.append(f"{parent}{sub_texts[sub_idx]}")
                    sub_idx += 1
                else:
                    names.append(parent)

    return names if names else None


def _fix_date_column(df: pd.DataFrame, year: str) -> None:
    """Append year to mm/dd Date strings, handling Dec/Jan overlap."""
    if "Date" not in df.columns:
        return
    months = df["Date"].str.split("/").str[0]
    unique_months = sorted(months.dropna().unique())
    if "01" in unique_months and "12" in unique_months:
        yr_series = months.apply(lambda m: year if m == "01" else str(int(year) - 1))
        df["Date"] = df["Date"].astype(str) + "/" + yr_series
    else:
        df["Date"] = df["Date"].astype(str) + "/" + year
