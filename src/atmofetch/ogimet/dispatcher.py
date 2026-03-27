from __future__ import annotations

from datetime import date

import pandas as pd

from atmofetch.ogimet.daily import ogimet_daily
from atmofetch.ogimet.hourly import ogimet_hourly


def meteo_ogimet(
    interval: str,
    date_range: tuple[str | date, str | date] | None = None,
    coords: bool = False,
    station: int | str | list[int | str] = 12330,
    precip_split: bool = True,
) -> pd.DataFrame:
    """Download hourly or daily SYNOP data from Ogimet.

    Parameters
    ----------
    interval : ``"daily"`` or ``"hourly"``.
    date_range : ``(start, end)`` dates. Defaults to last 30 days.
    coords : Add Lon/Lat columns.
    station : WMO station ID(s).
    precip_split : Split precipitation into 6/12/24h (hourly only).
    """
    if interval == "daily":
        if not precip_split:
            import warnings
            warnings.warn("precip_split argument is only valid for hourly time step", stacklevel=2)
        return ogimet_daily(date_range=date_range, coords=coords, station=station)
    elif interval == "hourly":
        return ogimet_hourly(
            date_range=date_range, coords=coords, station=station, precip_split_flag=precip_split,
        )
    else:
        raise ValueError(f"interval must be 'hourly' or 'daily', got '{interval}'")
