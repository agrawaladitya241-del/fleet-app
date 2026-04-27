"""
app.py — Fleet Intelligence Dashboard v2
-----------------------------------------
Seven tabs:
  1. Overview          — KPIs + daily trend
  2. Vehicles          — per-vehicle metrics with drill-down
  3. Drivers           — per-driver metrics
  4. Routes            — route-level analysis + per-truck deviation
  5. Accident Vehicles — grounded vehicles
  6. Audit / Verify    — search panel + drill-down for accuracy checking
  7. Raw Data          — full daily log, filterable, downloadable

Deploys on Streamlit Community Cloud, no login required.
"""

from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

import data_loader
import analytics

# ==================================================================
# Page config + theme
# ==================================================================

st.set_page_config(
    page_title="Fleet Intelligence · TSK",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap');

  html, body, [class*="css"] { font-family: 'IBM Plex Sans', -apple-system, sans-serif !important; }

  .stApp { background: #0b0d10; }

  .block-container {
    padding-top: 1.75rem;
    padding-bottom: 4rem;
    max-width: 1500px;
  }

  h1, h2, h3, h4 { font-family: 'IBM Plex Sans', sans-serif !important; letter-spacing: -0.01em; color: #f5f5f5; }
  h1 {
    font-weight: 700;
    font-size: 1.9rem !important;
    border-bottom: 1px solid #1f2328;
    padding-bottom: 0.75rem;
    margin-bottom: 0.25rem !important;
  }
  h2 {
    font-weight: 600;
    font-size: 1.15rem !important;
    margin-top: 1.8rem !important;
    color: #e5e7eb;
  }
  h3 {
    font-weight: 500;
    font-size: 0.85rem !important;
    color: #9aa3b2;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 1rem !important;
    margin-bottom: 0.5rem !important;
  }

  .page-subtitle {
    color: #8b93a1;
    font-size: 0.9rem;
    margin-bottom: 1.5rem;
    font-weight: 400;
  }

  /* KPI cards */
  .kpi-card {
    background: #11141a;
    border: 1px solid #1f2328;
    border-radius: 6px;
    padding: 1.1rem 1.25rem;
    height: 100%;
  }
  .kpi-label {
    color: #8b93a1;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.5rem;
  }
  .kpi-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 2rem;
    font-weight: 700;
    color: #f5f5f5;
    line-height: 1;
  }
  .kpi-unit { color: #8b93a1; font-size: 0.95rem; font-weight: 400; margin-left: 0.25rem; }
  .kpi-sub { color: #6b7280; font-size: 0.75rem; margin-top: 0.4rem; }
  .kpi-card.accent-green .kpi-value { color: #22c55e; }
  .kpi-card.accent-red   .kpi-value { color: #ef4444; }
  .kpi-card.accent-amber .kpi-value { color: #f59e0b; }
  .kpi-card.accent-blue  .kpi-value { color: #60a5fa; }
  .kpi-card.accent-purple .kpi-value { color: #a855f7; }

  /* Sidebar */
  section[data-testid="stSidebar"] { background: #0f1216; border-right: 1px solid #1f2328; }
  section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 { color: #e5e7eb; }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] { gap: 0; border-bottom: 1px solid #1f2328; overflow-x: auto; }
  .stTabs [data-baseweb="tab"] {
    background: transparent; color: #8b93a1; font-weight: 500;
    padding: 0.65rem 1.1rem; border: none; border-bottom: 2px solid transparent;
    white-space: nowrap;
  }
  .stTabs [aria-selected="true"] {
    color: #f5f5f5 !important;
    border-bottom: 2px solid #f59e0b !important;
    background: transparent !important;
  }

  .stDataFrame { border: 1px solid #1f2328; border-radius: 6px; }

  [data-testid="stFileUploader"] section {
    background: #11141a;
    border: 1px dashed #2a3039;
    border-radius: 6px;
  }

  .stAlert { background: #11141a; border: 1px solid #1f2328; border-radius: 6px; }

  /* Hide footer only. Keep the header visible so users can re-open the sidebar
     after collapsing it. */
  footer { visibility: hidden; }
  header[data-testid="stHeader"] { background: transparent; }

  /* Custom warning/info boxes */
  .note-box {
    background: #14181e;
    border-left: 3px solid #f59e0b;
    padding: 0.6rem 0.9rem;
    border-radius: 3px;
    color: #d1d5db;
    font-size: 0.85rem;
    margin: 0.5rem 0;
  }
  .note-box.info { border-left-color: #60a5fa; }
  .note-box.success { border-left-color: #22c55e; }
  .note-box.danger { border-left-color: #ef4444; }

  /* Status chip (used inline) */
  .chip {
    display: inline-block; padding: 0.1rem 0.45rem; border-radius: 3px;
    font-size: 0.7rem; font-weight: 700; font-family: 'JetBrains Mono', monospace;
    margin: 0 0.2rem;
  }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def kpi_card(label: str, value, unit: str = "", sub: str = "", accent: str = "") -> str:
    accent_cls = f"accent-{accent}" if accent else ""
    unit_html = f'<span class="kpi-unit">{unit}</span>' if unit else ""
    sub_html = f'<div class="kpi-sub">{sub}</div>' if sub else ""
    return f"""
    <div class="kpi-card {accent_cls}">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}{unit_html}</div>
      {sub_html}
    </div>
    """


def note(msg: str, kind: str = "info"):
    st.markdown(f'<div class="note-box {kind}">{msg}</div>', unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def load_all(file_bytes: bytes, year: int):
    buf = io.BytesIO(file_bytes)
    daily, plant = data_loader.load_all_months(buf, year=year)
    if daily.empty:
        return daily, plant
    daily = analytics.add_status_column(daily)
    daily = analytics.add_route_column(daily)
    return daily, plant


# ==================================================================
# Header
# ==================================================================

st.markdown("# Fleet Intelligence")
st.markdown(
    '<div class="page-subtitle">Daily operations dashboard · TSK/TSM flatbed fleet · Angul depot</div>',
    unsafe_allow_html=True,
)

# ==================================================================
# Sidebar: upload + controls
# ==================================================================

with st.sidebar:
    st.markdown("### Data")
    uploaded = st.file_uploader(
        "Upload fleet report (.xlsx)",
        type=["xlsx"],
        help="Multi-sheet workbook with one sheet per month.",
    )
    year = st.number_input(
        "Reporting year",
        min_value=2020,
        max_value=2100,
        value=datetime.now().year,
        help="Used when headers contain day+month but no year.",
    )

if not uploaded:
    st.info(
        "Upload a fleet report Excel file to begin. Expected format: "
        "one sheet per month (e.g. `February`, `March`, `APRIL`) with one row per vehicle "
        "and one column per day."
    )
    st.stop()

file_bytes = uploaded.getvalue()

with st.spinner("Loading workbook…"):
    try:
        daily_all, plant_all = load_all(file_bytes, int(year))
    except Exception as e:
        st.error(f"Couldn't read that file: {e}")
        st.stop()

if daily_all.empty:
    st.warning(
        "No month sheets were found. Expected sheet names like `February`, `March`, `APRIL`."
    )
    st.stop()

# ==================================================================
# Sidebar: filters
# ==================================================================

available_months = (
    daily_all[["month_name", "date"]]
    .assign(_m=lambda d: d["date"].dt.month)
    .drop_duplicates(subset=["month_name"])
    .sort_values("_m", ascending=False)["month_name"]
    .tolist()
)

with st.sidebar:
    st.markdown("### View")
    month_options = ["All months"] + available_months
    default_idx = 1 if len(month_options) > 1 else 0
    selected_month = st.selectbox("Month", month_options, index=default_idx)

    st.markdown("### Filter")
    all_drivers = sorted([d for d in daily_all["driver"].unique() if d and str(d).strip()])
    driver_filter = st.multiselect("Driver", all_drivers)
    all_vehicles = sorted(daily_all["vehicle"].unique())
    vehicle_filter = st.multiselect("Vehicle", all_vehicles)

    show_accidents = st.checkbox(
        "Include accident vehicles in Vehicles tab",
        value=True,
        help="Accident vehicles are always shown in the Accident Vehicles tab. "
             "This toggle controls whether they also appear in the main Vehicles list.",
    )

# Apply filters
daily = daily_all.copy()
if selected_month != "All months":
    daily = daily[daily["month_name"] == selected_month]
if driver_filter:
    daily = daily[daily["driver"].isin(driver_filter)]
if vehicle_filter:
    daily = daily[daily["vehicle"].isin(vehicle_filter)]

plant = plant_all.copy()
if selected_month != "All months" and not plant.empty:
    plant = plant[plant["month_name"] == selected_month]
if vehicle_filter and not plant.empty:
    plant = plant[plant["vehicle"].isin(vehicle_filter)]

if daily.empty:
    st.warning("No data matches the selected filters.")
    st.stop()

# ==================================================================
# KPIs
# ==================================================================

kpis = analytics.compute_kpis(daily)
latest = kpis["latest_date"]
latest_str = latest.strftime("%d %b %Y") if latest is not None else "—"

st.markdown(
    f"<div style='color:#8b93a1; font-size:0.85rem; margin-bottom:1rem;'>"
    f"Snapshot: <strong style='color:#d1d5db;'>{selected_month}</strong> · "
    f"Latest day logged: <strong style='color:#d1d5db;'>{latest_str}</strong> · "
    f"Vehicles: <strong style='color:#d1d5db;'>{kpis['total_vehicles']}</strong>"
    f"</div>",
    unsafe_allow_html=True,
)

st.markdown("### Top-line metrics")
k1, k2, k3, k4, k5, k6 = st.columns(6)
with k1:
    st.markdown(
        kpi_card("Trips (manual)", f"{kpis['trips_manual_total']:,}", accent="green",
                 sub="from Excel Trip/Status col"),
        unsafe_allow_html=True,
    )
with k2:
    st.markdown(
        kpi_card("Trips (computed)", f"{kpis['trips_computed_total']:,}", accent="green",
                 sub="TSK/TSM/JSPL heuristic"),
        unsafe_allow_html=True,
    )
with k3:
    st.markdown(
        kpi_card("Avg days / trip", kpis.get("avg_days_per_trip", 0), accent="blue",
                 sub="working days ÷ trips"),
        unsafe_allow_html=True,
    )
with k4:
    st.markdown(
        kpi_card("Fleet utilization", kpis["fleet_util_pct"], unit="%", accent="blue",
                 sub="excl. accident, R&M, DP"),
        unsafe_allow_html=True,
    )
with k5:
    st.markdown(
        kpi_card("Accident vehicles", kpis["accident_vehicles"], accent="purple",
                 sub="grounded for month"),
        unsafe_allow_html=True,
    )
with k6:
    st.markdown(
        kpi_card("Active trips today", kpis["active_trips"], accent="green",
                 sub=f"of {kpis['total_vehicles']} vehicles"),
        unsafe_allow_html=True,
    )

st.markdown("### Day breakdown for this period")
d1, d2, d3, d4 = st.columns(4)
with d1:
    st.markdown(
        kpi_card("DH days", kpis["dh_days_month"], accent="red",
                 sub="Driver Home (total this month)"),
        unsafe_allow_html=True,
    )
with d2:
    st.markdown(
        kpi_card("DP days", kpis["dp_days_month"], accent="red",
                 sub="Driver Problem (total this month)"),
        unsafe_allow_html=True,
    )
with d3:
    st.markdown(
        kpi_card("Maintenance days", kpis["maintenance_days_month"], accent="purple",
                 sub="RM/repair (total this month)"),
        unsafe_allow_html=True,
    )
with d4:
    st.markdown(
        kpi_card("Parking days", kpis["parking_days_month"], accent="amber",
                 sub="vehicle parked (total this month)"),
        unsafe_allow_html=True,
    )

# Data quality warnings
warnings = analytics.data_quality_warnings(daily_all, plant_all)
if warnings:
    with st.expander(f"Data quality notes ({len(warnings)})", expanded=False):
        for w in warnings:
            st.markdown(f"- {w}")

# ==================================================================
# Tabs
# ==================================================================

tab_overview, tab_vehicles, tab_drivers, tab_routes, tab_accidents, tab_audit, tab_raw = st.tabs(
    ["Overview", "Vehicles", "Drivers", "Routes", "Accident Vehicles", "Audit / Verify", "Raw Data"]
)

# ---------- Overview ----------
with tab_overview:
    st.markdown("## Daily status distribution")
    ds = analytics.daily_summary(daily)
    if ds.empty:
        note("Not enough data to chart.", "info")
    else:
        status_cols = [c for c in analytics.STATUS_ORDER if c != "NO_DATA"]
        melted = ds.melt(id_vars=["date"], value_vars=status_cols, var_name="status", value_name="count")
        fig = px.bar(
            melted, x="date", y="count", color="status",
            color_discrete_map=analytics.STATUS_COLORS,
            category_orders={"status": status_cols},
            labels={"date": "", "count": "Vehicles", "status": "Status"},
        )
        fig.update_layout(
            plot_bgcolor="#0b0d10", paper_bgcolor="#0b0d10",
            font=dict(family="IBM Plex Sans", color="#d1d5db"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor="rgba(0,0,0,0)"),
            margin=dict(l=20, r=20, t=40, b=20), height=420,
            xaxis=dict(gridcolor="#1f2328", showgrid=False), yaxis=dict(gridcolor="#1f2328"),
            bargap=0.15,
        )
        for t in fig.data:
            t.name = analytics.STATUS_LABELS.get(t.name, t.name)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("## Utilization trend")
        fig2 = px.line(ds, x="date", y="utilization_pct", markers=True,
                       labels={"date": "", "utilization_pct": "Utilization %"})
        fig2.update_traces(line_color="#60a5fa", marker=dict(size=6))
        fig2.update_layout(
            plot_bgcolor="#0b0d10", paper_bgcolor="#0b0d10",
            font=dict(family="IBM Plex Sans", color="#d1d5db"),
            margin=dict(l=20, r=20, t=20, b=20), height=260,
            xaxis=dict(gridcolor="#1f2328", showgrid=False),
            yaxis=dict(gridcolor="#1f2328", range=[0, 105]),
        )
        st.plotly_chart(fig2, use_container_width=True)

# ---------- Vehicles ----------
with tab_vehicles:
    vs = analytics.vehicle_summary(daily, exclude_accident_vehicles=True)
    if vs.empty:
        note("No vehicle data.", "info")
    else:
        if not show_accidents:
            vs_main = vs[~vs["is_accident_vehicle"]]
        else:
            vs_main = vs

        # Trip column check
        has_manual = vs["trips_manual"].notna().any()
        if has_manual:
            note(
                "The <strong>trips_manual</strong> column comes from the Excel Trip column. "
                "<strong>trips_computed</strong> is our heuristic (TSK/TSM/JSPL prefix). "
                "Compare the two to verify accuracy.",
                "info",
            )
        else:
            note(
                "No manual Trip column found in this month's sheet. "
                "<strong>trips_computed</strong> uses our heuristic — verify against Excel if possible.",
                "info",
            )

        st.markdown("## Top performers")
        top = vs_main.dropna(subset=["utilization_pct"]).head(10)
        st.dataframe(
            top,
            use_container_width=True,
            hide_index=True,
            column_config={
                "utilization_pct": st.column_config.ProgressColumn(
                    "Utilization %", min_value=0, max_value=100, format="%.1f%%",
                ),
                "is_accident_vehicle": st.column_config.CheckboxColumn("Accident"),
            },
        )

        st.markdown("## Flagged vehicles")
        note("Vehicles with <strong>utilization &lt; 40%</strong>, <strong>DH ≥ 3 days</strong>, or <strong>DP ≥ 2 days</strong>. Needs manager follow-up.", "danger")
        flagged = vs_main[
            ((vs_main["utilization_pct"] < 40) & vs_main["utilization_pct"].notna())
            | (vs_main["DH"] >= 3)
            | (vs_main["DP"] >= 2)
        ].sort_values("utilization_pct", na_position="first")
        if flagged.empty:
            note("No vehicles flagged.", "success")
        else:
            st.dataframe(
                flagged, use_container_width=True, hide_index=True,
                column_config={
                    "utilization_pct": st.column_config.ProgressColumn(
                        "Utilization %", min_value=0, max_value=100, format="%.1f%%"),
                    "is_accident_vehicle": st.column_config.CheckboxColumn("Accident"),
                },
            )

        st.markdown("## Day breakdown per vehicle")
        note(
            "How many days each vehicle spent in each unproductive state. "
            "Filter by clicking the column headers to sort. "
            "<strong>DH</strong> = Driver Home · <strong>DP</strong> = Driver Problem · "
            "<strong>MAINTENANCE</strong> = repair/RM · <strong>PARK</strong> = parked.",
            "info",
        )
        breakdown_cols = ["vehicle", "driver", "DH", "DP", "MAINTENANCE", "PARK",
                          "ACCIDENT", "trips_computed", "trips_manual", "active_days",
                          "utilization_pct"]
        breakdown_cols = [c for c in breakdown_cols if c in vs_main.columns]
        breakdown_df = vs_main[breakdown_cols].copy()
        # Sort by total unproductive days
        breakdown_df["_unprod"] = (
            breakdown_df.get("DH", 0) + breakdown_df.get("DP", 0)
            + breakdown_df.get("MAINTENANCE", 0) + breakdown_df.get("PARK", 0)
        )
        breakdown_df = breakdown_df.sort_values("_unprod", ascending=False).drop(columns=["_unprod"])
        st.dataframe(
            breakdown_df, use_container_width=True, hide_index=True,
            column_config={
                "utilization_pct": st.column_config.ProgressColumn(
                    "Utilization %", min_value=0, max_value=100, format="%.1f%%"),
            },
        )

        # ---- Trip count reconciliation ----
        rec = analytics.trip_reconciliation(daily)
        if not rec.empty:
            st.markdown("## Trip count reconciliation: manual vs computed")
            exact = (rec["diff"] == 0).sum()
            within1 = (rec["diff"].abs() <= 1).sum()
            off2plus = (rec["diff"].abs() > 1).sum()
            total_manual = int(rec["trips_manual"].sum())
            total_computed = int(rec["trips_computed"].sum())
            note(
                f"Comparing the manual trip count from the Excel sheet against our "
                f"computed count (cells starting with TSK/TSM/JSPL). "
                f"<strong>{exact}</strong> exact matches · <strong>{within1}</strong> within ±1 · "
                f"<strong>{off2plus}</strong> off by 2+. "
                f"Fleet total: manual <strong>{total_manual}</strong> vs computed <strong>{total_computed}</strong>. "
                f"Vehicles with the largest discrepancies are listed first — these are most likely "
                f"data entry errors or genuine cells our heuristic missed.",
                "info" if off2plus < 20 else "danger",
            )
            st.dataframe(rec, use_container_width=True, hide_index=True)

        st.markdown("## All vehicles")
        st.dataframe(
            vs_main, use_container_width=True, hide_index=True,
            column_config={
                "utilization_pct": st.column_config.ProgressColumn(
                    "Utilization %", min_value=0, max_value=100, format="%.1f%%"),
                "is_accident_vehicle": st.column_config.CheckboxColumn("Accident"),
            },
        )

        # Drill-down
        st.markdown("## Vehicle drill-down")
        veh_to_inspect = st.selectbox(
            "Pick a vehicle to see exact DH/DP days and all its status cells",
            options=sorted(vs["vehicle"].tolist()),
            key="vehicle_drill",
        )
        if veh_to_inspect:
            colA, colB = st.columns(2)
            with colA:
                st.markdown("### Driver Home days")
                dh_df = analytics.status_detail(daily, veh_to_inspect, "DH")
                if dh_df.empty:
                    note("No DH days for this vehicle.", "success")
                else:
                    dh_display = dh_df.copy()
                    dh_display["date"] = dh_display["date"].dt.strftime("%d %b")
                    st.dataframe(dh_display, use_container_width=True, hide_index=True)
            with colB:
                st.markdown("### Driver Problem days")
                dp_df = analytics.status_detail(daily, veh_to_inspect, "DP")
                if dp_df.empty:
                    note("No DP days for this vehicle.", "success")
                else:
                    dp_display = dp_df.copy()
                    dp_display["date"] = dp_display["date"].dt.strftime("%d %b")
                    st.dataframe(dp_display, use_container_width=True, hide_index=True)

            st.markdown("### All status cells for this vehicle")
            v_daily = daily[daily["vehicle"] == veh_to_inspect][
                ["date", "status", "status_raw", "month_name"]
            ].sort_values("date")
            v_daily["date"] = v_daily["date"].dt.strftime("%Y-%m-%d")
            st.dataframe(v_daily, use_container_width=True, hide_index=True, height=300)

# ---------- Drivers ----------
with tab_drivers:
    ds_driver = analytics.driver_summary(daily)
    if ds_driver.empty:
        note("No driver data.", "info")
    else:
        st.markdown("## Driver performance")
        st.dataframe(
            ds_driver, use_container_width=True, hide_index=True,
            column_config={
                "utilization_pct": st.column_config.ProgressColumn(
                    "Utilization %", min_value=0, max_value=100, format="%.1f%%"),
            },
        )

# ---------- Routes ----------
with tab_routes:
    rs = analytics.route_summary(daily, plant)
    if rs.empty:
        note(
            "No routes detected in this view. Route extraction requires cells starting with "
            "<strong>TSK-</strong>, <strong>TSM-</strong>, or <strong>JSPL-</strong> followed by a destination "
            "(the convention used in March and April sheets). "
            "If you're viewing February, note that its cells use a space-separated "
            "'Origin Destination' format that can't be reliably auto-parsed.",
            "info",
        )
    else:
        st.markdown("## Route summary")
        note(
            "Each row is a unique <strong>origin-destination</strong> route. "
            "<strong>avg_dwell_hours</strong> is the average plant-visit duration from "
            "Plant In/Out timestamps. Routes with no dwell data mean timestamps couldn't be parsed.",
            "info",
        )
        st.dataframe(rs, use_container_width=True, hide_index=True)

        # Per-route deviation analysis
        st.markdown("## Route deviation analysis")
        st.markdown(
            "Pick a route to see which trucks were fastest or slowest on it. "
            "**Positive deviation = slower than fleet average.**"
        )
        route_pick = st.selectbox("Route", options=rs["route"].tolist(), key="route_pick")
        if route_pick:
            dev = analytics.route_vehicle_deviation(daily, plant, route_pick)
            if dev.empty:
                note("No dwell data available for this route.", "info")
            else:
                dev_display = dev.copy()
                dev_display["date"] = dev_display["date"].dt.strftime("%d %b %Y")
                st.dataframe(dev_display, use_container_width=True, hide_index=True)

# ---------- Accident Vehicles ----------
with tab_accidents:
    st.markdown("## Accident-grounded vehicles")
    acc = analytics.identify_accident_vehicles(
        daily_all if selected_month == "All months" else daily,
        plant_df=plant_all if selected_month == "All months" else plant,
    )
    if acc.empty:
        note("No accident-grounded vehicles in this view.", "success")
    else:
        note(
            f"Found <strong>{len(acc)} vehicle(s)</strong> with 3 or more days marked "
            f"<strong>ACCIDENT</strong> or <strong>Accidental Work</strong> in the source sheet. "
            "These are excluded from fleet utilization calculations.",
            "danger",
        )
        acc_display = acc.copy()
        acc_display["first_date"] = acc_display["first_date"].dt.strftime("%d %b %Y")
        acc_display["last_date"] = acc_display["last_date"].dt.strftime("%d %b %Y")
        st.dataframe(acc_display, use_container_width=True, hide_index=True)

# ---------- Audit / Verify ----------
with tab_audit:
    st.markdown("## Search (Excel Find equivalent)")
    st.markdown(
        "Type any text and see every cell in the source sheet containing it — "
        "vehicle, date, and the exact cell text. Use this to verify counts by eye."
    )
    q_col1, q_col2 = st.columns([4, 1])
    with q_col1:
        query = st.text_input("Search text", placeholder="e.g. DH, Wait For Load, ACCIDENT, Paradeep")
    with q_col2:
        case_sensitive = st.checkbox("Case-sensitive", value=False)

    search_scope = st.radio(
        "Search scope", ["Current view", "All months"], horizontal=True, key="search_scope"
    )
    scope_df = daily if search_scope == "Current view" else daily_all

    if query:
        results = analytics.search_cells(scope_df, query, case_sensitive=case_sensitive)
        if results.empty:
            note(f"No cells found matching '{query}'.", "info")
        else:
            st.markdown(f"### {len(results)} match(es)")
            results_display = results.copy()
            results_display["date"] = results_display["date"].dt.strftime("%Y-%m-%d")
            st.dataframe(results_display, use_container_width=True, hide_index=True, height=400)

    st.divider()
    st.markdown("## Count verification")
    st.markdown(
        "Pick any status, and see every matching cell so you can cross-check our counts against the Excel file."
    )
    status_to_audit = st.selectbox(
        "Status to audit",
        options=[s for s in analytics.STATUS_ORDER if s != "NO_DATA"],
        format_func=lambda s: f"{s} — {analytics.STATUS_LABELS.get(s, s)}",
    )
    if status_to_audit:
        audit_df = daily[daily["status"] == status_to_audit].copy()
        st.markdown(f"### {len(audit_df)} cell(s) classified as {status_to_audit}")
        if not audit_df.empty:
            audit_display = audit_df[["date", "vehicle", "driver", "status_raw", "month_name"]].copy()
            audit_display["date"] = audit_display["date"].dt.strftime("%Y-%m-%d")
            st.dataframe(audit_display, use_container_width=True, hide_index=True, height=400)

            # Download
            csv_bytes = audit_display.to_csv(index=False).encode("utf-8")
            st.download_button(
                f"Download {status_to_audit} audit CSV",
                data=csv_bytes,
                file_name=f"audit_{status_to_audit.lower()}_{selected_month.lower().replace(' ', '_')}.csv",
                mime="text/csv",
            )

# ---------- Raw Data ----------
with tab_raw:
    st.markdown("## Daily log")
    st.markdown(
        "One row per vehicle per day. Filter using the sidebar. "
        "Download as CSV for offline analysis."
    )
    display_df = daily[[
        "date", "vehicle", "driver", "status", "status_raw", "route", "is_yellow", "month_name"
    ]].copy()
    display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
    display_df = display_df.rename(columns={
        "status_raw": "original_text", "month_name": "month", "is_yellow": "highlighted",
    })
    st.dataframe(display_df, use_container_width=True, hide_index=True, height=500)

    csv_bytes = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV",
        data=csv_bytes,
        file_name=f"fleet_log_{selected_month.lower().replace(' ', '_')}.csv",
        mime="text/csv",
    )

    # Plant In/Out data
    if not plant.empty:
        st.markdown("## Plant In/Out log")
        st.markdown(
            "Parsed plant visits with IN/OUT timestamps and dwell time (hours at plant). "
            "Rows with notes instead of timestamps show up with a 'note' value instead."
        )
        plant_display = plant.copy()
        plant_display["date"] = plant_display["date"].dt.strftime("%Y-%m-%d")
        plant_display["in_time"] = plant_display["in_time"].apply(
            lambda t: t.strftime("%Y-%m-%d %H:%M") if pd.notna(t) else ""
        )
        plant_display["out_time"] = plant_display["out_time"].apply(
            lambda t: t.strftime("%Y-%m-%d %H:%M") if pd.notna(t) else ""
        )
        st.dataframe(plant_display, use_container_width=True, hide_index=True, height=400)

        plant_csv = plant_display.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download plant log CSV",
            data=plant_csv,
            file_name=f"plant_log_{selected_month.lower().replace(' ', '_')}.csv",
            mime="text/csv",
        )
