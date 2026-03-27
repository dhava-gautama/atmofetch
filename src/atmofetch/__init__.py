"""AtmoFetch - Download meteorological data from publicly available repositories.

Data sources:
- OGIMET (ogimet.com) — SYNOP station data (hourly & daily)
- University of Wyoming — atmospheric vertical profiling (sounding) data
- NOAA — Integrated Surface Hourly (ISH) and Mauna Loa CO2 data
"""

from atmofetch.noaa import meteo_noaa_hourly, meteo_noaa_co2, nearest_stations_noaa
from atmofetch.ogimet import (
    meteo_ogimet,
    ogimet_daily,
    ogimet_hourly,
    stations_ogimet,
    nearest_stations_ogimet,
)
from atmofetch.wyoming import sounding_wyoming
from atmofetch._utils.distance import spheroid_dist

__version__ = "0.1.0"

__all__ = [
    # NOAA
    "meteo_noaa_hourly",
    "meteo_noaa_co2",
    "nearest_stations_noaa",
    # OGIMET
    "meteo_ogimet",
    "ogimet_daily",
    "ogimet_hourly",
    "stations_ogimet",
    "nearest_stations_ogimet",
    # Wyoming
    "sounding_wyoming",
    # Utilities
    "spheroid_dist",
]
