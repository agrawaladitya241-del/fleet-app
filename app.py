"""
app.py
------
Fleet Intelligence Dashboard for TSK/TSM flatbed trailer fleet.

Reads a multi-sheet Excel workbook (one sheet per month) and renders a
clean, month-aware dashboard with KPIs, drill-down tables, and a daily
status trend.

Deployment: Streamlit Community Cloud (free tier). No login required.
"""

from __future__ import annotations

import io
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

import data_loader
import analytics

# ------------------------------------------------------------------
# Page config + global styling
# ------------------------------------------------------------------

st.set_page_config(
    page_title="Fleet Intelligence · TSK",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# A restrained, utilitarian dark theme. No decorative gradients — this is an
# ops dashboard, not a marketing page. Typography: IBM Plex Sans (industrial,
# designed for data) paired with JetBrains Mono for numbers.
CUSTOM_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@500;700&display=swap');

  html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', -apple-system, sans-serif !important;
  }

  /* Page background: flat near-black, no gradients */
  .stApp {
    background: #0b0d10;
  }

  /* Main container padding */
  .block-container {
    padding-top: 2rem;
    padding-bottom: 4rem;
    max-width: 1400px;
  }

  /* Headings */
  h1, h2, h3, h4 {
    font-family: 'IBM Plex Sans', sans-serif !important;
    letter-spacing: -0.01em;
    color: #f5f5f5;
  }
  h1 {
    font-weight: 700;
    font-size: 2rem !important;
    border-bottom: 1px solid #1f2328;
    padding-bottom: 0.75rem;
    margin-bottom: 0.5rem !important;
  }
  h2 {
    font-weight: 600;
    font-size: 1.25rem !important;
    margin-top: 2rem !important;
    color: #e5e7eb;
  }
  h3 {
    font-weight: 500;
    font-size: 1rem !important;
    color: #d1d5db;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  /* Subtle page subtitle under h1 */
  .page-subtitle {
    color: #8b93a1;
    font-size: 0.95rem;
    margin-bottom: 2rem;
    font-weight: 400;
  }

  /* KPI cards — flat, bordered, monospaced numbers */
  .kpi-card {
    background: #11141a;
    border: 1px solid #1f2328;
    border-radius: 8px;
    padding: 1.25rem 1.5rem;
    height: 100%;
  }
  .kpi-label {
    color: #8b93a1;
    font-size: 0.75rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.5rem;
  }
  .kpi-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 2.25rem;
    font-weight: 700;
    color: #f5f5f5;
    line-height: 1;
  }
  .kpi-unit {
    color: #8b93a1;
    font-size: 1rem;
    font-weight: 400;
    margin-left: 0.25rem;
  }
  .kpi-card.accent-green .kpi-value { color: #22c55e; }
  .kpi-card.accent-red   .kpi-value { color: #ef4444; }
  .kpi-card.accent-amber .kpi-value { color: #f59e0b; }
  .kpi-card.accent-blue  .kpi-value { color: #60a5fa; }

  /* Sidebar styling */
  section[data-testid="stSidebar"] {
    background: #0f1216;
    border-right: 1px solid #1f2328;
  }
  section[data-testid="stSidebar"] h1,
  section[data-testid="stSidebar"] h2,
  section[data-testid="stSidebar"] h3 {
    color: #e5e7eb;
  }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid #1f2328;
  }
  .stTabs [data-baseweb="tab"] {
    background: transparent;
    color: #8b93a1;
    font-weight: 500;
    padding: 0.75rem 1.25rem;
    border: none;
    border-bottom: 2px solid transparent;
  }
  .stTabs [aria-selected="true"] {
    color: #f5f5f5 !important;
    border-bottom: 2px solid #f59e0b !important;
    background: transparent !important;
  }

  /* Dataframes */
  .stDataFrame {
    border: 1px solid #1f2328;
    border-radius: 6px;
  }

  /* File uploader — make it less shouty */
  [data-testid="stFileUploader"] section {
    background: #11141a;
    border: 1px dashed #2a3039;
    border-radius: 6px;
  }

  /* Status chip */
  .status-chip {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
    font-family: 'JetBrains Mono', monospace;
  }

  /* Hide Streamlit's default chrome we don't need */
  #MainMenu, footer, header[data-testid="stHeader"] {
    visibility: hidden;
  }

  /* Info/warning boxes */
  .stAlert {
    background: #11141a;
    border: 1px solid #1f2328;
    border-radius: 6px;
  }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def kpi_card(label: str, value, unit: str = "", accent: str = "") -> str:
    """Render an HTML KPI card."""
    accent_class = f"accent-{accent}" if accent else ""
    unit_html = f'<span class="kpi-unit">{unit}</span>' if unit else ""
    return f"""
    <div class="kpi-card {accent_class}">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}{unit_html}</div>
    </div>
    """


@st.cache_data(show_spinner=False)
def load_data(file_bytes: bytes, year: int) -> pd.DataFrame:
    """Cached load. file_bytes makes this cache on file content, not path."""
    buf = io.BytesIO(file_bytes)
    df = data_loader.load_all_months(buf, year=year)
    return analytics.add_status_column(df)


# ------------------------------------------------------------------
# Header
# ------------------------------------------------------------------

st.markdown("# Fleet Intelligence")
st.markdown(
    '<div class="page-subtitle">'
    "Daily operations dashboard for TSK/TSM flatbed fleet · Angul depot"
    "</div>",
    unsafe_allow_html=True,
)


# ------------------------------------------------------------------
# Sidebar: file upload + filters
# ------------------------------------------------------------------

with st.sidebar:
    st.markdown("### Data")
    uploaded = st.file_uploader(
        "Upload fleet report (.xlsx)",
        type=["xlsx"],
        help="Multi-sheet workbook with one sheet per month (e.g. February, March, APRIL).",
    )

    # Year used for date parsing — only matters for text-date sheets like 'APRIL'
    year = st.number_input(
        "Reporting year",
        min_value=2020,
        max_value=2100,
        value=datetime.now().year,
        help="Used to assign a year to date columns. Doesn't affect data values.",
    )


# ------------------------------------------------------------------
# Main body
# ------------------------------------------------------------------

if not uploaded:
    st.info(
        "Upload a fleet report Excel file to begin. "
        "The file should have one sheet per month (e.g., `February`, `March`, `APRIL`) "
        "with columns for Vehicle No, Driver Name, and one column per day of the month."
    )
    st.stop()

# Read file bytes once (for caching)
file_bytes = uploaded.getvalue()

try:
    df_all = load_data(file_bytes, year=int(year))
except Exception as e:
    st.error(f"Couldn't read that file: {e}")
    st.stop()

if df_all.empty:
    st.warning(
        "No month sheets were found in this workbook. "
        "Expected sheet names like `February`, `March`, `APRIL`."
    )
    st.stop()


# ------------------------------------------------------------------
# Month selector (in sidebar, after data loads)
# ------------------------------------------------------------------

available_months = (
    df_all[["month_name", "date"]]
    .assign(_month_num=lambda d: d["date"].dt.month)
    .drop_duplicates(subset=["month_name"])
    .sort_values("_month_num", ascending=False)["month_name"]
    .tolist()
)

with st.sidebar:
    st.markdown("### View")
    month_options = ["All months"] + available_months
    # Default: latest month (first real month in the sorted list)
    default_index = 1 if len(month_options) > 1 else 0
    selected_month = st.selectbox("Month", month_options, index=default_index)

    st.markdown("### Filter")
    all_drivers = sorted(
        [d for d in df_all["driver"].unique() if d and str(d).strip()]
    )
    driver_filter = st.multiselect("Driver", all_drivers, default=[])

    all_vehicles = sorted(df_all["vehicle"].unique())
    vehicle_filter = st.multiselect("Vehicle", all_vehicles, default=[])


# Apply filters
df = df_all.copy()
if selected_month != "All months":
    df = df[df["month_name"] == selected_month]
if driver_filter:
    df = df[df["driver"].isin(driver_filter)]
if vehicle_filter:
    df = df[df["vehicle"].isin(vehicle_filter)]

if df.empty:
    st.warning("No data matches the selected filters.")
    st.stop()


# ------------------------------------------------------------------
# KPI row
# ------------------------------------------------------------------

kpis = analytics.compute_kpis(df)

latest = kpis["latest_date"]
latest_str = latest.strftime("%d %b %Y") if latest is not None else "—"

st.markdown(
    f"<div style='color:#8b93a1; font-size:0.85rem; margin-bottom:1rem;'>"
    f"Snapshot: <strong style='color:#d1d5db;'>{selected_month}</strong> · "
    f"Latest day logged: <strong style='color:#d1d5db;'>{latest_str}</strong>"
    f"</div>",
    unsafe_allow_html=True,
)

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(
        kpi_card("Active trips today", kpis["active_trips"], accent="green"),
        unsafe_allow_html=True,
    )
with k2:
    st.markdown(
        kpi_card("Drivers home", kpis["drivers_home"], accent="red"),
        unsafe_allow_html=True,
    )
with k3:
    st.markdown(
        kpi_card("Waiting / idle", kpis["idle_waiting"], accent="amber"),
        unsafe_allow_html=True,
    )
with k4:
    st.markdown(
        kpi_card("Fleet utilization", kpis["fleet_util_pct"], unit="%", accent="blue"),
        unsafe_allow_html=True,
    )


# ------------------------------------------------------------------
# Tabs
# ------------------------------------------------------------------

tab_overview, tab_vehicles, tab_drivers, tab_raw = st.tabs(
    ["Overview", "Vehicles", "Drivers", "Raw data"]
)

# ---- Overview tab ----
with tab_overview:
    st.markdown("## Daily status trend")

    daily = analytics.daily_summary(df)
    if daily.empty:
        st.info("Not enough data to chart.")
    else:
        # Stacked bar chart of status counts per day
        status_cols = [c for c in analytics.STATUS_ORDER if c != "NO_DATA"]
        melted = daily.melt(
            id_vars=["date"],
            value_vars=status_cols,
            var_name="status",
            value_name="count",
        )
        melted["status_label"] = melted["status"].map(analytics.STATUS_LABELS)

        fig = px.bar(
            melted,
            x="date",
            y="count",
            color="status",
            color_discrete_map=analytics.STATUS_COLORS,
            category_orders={"status": status_cols},
            labels={"date": "", "count": "Vehicles", "status": "Status"},
        )
        fig.update_layout(
            plot_bgcolor="#0b0d10",
            paper_bgcolor="#0b0d10",
            font=dict(family="IBM Plex Sans", color="#d1d5db"),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor="rgba(0,0,0,0)",
            ),
            margin=dict(l=20, r=20, t=40, b=20),
            height=420,
            xaxis=dict(gridcolor="#1f2328", showgrid=False),
            yaxis=dict(gridcolor="#1f2328"),
            bargap=0.15,
        )
        # Update legend labels
        for trace in fig.data:
            trace.name = analytics.STATUS_LABELS.get(trace.name, trace.name)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("## Utilization trend")
        fig2 = px.line(
            daily,
            x="date",
            y="utilization_pct",
            markers=True,
            labels={"date": "", "utilization_pct": "Utilization %"},
        )
        fig2.update_traces(line_color="#60a5fa", marker=dict(size=6))
        fig2.update_layout(
            plot_bgcolor="#0b0d10",
            paper_bgcolor="#0b0d10",
            font=dict(family="IBM Plex Sans", color="#d1d5db"),
            margin=dict(l=20, r=20, t=20, b=20),
            height=280,
            xaxis=dict(gridcolor="#1f2328", showgrid=False),
            yaxis=dict(gridcolor="#1f2328", range=[0, 105]),
        )
        st.plotly_chart(fig2, use_container_width=True)


# ---- Vehicles tab ----
with tab_vehicles:
    st.markdown("## Vehicle performance")

    vs = analytics.vehicle_summary(df)
    if vs.empty:
        st.info("No vehicle data for this selection.")
    else:
        st.markdown("### Top performers")
        top = vs.head(10)
        st.dataframe(
            top,
            use_container_width=True,
            hide_index=True,
            column_config={
                "utilization_pct": st.column_config.ProgressColumn(
                    "Utilization %",
                    min_value=0,
                    max_value=100,
                    format="%.1f%%",
                ),
            },
        )

        st.markdown("### Flagged vehicles")
        st.markdown(
            "<div style='color:#8b93a1; font-size:0.85rem; margin-bottom:0.5rem;'>"
            "Vehicles with high idle / driver issues deserve follow-up."
            "</div>",
            unsafe_allow_html=True,
        )
        # A vehicle is flagged if:
        #   - utilization < 40%, OR
        #   - DH days >= 3, OR
        #   - DP days >= 2
        flagged = vs[
            (vs["utilization_pct"] < 40)
            | (vs["DH"] >= 3)
            | (vs["DP"] >= 2)
        ].sort_values("utilization_pct")
        if flagged.empty:
            st.success("No vehicles flagged in the current view.")
        else:
            st.dataframe(
                flagged,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "utilization_pct": st.column_config.ProgressColumn(
                        "Utilization %",
                        min_value=0,
                        max_value=100,
                        format="%.1f%%",
                    ),
                },
            )

        st.markdown("### All vehicles")
        st.dataframe(
            vs,
            use_container_width=True,
            hide_index=True,
            column_config={
                "utilization_pct": st.column_config.ProgressColumn(
                    "Utilization %",
                    min_value=0,
                    max_value=100,
                    format="%.1f%%",
                ),
            },
        )


# ---- Drivers tab ----
with tab_drivers:
    st.markdown("## Driver performance")
    ds = analytics.driver_summary(df)
    if ds.empty:
        st.info("No driver data for this selection.")
    else:
        st.dataframe(
            ds,
            use_container_width=True,
            hide_index=True,
            column_config={
                "utilization_pct": st.column_config.ProgressColumn(
                    "Utilization %",
                    min_value=0,
                    max_value=100,
                    format="%.1f%%",
                ),
            },
        )


# ---- Raw data tab ----
with tab_raw:
    st.markdown("## Daily log")
    st.markdown(
        "<div style='color:#8b93a1; font-size:0.85rem; margin-bottom:0.75rem;'>"
        "One row per vehicle per day. Filter in the sidebar to narrow down."
        "</div>",
        unsafe_allow_html=True,
    )

    display_df = df.copy()
    display_df["date"] = display_df["date"].dt.strftime("%Y-%m-%d")
    display_df = display_df[
        ["date", "vehicle", "driver", "status", "status_raw", "month_name"]
    ].rename(columns={
        "status_raw": "original_text",
        "month_name": "month",
    })

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=500,
    )

    # Download button
    csv_bytes = display_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download CSV",
        data=csv_bytes,
        file_name=f"fleet_log_{selected_month.lower().replace(' ', '_')}.csv",
        mime="text/csv",
    )
