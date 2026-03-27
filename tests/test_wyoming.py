class TestSoundingWyoming:
    def test_import(self):
        from atmofetch.wyoming.sounding import sounding_wyoming

        assert callable(sounding_wyoming)
