import math

import pandas as pd
import pytest

from atmofetch._utils.distance import spheroid_dist
from atmofetch._utils.coordinates import get_coord_from_string, precip_split


class TestSpheroidDist:
    def test_known_distance(self):
        # Gdansk to Slupsk ~approx 100-120 km
        p1 = (18.633333, 54.366667)
        p2 = (17.016667, 54.466667)
        d = spheroid_dist(p1, p2)
        assert 95 < d < 125

    def test_same_point(self):
        p = (0.0, 0.0)
        assert spheroid_dist(p, p) == pytest.approx(0.0, abs=1e-6)

    def test_antipodal(self):
        d = spheroid_dist((0, 0), (180, 0))
        assert d == pytest.approx(math.pi * 6371.009, rel=0.01)


class TestGetCoordFromString:
    def test_longitude(self):
        txt = "Latitude: 52-25N  Longitude: 016-50E  Alt: 84m"
        lon = get_coord_from_string(txt, "Longitude")
        assert lon is not None
        assert 16 < lon < 17

    def test_latitude(self):
        txt = "Latitude: 52-25N  Longitude: 016-50E  Alt: 84m"
        lat = get_coord_from_string(txt, "Latitude")
        assert lat is not None
        assert 52 < lat < 53

    def test_southern_hemisphere(self):
        txt = "Latitude: 33-55S  Longitude: 018-36E  Alt: 46m"
        lat = get_coord_from_string(txt, "Latitude")
        assert lat is not None
        assert lat < 0

    def test_no_match(self):
        assert get_coord_from_string("no coords here", "Longitude") is None


class TestPrecipSplit:
    def test_basic(self):
        s = pd.Series(["1.2/6h0.0/12h3.4/24h"])
        assert precip_split(s, pattern="/6").iloc[0] == pytest.approx(1.2)
        assert precip_split(s, pattern="/12").iloc[0] == pytest.approx(0.0)
        assert precip_split(s, pattern="/24").iloc[0] == pytest.approx(3.4)

    def test_missing(self):
        s = pd.Series([None, float("nan")])
        result = precip_split(s, pattern="/6")
        assert result.isna().all()
