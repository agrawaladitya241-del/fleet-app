import streamlit as st
import pandas as pd
from datetime import date

from ai_helper import smart_query, fleet_summary, compare_files
from driver_helper import (
    process_driver_file,
    driver_summary,
    driver_home_days,
    vehicle_driver_changes,
    driver_vehicle_switch,
    vehicle_home_days,
    driver_query
)
from database import save_fleet_data, save_driver_data, get_monthly_fleet

st.set_page_config(page_title="Fleet Intelligence System", layout="wide")

st.title("🚛 Fleet Intelligence System")

tab1, tab2, tab3 = st.tabs(["Fleet", "Driver", "Monthly Analytics"])


# ================= FLEET =================
with tab1:

    files = st.file_uploader("Upload Fleet Files", type=["xlsx"], accept_multiple_files=True)

    if files:

        summary = fleet_summary(files)

        # SAVE TO DATABASE
        save_fleet_data(summary["vehicle_data"], str(date.today()))

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Vehicles", summary["total_vehicles"])
        col2.metric("Trips", summary["total_trips"])
        col3.metric("Idle", summary["total_idle"])
        col4.metric("Efficiency", summary["efficiency"])

        st.subheader("🔍 Fleet Search")
        query = st.text_input("Ask anything")

        if query:
            st.success(smart_query(query, files))

        df = pd.DataFrame(summary["vehicle_data"]).T
        st.bar_chart(df)

    st.subheader("📊 Compare Two Files")

    f1 = st.file_uploader("Previous File", key="f1")
    f2 = st.file_uploader("Current File", key="f2")

    if f1 and f2:
        st.dataframe(pd.DataFrame(compare_files(f1, f2)).T)


# ================= DRIVER =================
with tab2:

    file = st.file_uploader("Upload Driver File")

    if file:
        df = process_driver_file(file)

        # SAVE DRIVER DATA
        save_driver_data(df)

        st.subheader("🔍 Driver Search")
        q = st.text_input("Ask about drivers")

        if q:
            st.success(driver_query(q, df))

        st.subheader("Driver Summary")
        st.dataframe(driver_summary(df))

        st.subheader("Driver Home Days")
        st.dataframe(driver_home_days(df))

        st.subheader("Vehicle Driver Changes")
        st.dataframe(vehicle_driver_changes(df))

        st.subheader("Driver Vehicle Switching")
        st.dataframe(driver_vehicle_switch(df))

        st.subheader("Vehicle-wise Home Days")
        st.dataframe(vehicle_home_days(df))


# ================= MONTHLY ANALYTICS =================
with tab3:

    st.subheader("📅 Monthly Fleet Performance")

    monthly = get_monthly_fleet()

    if not monthly.empty:

        st.dataframe(monthly)

        st.subheader("Top Performing Vehicles")
        st.dataframe(monthly.head(5))

        st.subheader("Worst Performing Vehicles")
        st.dataframe(monthly.tail(5))

    else:
        st.info("No data stored yet. Upload files first.")
