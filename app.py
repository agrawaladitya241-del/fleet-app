import streamlit as st
import pandas as pd
from ai_helper import smart_query, fleet_summary

st.set_page_config(page_title="Fleet AI", layout="wide")

st.title("🚚 Fleet Intelligence Dashboard")

uploaded_files = st.file_uploader(
    "Upload Excel files",
    type=["xlsx"],
    accept_multiple_files=True
)

if uploaded_files:

    summary = fleet_summary(uploaded_files)
    data = summary["vehicle_data"]

    # KPI
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Vehicles", summary["total_vehicles"])
    col2.metric("Trips", summary["total_trips"])
    col3.metric("Idle", summary["total_idle"])
    col4.metric("Efficiency", summary["efficiency"])

    st.markdown("---")

    # Issue KPIs
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("DH", summary["total_dh"])
    col2.metric("DP", summary["total_dp"])
    col3.metric("AC", summary["total_ac"])
    col4.metric("RM", summary["total_rm"])

    st.markdown("---")

    # Query
    st.subheader("💬 Ask Anything")

    query = st.text_input("Ask anything about your fleet data")

    if query:
        st.success(smart_query(query, uploaded_files))

    st.markdown("---")

    # Table
    df = pd.DataFrame([
        {"Vehicle": v, **d}
        for v, d in data.items()
    ])

    st.dataframe(df)

    # Graph
    st.subheader("📊 Performance")

    chart_df = df.set_index("Vehicle")
    st.bar_chart(chart_df[["trips", "idle", "dp", "dh"]])

else:
    st.info("Upload files to begin")
