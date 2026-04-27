"""
analytics.py
------------
Status classification, trip counting, route extraction, accident detection,
and all summary-builder functions used by the dashboard.

Status taxonomy:
  DH       - Driver Home
  DP       - Driver Problem
  LP       - Loading Point
  PARK     - Parking
  WAIT     - Waiting
  TNST     - In Transit
  UL       - Unloading
  MT       - Empty Truck Movement
  TRIP     - Active laden trip (origin-destination route, esp. TSK/TSM/JSPL prefix)
  ACCIDENT - Vehicle grounded due to accident
  MAINTENANCE - Vehicle grounded for repair (RM tag in Tata Steel; clutch, tyre, engine, etc.)
  NO_DATA  - Empty cell

Trip counting:
  A "trip" is defined as a cell whose text starts with TSK-, TSM-, or JSPL-
  followed by a destination code. This heuristic matches the human-entered
  Trip column in March with ~90% accuracy.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

import pandas as pd


# ------------------------------------------------------------------
# Regex patterns
# ------------------------------------------------------------------

_RE_DH = re.compile(r"\(DH\)|\bDH\b", re.IGNORECASE)
_RE_DP = re.compile(r"\(DP\)|\bDP\b", re.IGNORECASE)
_RE_LOADING = re.compile(r"\bloading\s*point\b|\bl[\-\s]*point\b", re.IGNORECASE)
_RE_PARKING = re.compile(r"\bparking\b", re.IGNORECASE)
_RE_WAIT = re.compile(r"\bwait\b|\bwt\s+for\b|\bw\.t\.\b", re.IGNORECASE)
_RE_TNST = re.compile(r"^\s*(tnst|t)\s+[a-zA-Z]", re.IGNORECASE)
_RE_UL = re.compile(r"\bul\b|\bunload", re.IGNORECASE)
_RE_MT = re.compile(r"\bmt\b", re.IGNORECASE)

# Accident: explicit ACCIDENT or "Accidental Work"
_RE_ACCIDENT = re.compile(r"\baccident", re.IGNORECASE)

# Repair & Maintenance — covers two cases:
#  1. The literal "RM" code anywhere in the cell (Tata Steel convention: RM = Repair)
#  2. Mechanical descriptions (clutch, tyre, engine, silencer, etc.)
_RE_RM_TAG = re.compile(r"\bRM\b", re.IGNORECASE)
_RE_MAINTENANCE = re.compile(
    r"\b(clutch|tyre|tire|engine|silencer|brake|broken|damage|repair|breakdown|"
    r"break\s*down|starting\s*issue|trolly\s*pati|gadi\s*broken|leak|adjust|"
    r"overhaul|workshop|maintenance|maintainance|maintaninance|service)\b",
    re.IGNORECASE,
)

# A "trip" (laden delivery) — cell starts with TSK-, TSM-, or JSPL- prefix
_RE_TRIP_PREFIX = re.compile(
    r"^\s*(TSK|TSM|JSPL)[\s\-]+([A-Za-z][A-Za-z\s]*)",
    re.IGNORECASE,
)

# Generic route pattern: any ORIGIN-DESTINATION with both being place codes
# (used as fallback for route extraction in April where fewer TSK/TSM/JSPL cells)
_RE_ROUTE = re.compile(
    r"^\s*([A-Z][A-Z\s]{1,10})[\-](\s*[A-Z][A-Za-z\s]+)",
    re.IGNORECASE,
)


# ------------------------------------------------------------------
# Status classification
# ------------------------------------------------------------------

STATUS_ORDER = [
    "ACCIDENT", "MAINTENANCE", "DH", "DP", "LP", "PARK", "WAIT",
    "TNST", "UL", "MT", "TRIP", "NO_DATA",
]

STATUS_LABELS = {
    "ACCIDENT": "Accident",
    "MAINTENANCE": "Repair & Maintenance",
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
    "MAINTENANCE": "#a855f7",
    "ACCIDENT": "#7c3aed",
    "NO_DATA": "#4b5563",
}

def classify_status(cell: str) -> str:
    """
    Classify one status cell.

    Precedence: ACCIDENT > MAINTENANCE > DH > DP > LP > PARK > WAIT > TNST > UL > MT > TRIP.

    MAINTENANCE catches:
      - The literal "RM" code anywhere (Tata Steel: RM = Repair & Maintenance)
      - Mechanical descriptors (clutch, tyre, engine, silencer, etc.)
    """
    if cell is None:
        return "NO_DATA"
    text = str(cell).strip()
    if not text:
        return "NO_DATA"

    if _RE_ACCIDENT.search(text):
        return "ACCIDENT"
    if _RE_RM_TAG.search(text) or _RE_MAINTENANCE.search(text):
        return "MAINTENANCE"
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
    return "TRIP"


def add_status_column(df: pd.DataFrame) -> pd.DataFrame:
    """Add 'status' column (classification) and 'is_trip' column (bool).

    A cell counts as a trip only if:
      - It starts with TSK-, TSM-, or JSPL- followed by a destination
      - AND the destination is not a waiting-state keyword (WT, WAIT, etc.)
      - AND the cell isn't classified as WAIT/PARK/LP/ACCIDENT/MAINTENANCE/DH/DP
    """
    out = df.copy()
    out["status"] = out["status_raw"].apply(classify_status)

    def _is_trip(text, status):
        if status in {"WAIT", "PARK", "LP", "ACCIDENT", "MAINTENANCE", "DH", "DP", "NO_DATA"}:
            return False
        if not text:
            return False
        m = _RE_TRIP_PREFIX.match(str(text).strip())
        if not m:
            return False
        dest = m.group(2).strip().upper()
        bad_dest_prefixes = ("WT", "WAIT", "PARK", "LOADING", "L POINT", "DH", "DP")
        if any(dest.startswith(p) for p in bad_dest_prefixes):
            return False
        return True

    out["is_trip"] = out.apply(
        lambda r: _is_trip(r["status_raw"], r["status"]),
        axis=1,
    )
    return out


# ------------------------------------------------------------------
# Route extraction
# ------------------------------------------------------------------

# Normalize destination/origin aliases
_PLACE_ALIASES = {
    "JSPR": "JSPR", "JAMSHEDPUR": "JSPR", "JSR": "JSPR",
    "PDP": "PDP", "PARADEEP": "PDP", "PARADIP": "PDP",
    "RKL": "RKL", "ROURKELA": "RKL",
    "BLSR": "BLSR", "BALESWAR": "BLSR", "BALASORE": "BLSR",
    "BBSR": "BBSR", "BHUBANESWAR": "BBSR", "BHUBHANESWAR": "BBSR",
    "DKL": "DKL", "DHENKANAL": "DKL", "DHENAKANL": "DKL",
    "JAJPUR": "JAJPUR",
    "CUTTACK": "CUTTACK", "CTC": "CUTTACK",
    "SUNDARGARH": "SUNDARGARH",
    "ANGUL": "ANGUL", "ANG": "ANGUL",
    "BEGUNIA": "BEGUNIA",
    "RAIGARH": "RAIGARH",
    "RAIPUR": "RAIPUR",
    "DHAMRA": "DHAMRA", "DHAMARA": "DHAMRA",
    "CUTTACK": "CUTTACK",
    "KAMAKHYA": "KAMAKHYA",
    "MERAMANDALI": "MERAMANDALI", "MERAMDALI": "MERAMANDALI",
    "KENDRAPARA": "KENDRAPARA", "KENDRAPADA": "KENDRAPARA", "KENDRAPAD": "KENDRAPARA",
    "TANGI": "TANGI",
    "KEONJHAR": "KEONJHAR",
    "JASHIPUR": "JASHIPUR",
    "GHATAGAON": "GHATAGAON", "GHATGOAN": "GHATAGAON",
    "CHOUDWAR": "CHOUDWAR",
}


def _normalize_place(s: str) -> str:
    up = re.sub(r"[^A-Z]", "", str(s).upper())
    return _PLACE_ALIASES.get(up, up)


def extract_route(cell: str) -> Optional[str]:
    """
    Return a normalized route string like 'TSK-PDP' for a cell, or None.

    Matches cells starting with TSK-, TSM-, or JSPL- followed by a real destination.
    Returns the route as 'ORIGIN-DESTINATION' using normalized place codes.
    Waiting-state destinations (WT, WAIT, PARK, etc.) are rejected.
    """
    if not cell:
        return None
    text = str(cell).strip()
    m = _RE_TRIP_PREFIX.match(text)
    if not m:
        return None
    origin = m.group(1).upper()
    destination_raw = m.group(2).strip()
    # Reject waiting/service destinations
    up = destination_raw.upper()
    bad_prefixes = ("WT", "WAIT", "PARK", "LOADING", "L POINT", "DH", "DP")
    if any(up.startswith(p) for p in bad_prefixes):
        return None
    destination = _normalize_place(destination_raw)
    if not destination:
        return None
    return f"{origin}-{destination}"


def add_route_column(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["route"] = out["status_raw"].apply(extract_route)
    return out


# ------------------------------------------------------------------
# Accident vehicles
# ------------------------------------------------------------------

def identify_accident_vehicles(
    df: pd.DataFrame,
    plant_df: Optional[pd.DataFrame] = None,
    min_days: int = 3,
) -> pd.DataFrame:
    """
    Return a DataFrame of vehicles flagged as accident-grounded.

    Checks both:
      - Daily status cells classified as ACCIDENT
      - Plant In/Out notes containing 'accident' (sometimes the data-entry
        person logs accidents in the wrong column)

    A vehicle is flagged if its combined accident-count >= min_days for a month.

    Columns: vehicle, driver, month_name, accident_days, first_date, last_date
    """
    df = df if "status" in df.columns else add_status_column(df)

    # Accident cells from daily data
    acc_daily = df[df["status"] == "ACCIDENT"][
        ["vehicle", "driver", "date", "month_name"]
    ].copy()

    # Accident mentions in plant notes
    if plant_df is not None and not plant_df.empty and "note" in plant_df.columns:
        acc_plant = plant_df[
            plant_df["note"].astype(str).str.contains("accident", case=False, na=False)
        ][["vehicle", "date", "month_name"]].copy()
        acc_plant["driver"] = ""
    else:
        acc_plant = pd.DataFrame(columns=["vehicle", "date", "month_name", "driver"])

    combined = pd.concat([acc_daily, acc_plant], ignore_index=True)
    if combined.empty:
        return pd.DataFrame(
            columns=["vehicle", "driver", "month_name", "accident_days", "first_date", "last_date"]
        )

    # Deduplicate on (vehicle, date, month_name)
    combined = combined.drop_duplicates(subset=["vehicle", "date", "month_name"])

    grouped = (
        combined.groupby(["vehicle", "month_name"])
        .agg(
            driver=("driver", lambda s: next((x for x in s if x), "")),
            accident_days=("date", "count"),
            first_date=("date", "min"),
            last_date=("date", "max"),
        )
        .reset_index()
    )
    grouped = grouped[grouped["accident_days"] >= min_days]
    return grouped.sort_values(
        ["month_name", "accident_days"], ascending=[True, False]
    ).reset_index(drop=True)


# ------------------------------------------------------------------
# Productive-state definition for utilization
# ------------------------------------------------------------------

PRODUCTIVE_STATES = {"TRIP", "UL", "TNST", "LP", "MT"}
# States that EXCLUDE a vehicle-day from utilization denominator entirely:
# (truck isn't "available to do work" on these days)
EXCLUDED_FROM_DENOM = {"NO_DATA", "ACCIDENT", "MAINTENANCE"}


def _utilization_pct(s: pd.Series, row_sum_cols: List[str]) -> float:
    """Compute utilization given a row with count columns."""
    total = sum(int(s.get(c, 0)) for c in row_sum_cols if c not in EXCLUDED_FROM_DENOM)
    prod = sum(int(s.get(c, 0)) for c in PRODUCTIVE_STATES)
    if total <= 0:
        return 0.0
    return round(prod / total * 100, 1)


# ------------------------------------------------------------------
# Vehicle summary
# ------------------------------------------------------------------

def vehicle_summary(df: pd.DataFrame, exclude_accident_vehicles: bool = True) -> pd.DataFrame:
    """
    One row per vehicle with counts for every status + utilization %.

    If exclude_accident_vehicles is True, vehicles whose entire month is accident
    are excluded from the utilization calculation (they still appear, but marked).
    """
    if df.empty:
        return pd.DataFrame()

    df = df if "status" in df.columns else add_status_column(df)
    df = df if "is_trip" in df.columns else add_status_column(df)

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
    for s in STATUS_ORDER:
        if s not in pivot.columns:
            pivot[s] = 0

    # Trip count via heuristic
    trips_per_v = df.groupby("vehicle")["is_trip"].sum().astype(int).to_dict()
    pivot["trips_computed"] = pivot["vehicle"].map(trips_per_v).fillna(0).astype(int)

    # Manual trip count from Excel (takes the max non-null across days; should be
    # the same value repeated for every day of a given month for a vehicle)
    manual_map = (
        df[df["manual_trip_count"].notna()]
        .groupby("vehicle")["manual_trip_count"]
        .max()
    )
    pivot["trips_manual"] = pivot["vehicle"].map(manual_map)

    # Driver
    driver_map = (
        df[df["driver"].astype(str).str.strip() != ""]
        .sort_values("date")
        .groupby("vehicle")["driver"]
        .last()
    )
    pivot["driver"] = pivot["vehicle"].map(driver_map).fillna("")

    # Accident flag
    pivot["is_accident_vehicle"] = pivot["ACCIDENT"] >= 3

    # Utilization
    count_cols = [c for c in STATUS_ORDER if c not in EXCLUDED_FROM_DENOM]
    pivot["active_days"] = pivot[count_cols].sum(axis=1)
    pivot["productive_days"] = pivot[list(PRODUCTIVE_STATES)].sum(axis=1)
    pivot["utilization_pct"] = (
        (pivot["productive_days"] / pivot["active_days"].replace(0, pd.NA) * 100)
        .fillna(0)
        .round(1)
    )
    # Blank out utilization for accident vehicles if requested
    if exclude_accident_vehicles:
        pivot.loc[pivot["is_accident_vehicle"], "utilization_pct"] = None

    ordered = (
        ["vehicle", "driver", "is_accident_vehicle"]
        + STATUS_ORDER
        + ["trips_computed", "trips_manual", "active_days", "productive_days", "utilization_pct"]
    )
    pivot = pivot[ordered]
    return pivot.sort_values(
        by=["is_accident_vehicle", "utilization_pct"],
        ascending=[True, False],
        na_position="last",
    ).reset_index(drop=True)


def driver_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    df = df if "status" in df.columns else add_status_column(df)
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

    # Trips via heuristic
    trips_per_d = df.groupby("driver")["is_trip"].sum().astype(int).to_dict()
    pivot["trips_computed"] = pivot["driver"].map(trips_per_d).fillna(0).astype(int)

    count_cols = [c for c in STATUS_ORDER if c not in EXCLUDED_FROM_DENOM]
    pivot["active_days"] = pivot[count_cols].sum(axis=1)
    pivot["productive_days"] = pivot[list(PRODUCTIVE_STATES)].sum(axis=1)
    pivot["utilization_pct"] = (
        (pivot["productive_days"] / pivot["active_days"].replace(0, pd.NA) * 100)
        .fillna(0)
        .round(1)
    )
    ordered = ["driver"] + STATUS_ORDER + ["trips_computed", "active_days", "productive_days", "utilization_pct"]
    return pivot[ordered].sort_values("utilization_pct", ascending=False).reset_index(drop=True)


def daily_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    df = df if "status" in df.columns else add_status_column(df)
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
    count_cols = [c for c in STATUS_ORDER if c not in EXCLUDED_FROM_DENOM]
    pivot["total_logged"] = pivot[count_cols].sum(axis=1)
    pivot["productive"] = pivot[list(PRODUCTIVE_STATES)].sum(axis=1)
    pivot["utilization_pct"] = (
        (pivot["productive"] / pivot["total_logged"].replace(0, pd.NA) * 100)
        .fillna(0)
        .round(1)
    )
    ordered = ["date"] + STATUS_ORDER + ["total_logged", "productive", "utilization_pct"]
    return pivot[ordered].sort_values("date").reset_index(drop=True)


# ------------------------------------------------------------------
# KPIs
# ------------------------------------------------------------------

def compute_kpis(df: pd.DataFrame) -> Dict:
    if df.empty:
        return {
            "total_vehicles": 0, "active_trips": 0, "drivers_home": 0,
            "idle_waiting": 0, "fleet_util_pct": 0.0,
            "accident_vehicles": 0, "latest_date": None,
            "total_trips_month": 0,
            "trips_manual_total": 0, "trips_computed_total": 0,
            "all_have_manual": False,
            "dh_days_month": 0, "dp_days_month": 0,
            "maintenance_days_month": 0, "parking_days_month": 0,
            "avg_days_per_trip": 0.0, "working_days_total": 0,
        }
    df = df if "status" in df.columns else add_status_column(df)
    latest_date = df["date"].max()
    latest = df[df["date"] == latest_date]

    total_vehicles = df["vehicle"].nunique()
    active_trips = int(latest["status"].isin(["TRIP", "UL"]).sum())
    drivers_home = int((latest["status"] == "DH").sum())
    idle_waiting = int(latest["status"].isin(["WAIT", "PARK"]).sum())

    # Monthly totals (sum across all vehicles + all days in this view)
    dh_days_month = int((df["status"] == "DH").sum())
    dp_days_month = int((df["status"] == "DP").sum())
    maintenance_days_month = int((df["status"] == "MAINTENANCE").sum())
    parking_days_month = int((df["status"] == "PARK").sum())

    # Utilization excluding accident-grounded vehicles
    vs = vehicle_summary(df, exclude_accident_vehicles=True)
    accident_count = int(vs["is_accident_vehicle"].sum()) if not vs.empty else 0
    non_acc = vs[~vs["is_accident_vehicle"]] if not vs.empty else vs
    if not non_acc.empty and non_acc["active_days"].sum() > 0:
        fleet_util = round(
            non_acc["productive_days"].sum() / non_acc["active_days"].sum() * 100, 1
        )
    else:
        fleet_util = 0.0

    # Total trips: only use manual if EVERY vehicle has it; else fallback to computed
    # so the Total Trips KPI and Avg Days/Trip stay internally consistent.
    manual_total = df[df["manual_trip_count"].notna()].groupby("vehicle")["manual_trip_count"].max().sum()
    computed_total = int(df["is_trip"].sum()) if "is_trip" in df.columns else 0
    vehicles_in_view = df["vehicle"].nunique()
    vehicles_with_manual = df[df["manual_trip_count"].notna()]["vehicle"].nunique()
    all_have_manual = vehicles_with_manual == vehicles_in_view and manual_total > 0
    total_trips_month = int(manual_total) if all_have_manual else computed_total

    # Working days = cells NOT in {NO_DATA, ACCIDENT, MAINTENANCE, DP}
    working_excluded = EXCLUDED_FROM_DENOM | {"DP"}
    working_days = int((~df["status"].isin(working_excluded)).sum())
    avg_days_per_trip = round(working_days / total_trips_month, 2) if total_trips_month > 0 else 0.0

    return {
        "total_vehicles": total_vehicles,
        "active_trips": active_trips,
        "drivers_home": drivers_home,
        "idle_waiting": idle_waiting,
        "fleet_util_pct": fleet_util,
        "accident_vehicles": accident_count,
        "latest_date": latest_date,
        "total_trips_month": total_trips_month,
        "trips_manual_total": int(manual_total) if manual_total > 0 else 0,
        "trips_computed_total": computed_total,
        "all_have_manual": all_have_manual,
        "dh_days_month": dh_days_month,
        "dp_days_month": dp_days_month,
        "maintenance_days_month": maintenance_days_month,
        "parking_days_month": parking_days_month,
        "avg_days_per_trip": avg_days_per_trip,
        "working_days_total": working_days,
    }


# ------------------------------------------------------------------
# Route analytics
# ------------------------------------------------------------------

def route_summary(df: pd.DataFrame, plant_df: pd.DataFrame) -> pd.DataFrame:
    """
    For each route (e.g. 'TSK-PDP'), compute:
      - trip_count: how many times this route appears
      - unique_vehicles: how many distinct vehicles ran it
      - avg_dwell_hours: average plant-dwell time for trips on this route

    We link dwell time to route by matching the date: a plant In/Out entry
    attributed to date D is associated with the route cell on date D.
    """
    df = df if "route" in df.columns else add_route_column(df)
    routed = df[df["route"].notna()].copy()
    if routed.empty:
        return pd.DataFrame()

    # Merge in dwell hours from plant_df on (vehicle, date)
    if not plant_df.empty:
        p = plant_df.groupby(["vehicle", "date"])["dwell_hours"].mean().reset_index()
        routed = routed.merge(p, on=["vehicle", "date"], how="left")
    else:
        routed["dwell_hours"] = None

    agg = (
        routed.groupby("route")
        .agg(
            trip_count=("vehicle", "count"),
            unique_vehicles=("vehicle", "nunique"),
            avg_dwell_hours=("dwell_hours", "mean"),
            min_dwell_hours=("dwell_hours", "min"),
            max_dwell_hours=("dwell_hours", "max"),
        )
        .reset_index()
    )
    agg["avg_dwell_hours"] = agg["avg_dwell_hours"].round(2)
    agg["min_dwell_hours"] = agg["min_dwell_hours"].round(2)
    agg["max_dwell_hours"] = agg["max_dwell_hours"].round(2)
    return agg.sort_values("trip_count", ascending=False).reset_index(drop=True)


def route_vehicle_deviation(df: pd.DataFrame, plant_df: pd.DataFrame, route: str) -> pd.DataFrame:
    """
    For a specific route, return per-trip data with deviation from route's avg dwell.
    Columns: vehicle, date, dwell_hours, deviation_hours (positive = slower)
    """
    df = df if "route" in df.columns else add_route_column(df)
    routed = df[df["route"] == route].copy()
    if routed.empty or plant_df.empty:
        return pd.DataFrame()

    p = plant_df.groupby(["vehicle", "date"])["dwell_hours"].mean().reset_index()
    routed = routed.merge(p, on=["vehicle", "date"], how="left")
    valid = routed[routed["dwell_hours"].notna()].copy()
    if valid.empty:
        return pd.DataFrame()

    avg = valid["dwell_hours"].mean()
    valid["avg_dwell"] = round(avg, 2)
    valid["deviation_hours"] = (valid["dwell_hours"] - avg).round(2)
    return valid[["vehicle", "date", "dwell_hours", "avg_dwell", "deviation_hours", "status_raw"]].sort_values(
        "deviation_hours", ascending=False
    ).reset_index(drop=True)


# ------------------------------------------------------------------
# DH/DP audit — exact days per vehicle
# ------------------------------------------------------------------

def dh_dp_detail(df: pd.DataFrame, vehicle: str) -> pd.DataFrame:
    """Return the exact cells classified as DH or DP for one vehicle."""
    df = df if "status" in df.columns else add_status_column(df)
    sub = df[(df["vehicle"] == vehicle) & (df["status"].isin(["DH", "DP"]))].copy()
    return sub[["date", "status", "status_raw", "month_name"]].sort_values("date").reset_index(drop=True)


def status_detail(df: pd.DataFrame, vehicle: str, status: str) -> pd.DataFrame:
    """Return exact cells for one vehicle matching a status code."""
    df = df if "status" in df.columns else add_status_column(df)
    sub = df[(df["vehicle"] == vehicle) & (df["status"] == status)].copy()
    return sub[["date", "status_raw", "month_name"]].sort_values("date").reset_index(drop=True)


# ------------------------------------------------------------------
# Search (Excel-Find equivalent)
# ------------------------------------------------------------------

# ------------------------------------------------------------------
# Trip count reconciliation: manual (Excel) vs computed (heuristic)
# ------------------------------------------------------------------

def trip_reconciliation(df: pd.DataFrame) -> pd.DataFrame:
    """
    For every vehicle that has a manual trip count in the Excel sheet, return:
      vehicle, trips_manual, trips_computed, diff (computed - manual)
    Sorted by absolute diff descending so worst mismatches surface first.
    """
    if df.empty:
        return pd.DataFrame()
    df = df if "status" in df.columns else add_status_column(df)

    # Per-vehicle manual count (one value per vehicle per month, take max)
    manual_per_v = (
        df[df["manual_trip_count"].notna()]
        .groupby("vehicle")["manual_trip_count"].max()
    )
    if manual_per_v.empty:
        return pd.DataFrame()

    # Per-vehicle computed trip count
    computed_per_v = df.groupby("vehicle")["is_trip"].sum().astype(int)

    # Driver name (latest non-empty)
    driver_per_v = (
        df[df["driver"].astype(str).str.strip() != ""]
        .sort_values("date").groupby("vehicle")["driver"].last()
    )

    out = pd.DataFrame({
        "vehicle": manual_per_v.index,
        "driver": [driver_per_v.get(v, "") for v in manual_per_v.index],
        "trips_manual": manual_per_v.values.astype(int),
        "trips_computed": [computed_per_v.get(v, 0) for v in manual_per_v.index],
    })
    out["diff"] = out["trips_computed"] - out["trips_manual"]
    out["abs_diff"] = out["diff"].abs()
    out = out.sort_values("abs_diff", ascending=False).drop(columns=["abs_diff"])
    return out.reset_index(drop=True)


def search_cells(df: pd.DataFrame, query: str, case_sensitive: bool = False) -> pd.DataFrame:
    """Return every daily cell whose status_raw matches the query."""
    if not query or not query.strip() or df.empty:
        return pd.DataFrame()
    q = query.strip()
    pattern = re.escape(q)
    if case_sensitive:
        mask = df["status_raw"].astype(str).str.contains(pattern, regex=True, na=False)
    else:
        mask = df["status_raw"].astype(str).str.contains(pattern, regex=True, case=False, na=False)
    sub = df[mask].copy()
    if sub.empty:
        return pd.DataFrame()
    return sub[["date", "vehicle", "driver", "status_raw", "month_name"]].sort_values(
        ["date", "vehicle"]
    ).reset_index(drop=True)


# ------------------------------------------------------------------
# Data quality warnings
# ------------------------------------------------------------------

def data_quality_warnings(df: pd.DataFrame, plant_df: pd.DataFrame) -> List[str]:
    warnings = []
    if df.empty:
        return ["No data loaded."]

    # 1. Vehicles without any driver name in ANY row across all months
    driver_by_vehicle = df.groupby("vehicle")["driver"].apply(
        lambda s: any(str(x).strip() for x in s)
    )
    no_driver_vehicles = driver_by_vehicle[~driver_by_vehicle].index.tolist()
    if no_driver_vehicles:
        warnings.append(
            f"⚠ {len(no_driver_vehicles)} vehicle(s) have no driver name recorded in any month: "
            f"{', '.join(no_driver_vehicles[:5])}{'…' if len(no_driver_vehicles) > 5 else ''}"
        )

    # 2. Plant in/out entries that couldn't be parsed
    if not plant_df.empty:
        unparseable = plant_df[
            plant_df["in_time"].isna() & plant_df["out_time"].isna() & plant_df["note"].notna()
        ]
        if len(unparseable) > 20:
            warnings.append(
                f"ℹ {len(unparseable)} plant in/out cells contain notes instead of timestamps "
                f"(e.g., service notes like 'Clutch Adjust'). These are shown in the Trip log."
            )

    # 3. Dwell time outliers (> 5 days)
    if not plant_df.empty and plant_df["dwell_hours"].notna().any():
        outliers = plant_df[plant_df["dwell_hours"] > 120]
        if len(outliers) > 0:
            warnings.append(
                f"⚠ {len(outliers)} plant visit(s) have dwell time > 5 days — likely parsing errors "
                f"or cross-month trips. Review before using dwell metrics."
            )

    # 4. Manual vs computed trip count discrepancy
    for month in df["month_name"].unique():
        mdf = df[df["month_name"] == month]
        manual = mdf[mdf["manual_trip_count"].notna()].groupby("vehicle")["manual_trip_count"].max().sum()
        if manual == 0:
            continue
        if "is_trip" not in mdf.columns:
            mdf = add_status_column(mdf)
        computed = int(mdf["is_trip"].sum())
        diff = computed - manual
        pct = abs(diff) / manual * 100 if manual else 0
        if pct > 10:
            warnings.append(
                f"⚠ {month}: computed trips ({computed}) differs from manual Trip column ({int(manual)}) "
                f"by {diff:+d} ({pct:.1f}%). The manual count is authoritative."
            )

    return warnings
