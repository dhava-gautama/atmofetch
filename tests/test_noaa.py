import gzip
import io

import pandas as pd
import pytest


class TestMeteoNoaaHourly:
    def test_import(self):
        from atmofetch.noaa.hourly import meteo_noaa_hourly
        assert callable(meteo_noaa_hourly)

    def test_empty_on_bad_station(self, monkeypatch):
        from atmofetch.noaa import hourly as mod

        def fake_download(url):
            raise RuntimeError("not found")

        monkeypatch.setattr(mod, "download", fake_download)
        from atmofetch.noaa.hourly import meteo_noaa_hourly
        result = meteo_noaa_hourly(station="000000-00000", year=1900)
        assert isinstance(result, pd.DataFrame)
        assert result.empty


class TestMeteoNoaaCo2:
    def test_import(self):
        from atmofetch.noaa.co2 import meteo_noaa_co2
        assert callable(meteo_noaa_co2)


class TestNearestStationsNoaa:
    def test_import(self):
        from atmofetch.noaa.stations import nearest_stations_noaa
        assert callable(nearest_stations_noaa)
