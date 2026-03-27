import pandas as pd
import pytest


class TestOgimetImports:
    def test_hourly_import(self):
        from atmofetch.ogimet.hourly import ogimet_hourly
        assert callable(ogimet_hourly)

    def test_daily_import(self):
        from atmofetch.ogimet.daily import ogimet_daily
        assert callable(ogimet_daily)

    def test_dispatcher_import(self):
        from atmofetch.ogimet.dispatcher import meteo_ogimet
        assert callable(meteo_ogimet)

    def test_stations_import(self):
        from atmofetch.ogimet.stations import stations_ogimet, nearest_stations_ogimet
        assert callable(stations_ogimet)
        assert callable(nearest_stations_ogimet)


class TestMeteoOgimet:
    def test_invalid_interval(self):
        from atmofetch.ogimet.dispatcher import meteo_ogimet
        with pytest.raises(ValueError, match="interval must be"):
            meteo_ogimet(interval="weekly", station=12330)


class TestNearestStationsOgimet:
    def test_invalid_point(self):
        from atmofetch.ogimet.stations import nearest_stations_ogimet
        with pytest.raises(ValueError, match="two coordinates"):
            nearest_stations_ogimet(point=(1, 2, 3))
