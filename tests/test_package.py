def test_version():
    import atmofetch
    assert hasattr(atmofetch, "__version__")
    assert atmofetch.__version__ == "0.1.0"


def test_all_exports():
    import atmofetch
    expected = [
        "meteo_noaa_hourly", "meteo_noaa_co2", "nearest_stations_noaa",
        "meteo_ogimet", "ogimet_daily", "ogimet_hourly",
        "stations_ogimet", "nearest_stations_ogimet",
        "sounding_wyoming", "spheroid_dist",
    ]
    for name in expected:
        assert hasattr(atmofetch, name), f"Missing export: {name}"


def test_no_imgw_references():
    """Verify no IMGW functionality leaked into the package."""
    import atmofetch
    public = [name for name in dir(atmofetch) if not name.startswith("_")]
    for name in public:
        assert "imgw" not in name.lower(), f"IMGW reference found: {name}"
