from __future__ import annotations

import io
import logging
import re

import pandas as pd

from atmofetch._utils.network import fetch_text

logger = logging.getLogger(__name__)

_SOUNDING_COLS = [
    "PRES",
    "HGHT",
    "TEMP",
    "DWPT",
    "RELH",
    "MIXR",
    "DRCT",
    "SKNT",
    "THTA",
    "THTE",
    "THTV",
]


def sounding_wyoming(
    wmo_id: int,
    yy: int,
    mm: int,
    dd: int,
    hh: int,
    minute: int = 0,
    bufr: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Download atmospheric sounding data from the University of Wyoming.

    Parameters
    ----------
    wmo_id : WMO station ID.
    yy, mm, dd, hh : Year, month, day, hour of the sounding.
    minute : Minute (relevant for BUFR soundings only).
    bufr : If True, use BUFR format instead of TEMP.

    Returns
    -------
    Tuple of (profile_data, metadata).
        - profile_data: DataFrame with PRES, HGHT, TEMP, DWPT, RELH, MIXR, DRCT, SKNT, THTA, THTE, THTV
        - metadata: DataFrame with sounding metadata / instability indices
    """
    mm_s = f"{mm:02d}"
    dd_s = f"{dd:02d}"
    hh_s = f"{hh:02d}"
    min_s = f"{minute:02d}"

    if bufr:
        url = (
            f"http://weather.uwyo.edu/cgi-bin/bufrraob.py?src=bufr"
            f"&datetime={yy}-{mm_s}-{dd_s}+{hh_s}:{min_s}:00"
            f"&id={wmo_id:05d}&type=TEXT:LIST"
        )
    else:
        url = (
            f"http://weather.uwyo.edu/cgi-bin/sounding?TYPE=TEXT%3ALIST"
            f"&YEAR={yy}&MONTH={mm_s}&FROM={dd_s}{hh_s}&TO={dd_s}{hh_s}"
            f"&STNM={wmo_id:05d}"
        )

    text = fetch_text(url)
    if len(text) < 800:
        raise RuntimeError(f"Response too small. Check URL: {url}")

    # find <PRE> sections
    pre_indices = [m.start() for m in re.finditer(r"</?PRE>", text, re.IGNORECASE)]
    if len(pre_indices) < 2:
        raise RuntimeError(
            "Could not find sounding data markers. "
            "Check wmo_id and date at http://weather.uwyo.edu/upperair/sounding.html"
        )

    # extract profile data between first <PRE> and second </PRE>
    section1 = text[pre_indices[0] : pre_indices[1]]
    lines = section1.split("\n")

    # skip header lines (typically: <PRE>, blank, header, dashes, units)
    data_lines: list[str] = []
    header_found = False
    dashes_passed = False
    for line in lines:
        stripped = line.strip()
        if not stripped or "<" in stripped:
            continue
        if "PRES" in stripped and "HGHT" in stripped:
            header_found = True
            continue
        if not header_found:
            continue
        if stripped.startswith("---"):
            dashes_passed = True
            continue
        if not dashes_passed:
            # this is the units row (e.g. "hPa    m     C ...")
            dashes_passed = True
            continue
        data_lines.append(stripped)

    if not data_lines:
        raise RuntimeError(f"No profile data found in sounding response from {url}")

    df = pd.read_fwf(
        io.StringIO("\n".join(data_lines)),
        widths=[7] * 11,
        header=None,
    )
    df.columns = _SOUNDING_COLS[: df.shape[1]]
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # for BUFR: convert m/s → knots to match TEMP format
    if bufr and "SKNT" in df.columns:
        df["SKNT"] = (df["SKNT"] * 1.9438).round(1)

    # extract metadata
    if not bufr and len(pre_indices) >= 4:
        meta_section = text[pre_indices[2] : pre_indices[3]]
        meta_lines = [
            line.strip() for line in meta_section.split("\n") if line.strip() and "<" not in line
        ]
        meta_records: list[dict[str, str]] = []
        for ml in meta_lines:
            parts = ml.split(":", 1)
            if len(parts) == 2:
                meta_records.append({"parameter": parts[0].strip(), "value": parts[1].strip()})
        metadata = pd.DataFrame(meta_records)
    elif bufr:
        # minimal metadata for BUFR
        obs_lines = [ln for ln in text.split("\n") if "Observations" in ln or "Station" in ln]
        metadata = pd.DataFrame(
            {"bufr_metadata": [re.sub(r"<.*?>", "", ln).strip() for ln in obs_lines[:2]]}
        )
    else:
        metadata = pd.DataFrame()

    return df, metadata
