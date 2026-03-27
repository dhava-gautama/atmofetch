from __future__ import annotations

import re

import numpy as np
import pandas as pd


def get_coord_from_string(txt: str, pattern: str = "Longitude") -> float | None:
    """Extract a decimal-degree coordinate from an Ogimet metadata string.

    Parameters
    ----------
    txt : raw metadata string (e.g. ``"Latitude: 52-25N  Longitude: 016-50E ..."``)
    pattern : ``"Longitude"`` or ``"Latitude"``
    """
    m = re.search(rf"{pattern}:\s*([\d]+)-([\d]+)(?:-([\d]+))?\s*([NSEW])", txt)
    if m is None:
        return None
    deg, minutes, seconds, hemisphere = m.groups()
    seconds = seconds or "0"
    value = int(deg) + (int(minutes) * 5 / 3) / 100 + (int(seconds) * 5 / 3) / 100 / 60
    if hemisphere in ("W", "S"):
        value *= -1
    return value


def precip_split(precip: pd.Series, pattern: str = "/12") -> pd.Series:
    """Split Ogimet precipitation string into numeric values for a given hour window.

    Parameters
    ----------
    precip : Series of strings like ``"1.2/6h0.0/12h3.4/24h"``
    pattern : ``"/6"``, ``"/12"``, or ``"/24"``
    """

    def _extract(val: str | None) -> float | None:
        if val is None or (isinstance(val, float) and np.isnan(val)):
            return None
        parts = str(val).split("h")
        for part in parts:
            if pattern in part:
                numeric = part.replace(pattern, "")
                try:
                    return float(numeric)
                except ValueError:
                    return None
        return None

    return precip.apply(_extract)
