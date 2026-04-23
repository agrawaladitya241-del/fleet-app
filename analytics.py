"""
analytics.py
------------
Classifies each daily status cell into an operational state and produces
summary tables for the dashboard.

Status taxonomy (confirmed with the user):
  DH      - Driver Home (driver on leave, vehicle parked)
  DP      - Driver Problem (driver-side issue, sick/absent/etc.)
  TNST    - Transit (vehicle moving between points)
  UL      - Unloading Point (at destination, unloading)
  LP      - Loading Point (at source, loading; includes "Loading Point Wait For X")
  MT      - Empty Truck Movement (deadhead, running empty)
  WAIT    - Waiting / parked at a waiting spot awaiting dispatch
  PARK    - Parked at a designated parking spot
  TRIP    - Active laden trip between two locations
  NO_DATA - Empty cell / no activity logged
"""

from __future__ import annotations

import re
from typing import Dict, List

import pandas as pd


# ------------------------------------------------------------------
# Status classification
# ------------------------------------------------------------------

# Precompiled regex patterns for robustness.
# IMPORTANT: these patterns match *tags* (DH/DP as standalone words or in parens),
# not substrings inside place names. This is the key bug fix from the old code.

_RE_DH = re.compile(r"\(DH\)|\bDH\b", re.IGNORECASE)
_RE_DP = re.compile(r"\(DP\)|\bDP\b", re.IGNORECASE)

# User clarified: "Loading Point" and "Parking" are LOCATIONS.
# "Wait For Load / Wait For DO / WT FOR X" = WAIT state.
# Precedence: location wins over waiting (per user decision).
_RE_LOADING = re.compile(r"\bloading\s*point\b|\bl\s*point\b", re.IGNORECASE)
_RE_PARKING = re.compile(r"\bparking\b", re.IGNORECASE)
_RE_WAIT = re.compile(r"\bwait\b|\bwt\s+for\b|\bw\.t\.\b", re.IGNORECASE)

# Transit — cell starts with "TNST " or "T " followed by a location.
# We require the space to avoid matching things like "Tata" or "TSK".
_RE_TNST = re.compile(r"^\s*(tnst|t)\s+[a-z]", re.IGNORECASE)

# Unloading — "UL" as a word, "UL JSPR", "Rourkela UL Rourkela", etc.
_RE_UL = re.compile(r"\bul\b|\bunload", re.IGNORECASE)

# Empty-truck movement — " MT" at end, or "MT " at start/middle as a tag.
# Again we require word boundaries to avoid "Dhamra" being flagged.
_RE_MT = re.compile(r"\bmt\b", re.IGNORECASE)


STATUS_ORDER = ["DH", "DP", "LP", "PARK", "WAIT", "TNST", "UL", "MT", "TRIP", "NO_DATA"]

# Human-friendly labels for the UI
STATUS_LABELS = {
    "DH": "Driver Home",
    "DP": "Driver Problem",
    "LP": "Loading Point",
    "PARK": "Parking",
    "WAIT": "Waiting",
    "TNST": "In Transit",
    "UL": "Unloading",
    "MT": "Empty Movement",
    "TRIP": "Active Trip",
    "NO_DATA": "No Data",
}

# Color hints for charts / chips. Ops meaning:
#   green  = productive (TRIP, UL)
#   yellow = in-progress / neutral (TNST, LP, MT)
#   orange = unproductive but excusable (WAIT, PARK)
#   red    = unproductive and costly (DH, DP)
#   gray   = no data
STATUS_COLORS = {
    "TRIP": "#22c55e",
    "UL": "#16a34a",
    "TNST": "#eab308",
    "LP": "#f59e0b",
    "MT": "#fbbf24",
    "WAIT": "#f97316",
    "PARK": "#fb923c",
    "DH": "#ef4444",
    "DP": "#dc2626",
    "NO_DATA": "#4b5563",
}


def classify_status(cell: str) -> str:
    """
    Classify a single status cell into one of the codes in STATUS_ORDER.

    Precedence (first match wins):
      1. NO_DATA if empty
      2. DH if cell has '(DH)' or ' DH' tag
      3. DP if cell has '(DP)' or ' DP' tag
      4. LP if cell contains 'Loading Point' or 'L Point'  (location wins over WAIT)
      5. PARK if cell contains 'Parking'                   (location wins over WAIT)
      6. WAIT if cell contains 'Wait' or 'WT FOR'
      7. TNST if cell starts with 'TNST ' or 'T '
      8. UL   if cell contains ' UL ' / starts with 'UL'
      9. MT   if cell contains ' MT ' / ends with ' MT'
     10. TRIP otherwise
    """
    if cell is None:
        return "NO_DATA"

    text = str(cell).strip()
    if not text:
        return "NO_DATA"

    if _RE_DH.search(text):
        return "DH"
    if _RE_DP.search(text):
        return "DP"
    if _RE_LOADING.search(text):
        return "LP"
    if _RE_PARKING.search(text):
        return "PARK"
    if _RE_WAIT.search(text):
        return "WAIT"
    if _RE_TNST.match(text):
        return "TNST"
    if _RE_UL.search(text):
        return "UL"
    if _RE_MT.search(text):
        return "MT"

    # Default: treat as an active laden trip (e.g. "Baharagora Jamshedpur")
    return "TRIP"


def add_status_column(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with a new 'status' column classifying status_raw."""
    out = df.copy()
    out["status"] = out["status_raw"].apply(classify_status)
    return out


# ------------------------------------------------------------------
# Summary builders
# ------------------------------------------------------------------

# What we count as "productive" (contributing to utilization).
PRODUCTIVE_STATES = {"TRIP", "UL", "TNST", "LP", "MT"}

# Non-data states that should not count in the denominator.
EXCLUDE_FROM_DENOMINATOR = {"NO_DATA"}


def vehicle_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    One row per vehicle. Columns: vehicle, driver, plus a count column for each
    status code, total active days, and a utilization percentage.
    """
    if df.empty:
        return pd.DataFrame()

    df = add_status_column(df) if "status" not in df.columns else df

    # Count each status per vehicle
    pivot = (
        df.pivot_table(
            index="vehicle",
            columns="status",
            values="date",
            aggfunc="count",
            fill_value=0,
        )
        .reset_index()
    )

    # Ensure all expected columns exist even if a status never appears
    for s in STATUS_ORDER:
        if s not in pivot.columns:
            pivot[s] = 0

    # Attach driver name (most recent non-empty driver for that vehicle)
    driver_map = (
        df[df["driver"].astype(str).str.strip() != ""]
        .sort_values("date")
        .groupby("vehicle")["driver"]
        .last()
    )
    pivot["driver"] = pivot["vehicle"].map(driver_map).fillna("")

    # Active days = days with any status other than NO_DATA
    pivot["active_days"] = pivot[
        [c for c in STATUS_ORDER if c != "NO_DATA"]
    ].sum(axis=1)

    # Productive days = days in PRODUCTIVE_STATES
    pivot["productive_days"] = pivot[list(PRODUCTIVE_STATES)].sum(axis=1)

    # Utilization = productive / active, as percentage (0 if active_days == 0)
    pivot["utilization_pct"] = (
        (pivot["productive_days"] / pivot["active_days"].replace(0, pd.NA) * 100)
        .fillna(0)
        .round(1)
    )

    # Friendly column order
    ordered = (
        ["vehicle", "driver"]
        + STATUS_ORDER
        + ["active_days", "productive_days", "utilization_pct"]
    )
    pivot = pivot[ordered]
    return pivot.sort_values(by="utilization_pct", ascending=False).reset_index(drop=True)


def daily_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    One row per date. Columns: date, count of each status.
    Useful for trend charts.
    """
    if df.empty:
        return pd.DataFrame()

    df = add_status_column(df) if "status" not in df.columns else df

    pivot = (
        df.pivot_table(
            index="date",
            columns="status",
            values="vehicle",
            aggfunc="count",
            fill_value=0,
        )
        .reset_index()
    )

    for s in STATUS_ORDER:
        if s not in pivot.columns:
            pivot[s] = 0

    pivot["total_logged"] = pivot[[c for c in STATUS_ORDER if c != "NO_DATA"]].sum(axis=1)
    pivot["productive"] = pivot[list(PRODUCTIVE_STATES)].sum(axis=1)
    pivot["utilization_pct"] = (
        (pivot["productive"] / pivot["total_logged"].replace(0, pd.NA) * 100)
        .fillna(0)
        .round(1)
    )

    ordered = ["date"] + STATUS_ORDER + ["total_logged", "productive", "utilization_pct"]
    return pivot[ordered].sort_values("date").reset_index(drop=True)


def driver_summary(df: pd.DataFrame) -> pd.DataFrame:
    """One row per driver with aggregated status counts."""
    if df.empty:
        return pd.DataFrame()

    df = add_status_column(df) if "status" not in df.columns else df
    # Drop rows with empty drivers
    df = df[df["driver"].astype(str).str.strip() != ""]

    if df.empty:
        return pd.DataFrame()

    pivot = (
        df.pivot_table(
            index="driver",
            columns="status",
            values="date",
            aggfunc="count",
            fill_value=0,
        )
        .reset_index()
    )

    for s in STATUS_ORDER:
        if s not in pivot.columns:
            pivot[s] = 0

    pivot["active_days"] = pivot[[c for c in STATUS_ORDER if c != "NO_DATA"]].sum(axis=1)
    pivot["productive_days"] = pivot[list(PRODUCTIVE_STATES)].sum(axis=1)
    pivot["utilization_pct"] = (
        (pivot["productive_days"] / pivot["active_days"].replace(0, pd.NA) * 100)
        .fillna(0)
        .round(1)
    )

    ordered = ["driver"] + STATUS_ORDER + ["active_days", "productive_days", "utilization_pct"]
    return pivot[ordered].sort_values("utilization_pct", ascending=False).reset_index(drop=True)


# ------------------------------------------------------------------
# KPIs for the top-of-dashboard cards
# ------------------------------------------------------------------

def compute_kpis(df: pd.DataFrame) -> Dict[str, float]:
    """
    Compute top-line KPIs for the current selection.

    Returns:
      total_vehicles:   unique vehicles in data
      active_trips:     count of TRIP or UL cells on the latest logged date
      drivers_home:     count of DH cells on the latest logged date
      idle_waiting:     count of WAIT + PARK cells on the latest logged date
      fleet_util_pct:   overall productive / active across the selection
    """
    if df.empty:
        return {
            "total_vehicles": 0,
            "active_trips": 0,
            "drivers_home": 0,
            "idle_waiting": 0,
            "fleet_util_pct": 0.0,
            "latest_date": None,
        }

    df = add_status_column(df) if "status" not in df.columns else df

    latest_date = df["date"].max()
    latest = df[df["date"] == latest_date]

    total_vehicles = df["vehicle"].nunique()
    active_trips = int(latest["status"].isin(["TRIP", "UL"]).sum())
    drivers_home = int((latest["status"] == "DH").sum())
    idle_waiting = int(latest["status"].isin(["WAIT", "PARK"]).sum())

    active_mask = df["status"] != "NO_DATA"
    productive_mask = df["status"].isin(PRODUCTIVE_STATES)
    active_count = int(active_mask.sum())
    productive_count = int(productive_mask.sum())
    fleet_util = round(productive_count / active_count * 100, 1) if active_count else 0.0

    return {
        "total_vehicles": total_vehicles,
        "active_trips": active_trips,
        "drivers_home": drivers_home,
        "idle_waiting": idle_waiting,
        "fleet_util_pct": fleet_util,
        "latest_date": latest_date,
    }
