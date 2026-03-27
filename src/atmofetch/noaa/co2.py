from __future__ import annotations

import io
import logging

import pandas as pd

from atmofetch._utils.network import fetch_text

logger = logging.getLogger(__name__)

_CO2_URL = "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_mm_mlo.txt"


def meteo_noaa_co2() -> pd.DataFrame:
    """Download monthly CO2 measurements from Mauna Loa Observatory (NOAA).

    Returns
    -------
    DataFrame with columns: yy, mm, yy_d, co2_avg, co2_interp, co2_seas, ndays, st_dev_days.
    """
    text = fetch_text(_CO2_URL)

    lines = [line for line in text.splitlines() if not line.startswith("#")]
    cleaned = "\n".join(lines)

    df = pd.read_csv(
        io.StringIO(cleaned),
        sep=r"\s+",
        header=None,
        names=["yy", "mm", "yy_d", "co2_avg", "co2_interp", "co2_seas", "ndays", "st_dev_days"],
        na_values=["-9.99", "-0.99"],
    )
    return df
