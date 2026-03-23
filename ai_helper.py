import streamlit as st
import pandas as pd

from ai_helper import smart_query, fleet_summary, compare_files
from driver_helper import (
    process_driver_file,
    driver_summary,
    driver_home_days,
    vehicle_driver_changes,
    driver_vehicle_switch
)

st.set_page_config(page_title="Fleet & Driver Dashboard", layout="wide")

st.title("🚛 Fleet & Driver Dashboard")

tab1, tab2 = st.tabs(["Fleet", "Driver"])


# ================= FLEET =================
with tab1:

    files = st.file_uploader("Upload Fleet Files", type=["xlsx"], accept_multiple_files=True)

    if files:
        summary = fleet_summary(files)

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Vehicles", summary["total_vehicles"])
        col2.metric("Trips", summary["total_trips"])
        col3.metric("Idle", summary["total_idle"])
        col4.metric("Efficiency", summary["efficiency"])

        st.markdown("---")

        if summary["vehicle_data"]:
            df = pd.DataFrame(summary["vehicle_data"]).T
            st.bar_chart(df)

    # 🔥 COMPARISON
    st.markdown("---")
    st.subheader("📊 Compare Two Days")

    f1 = st.file_uploader("Previous File", type=["xlsx"], key="f1")
    f2 = st.file_uploader("Current File", type=["xlsx"], key="f2")

    if f1 and f2:
        comp = compare_files(f1, f2)
        df = pd.DataFrame(comp).T
        st.dataframe(df)


# ================= DRIVER =================
with tab2:

    file = st.file_uploader("Upload Driver File", type=["xlsx"])

    if file:
        df = process_driver_file(file)

        summary = driver_summary(df)

        st.subheader("Driver Summary")
        st.dataframe(summary)

        st.subheader("Home Days")
        st.dataframe(driver_home_days(df))

        st.subheader("Vehicle Driver Changes")
        st.dataframe(vehicle_driver_changes(df))

        st.subheader("Driver Vehicle Switching")
        st.dataframe(driver_vehicle_switch(df))
