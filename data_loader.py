"""
data_loader.py
--------------
Handles reading the fleet Excel file.

The Excel file has one sheet per month (e.g., 'February', 'March', 'APRIL'),
plus miscellaneous sheets we should ignore ('Sheet1', 'Detail1', etc.).

Each month sheet has:
  - Meta columns: Sl No, Vehicle No, Model, Driver Name, Cont No
  - Date columns: one per day of the month, headers are either datetime objects
    (cleanest case) or text like '01-Feb', '01.APRL', '5-Aril', '03-Aprl'.
  - Optional 'PLANT IN/OUT' columns interleaved between date columns (March sheet).
  - Optional trailing meta columns: 'Total Trip count', 'Location', 'Time In'.

This loader:
  1. Identifies which sheets are actual month sheets (by name matching known months).
  2. For each month sheet, identifies the date columns vs meta columns.
  3. Returns a tidy (long-format) DataFrame: one row per (vehicle, day) with status.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
from openpyxl import load_workbook


# ------------------------------------------------------------------
# Month recognition
# ------------------------------------------------------------------

# Map sheet-name patterns to (month_number, display_name).
# We match loosely because the sheets are named inconsistently (e.g. 'APRIL').
_MONTH_PATTERNS = {
    "jan": (1, "January"),
    "feb": (2, "February"),
    "mar": (3, "March"),
    "apr": (4, "April"),
    "may": (5, "May"),
    "jun": (6, "June"),
    "jul": (7, "July"),
    "aug": (8, "August"),
    "sep": (9, "September"),
    "oct": (10, "October"),
    "nov": (11, "November"),
    "dec": (12, "December"),
}


def _identify_month(sheet_name: str) -> Optional[Tuple[int, str]]:
    """Return (month_number, display_name) if the sheet name looks like a month."""
    lower = sheet_name.strip().lower()
    for key, (num, name) in _MONTH_PATTERNS.items():
        if lower.startswith(key) or lower == key:
            return (num, name)
    return None


def list_month_sheets(file_path_or_buffer) -> List[Tuple[str, int, str]]:
    """
    Return a list of (sheet_name, month_number, display_name) for every sheet
    in the workbook that looks like a month sheet, sorted by month number.
    """
    wb = load_workbook(file_path_or_buffer, read_only=True, data_only=True)
    found = []
    for sheet_name in wb.sheetnames:
        match = _identify_month(sheet_name)
        if match:
            found.append((sheet_name, match[0], match[1]))
    wb.close()
    return sorted(found, key=lambda t: t[1])


# ------------------------------------------------------------------
# Header parsing
# ------------------------------------------------------------------

# Column-name keywords we recognize as meta (not date) columns.
_META_KEYWORDS = [
    "sl no", "sl.no", "serial",
    "vehicle", "truck",
    "model",
    "driver",
    "cont no", "contact", "phone",
    "total trip", "trip count",
    "location", "time in", "time out",
    "plant in", "plant out", "plant in/out", "plant in /out",
]


def _is_meta_header(value) -> bool:
    if value is None:
        return False
    if not isinstance(value, str):
        return False
    lower = value.strip().lower()
    return any(kw in lower for kw in _META_KEYWORDS)


# Matches date-like text headers: '01-Feb', '01.APRL', '5-Aril', '03-Aprl', '31.MAR'
_DATE_TEXT_RE = re.compile(
    r"^\s*(\d{1,2})[\s\-\.\/](?:jan|feb|mar|apr|apri|aprl|april|ari|may|jun|jul|aug|sep|oct|nov|dec)",
    re.IGNORECASE,
)


def _parse_date_header(value, fallback_year: int, fallback_month: int) -> Optional[datetime]:
    """
    Try to parse a header cell as a date. Returns a datetime or None.

    - If value is already a datetime, return it as-is.
    - If value is a string matching our date-text pattern, extract the day and
      return datetime(fallback_year, fallback_month, day).
    - If value is a plain number 1..31, treat as day in fallback month.
    """
    if isinstance(value, datetime):
        return value

    if value is None:
        return None

    s = str(value).strip()
    if not s:
        return None

    # Pure day number: "1", "2", "31"
    if re.match(r"^\d{1,2}$", s):
        day = int(s)
        if 1 <= day <= 31:
            try:
                return datetime(fallback_year, fallback_month, day)
            except ValueError:
                return None

    # Text date like '01-Feb', '05.APRL', '5-Aril', etc.
    m = _DATE_TEXT_RE.match(s)
    if m:
        day = int(m.group(1))
        # Try to also extract the month abbreviation from the string
        month_match = re.search(
            r"(jan|feb|mar|apr|apri|aprl|april|ari|may|jun|jul|aug|sep|oct|nov|dec)",
            s,
            re.IGNORECASE,
        )
        if month_match:
            abbr = month_match.group(1).lower()[:3]
            # 'ari' is a typo for 'April' in your data — normalize it
            if abbr == "ari":
                abbr = "apr"
            for key, (num, _) in _MONTH_PATTERNS.items():
                if key == abbr:
                    try:
                        return datetime(fallback_year, num, day)
                    except ValueError:
                        return None
        # Fallback to the sheet's month
        try:
            return datetime(fallback_year, fallback_month, day)
        except ValueError:
            return None

    return None


# ------------------------------------------------------------------
# Main loader
# ------------------------------------------------------------------

def load_month_sheet(
    file_path_or_buffer,
    sheet_name: str,
    month_number: int,
    year: Optional[int] = None,
) -> pd.DataFrame:
    """
    Load one month sheet into a tidy long-format DataFrame with columns:
      vehicle, driver, contact, model, date, status_raw, month_name

    Each row represents one vehicle on one day.
    """
    if year is None:
        year = datetime.now().year

    # Read with pandas using openpyxl engine — give us raw cells
    df_raw = pd.read_excel(
        file_path_or_buffer,
        sheet_name=sheet_name,
        header=None,  # we handle headers manually
        engine="openpyxl",
    )

    if df_raw.empty or df_raw.shape[0] < 2:
        return pd.DataFrame(
            columns=["vehicle", "driver", "contact", "model", "date", "status_raw", "month_name"]
        )

    header_row = df_raw.iloc[0].tolist()

    # Classify each column
    col_info: Dict[int, Dict] = {}
    for col_idx, header_val in enumerate(header_row):
        if _is_meta_header(header_val):
            col_info[col_idx] = {"kind": "meta", "name": str(header_val).strip().lower()}
            continue

        parsed_date = _parse_date_header(header_val, year, month_number)
        if parsed_date is not None:
            # Only accept if the parsed date is in the target month
            # (this filters out stray columns like '01.APRL' appearing in March sheet
            #  — we want those to stay visible in the April view, not the March view,
            #  since they represent April data mistakenly placed in the March sheet;
            #  we still keep them because some months span into the next).
            col_info[col_idx] = {
                "kind": "date",
                "date": parsed_date,
            }
            continue

        # Unknown headers are skipped silently
        col_info[col_idx] = {"kind": "skip"}

    # Find key meta columns by keyword in header text
    def find_meta_col(keywords: List[str]) -> Optional[int]:
        for idx, info in col_info.items():
            if info["kind"] != "meta":
                continue
            name = info.get("name", "")
            for kw in keywords:
                if kw in name:
                    return idx
        return None

    vehicle_col = find_meta_col(["vehicle", "truck"])
    driver_col = find_meta_col(["driver"])
    contact_col = find_meta_col(["cont no", "contact", "phone"])
    model_col = find_meta_col(["model"])

    if vehicle_col is None:
        # We can't do anything without a vehicle column
        return pd.DataFrame(
            columns=["vehicle", "driver", "contact", "model", "date", "status_raw", "month_name"]
        )

    date_cols = [(idx, info["date"]) for idx, info in col_info.items() if info["kind"] == "date"]

    # Build long-format records
    records = []
    month_display = _MONTH_PATTERNS.get(
        [k for k, v in _MONTH_PATTERNS.items() if v[0] == month_number][0]
    )[1]

    # Iterate data rows (skip header row)
    for row_idx in range(1, df_raw.shape[0]):
        row = df_raw.iloc[row_idx]

        vehicle_raw = row.iloc[vehicle_col] if vehicle_col is not None else None
        if pd.isna(vehicle_raw) or str(vehicle_raw).strip() == "":
            continue

        vehicle = str(vehicle_raw).strip().upper()
        # Skip obvious junk rows like 'fd' in row 2 of some sheets
        if len(vehicle) < 3 or vehicle == "FD":
            continue

        driver = (
            str(row.iloc[driver_col]).strip()
            if driver_col is not None and pd.notna(row.iloc[driver_col])
            else ""
        )
        contact = (
            str(row.iloc[contact_col]).strip()
            if contact_col is not None and pd.notna(row.iloc[contact_col])
            else ""
        )
        model = (
            str(row.iloc[model_col]).strip()
            if model_col is not None and pd.notna(row.iloc[model_col])
            else ""
        )

        for date_col_idx, the_date in date_cols:
            cell_val = row.iloc[date_col_idx]
            status_raw = ""
            if pd.notna(cell_val):
                status_raw = str(cell_val).strip()

            records.append({
                "vehicle": vehicle,
                "driver": driver,
                "contact": contact,
                "model": model,
                "date": the_date,
                "status_raw": status_raw,
                "month_name": month_display,
            })

    return pd.DataFrame.from_records(records)


def load_all_months(file_path_or_buffer, year: Optional[int] = None) -> pd.DataFrame:
    """
    Load every month sheet in the workbook into a single tidy DataFrame.
    Returns concatenated long-format data with one row per (vehicle, day).
    """
    months = list_month_sheets(file_path_or_buffer)
    all_frames = []
    for sheet_name, month_num, _display in months:
        frame = load_month_sheet(file_path_or_buffer, sheet_name, month_num, year=year)
        if not frame.empty:
            all_frames.append(frame)

    if not all_frames:
        return pd.DataFrame(
            columns=["vehicle", "driver", "contact", "model", "date", "status_raw", "month_name"]
        )

    combined = pd.concat(all_frames, ignore_index=True)
    # Deduplicate in case a date appears in two sheets (e.g. '01.APRL' in both March and April)
    # Keep the row from the sheet whose month matches the date's month when possible.
    combined["_date_month"] = combined["date"].dt.month
    combined["_month_match"] = combined.apply(
        lambda r: r["_date_month"] == _MONTH_PATTERNS[r["month_name"][:3].lower()][0],
        axis=1,
    )
    combined = combined.sort_values(by=["vehicle", "date", "_month_match"], ascending=[True, True, False])
    combined = combined.drop_duplicates(subset=["vehicle", "date"], keep="first")
    combined = combined.drop(columns=["_date_month", "_month_match"])
    return combined.reset_index(drop=True)
