# atmofetch

Python package to download *in-situ* meteorological data from publicly available repositories:

- **OGIMET** ([ogimet.com](http://ogimet.com/index.phtml.en)) — up-to-date SYNOP dataset (hourly & daily)
- **University of Wyoming** ([weather.uwyo.edu](http://weather.uwyo.edu/upperair/)) — atmospheric vertical profiling (sounding) data
- **NOAA NCEI** ([ncei.noaa.gov](https://www.ncei.noaa.gov/pub/data/noaa/)) — Integrated Surface Hourly (ISH) meteorological data
- **NOAA GML** ([gml.noaa.gov](https://gml.noaa.gov/ccgg/trends/)) — Mauna Loa CO2 monthly measurements

## Installation

```bash
pip install atmofetch
```

Or install from source:

```bash
pip install -e ".[dev]"
```

## Quick Start

### Download hourly NOAA ISH data

```python
from atmofetch import meteo_noaa_hourly

df = meteo_noaa_hourly(station="037720-99999", year=2023)
print(df.head())
```

### Download daily OGIMET data

```python
from atmofetch import meteo_ogimet

df = meteo_ogimet(interval="daily", station=72503, coords=True)
print(df.head())
```

### Download CO2 data from Mauna Loa

```python
from atmofetch import meteo_noaa_co2

co2 = meteo_noaa_co2()
print(co2.tail())
```

### Download atmospheric sounding

```python
from atmofetch import sounding_wyoming

profile, metadata = sounding_wyoming(wmo_id=45004, yy=2023, mm=7, dd=17, hh=12)
print(profile.head())
```

### Find nearest stations

```python
from atmofetch import nearest_stations_noaa, nearest_stations_ogimet

# NOAA stations near London
noaa = nearest_stations_noaa(country="UNITED KINGDOM", point=(-0.1, 51.5))
print(noaa[["STATION NAME", "distance"]].head())

# OGIMET stations near Paris
ogimet = nearest_stations_ogimet(country="France", point=(2.35, 48.86))
print(ogimet.head())
```

### Calculate distance between two points

```python
from atmofetch import spheroid_dist

km = spheroid_dist((18.63, 54.37), (17.02, 54.47))
print(f"Distance: {km:.1f} km")
```

## API Reference

### Meteorological Data

| Function | Source | Description |
|---|---|---|
| `meteo_ogimet()` | OGIMET | Hourly or daily SYNOP data |
| `ogimet_hourly()` | OGIMET | Hourly SYNOP data |
| `ogimet_daily()` | OGIMET | Daily SYNOP summaries |
| `meteo_noaa_hourly()` | NOAA ISH | Hourly data (some stations >100 years) |
| `meteo_noaa_co2()` | NOAA GML | Monthly CO2 from Mauna Loa |
| `sounding_wyoming()` | U. Wyoming | Vertical atmospheric profiles (TEMP/BUFR) |

### Station Discovery

| Function | Source | Description |
|---|---|---|
| `stations_ogimet()` | OGIMET | List all stations for a country |
| `nearest_stations_ogimet()` | OGIMET | Find nearest OGIMET stations |
| `nearest_stations_noaa()` | NOAA | Find nearest NOAA ISH stations |

### Utilities

| Function | Description |
|---|---|
| `spheroid_dist()` | Distance (km) between two (lon, lat) points |

## License

MIT
