import streamlit as st
import pandas as pd

from ai_helper import smart_query, fleet_summary
from driver_helper import (
    process_driver_file,
    driver_summary,
    vehicle_driver_changes,
    driver_home_days,
    driver_vehicle_switch
)

st.set_page_config(page_title="Fleet & Driver Dashboard", layout="wide")

st.title("🚛 Fleet & Driver Dashboard")

tab1, tab2 = st.tabs(["Fleet", "Driver"])


# ================= FLEET =================
with tab1:

    files = st.file_uploader("Upload Fleet Files", type=["xlsx"], accept_multiple_files=True)

    if files:
        try:
            summary = fleet_summary(files)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Vehicles", summary["total_vehicles"])
            col2.metric("Trips", summary["total_trips"])
            col3.metric("Idle", summary["total_idle"])
            col4.metric("Efficiency", summary["efficiency"])

            st.markdown("---")

            query = st.text_input("Ask Fleet")

            if query:
                st.success(smart_query(query, files))

            if summary["vehicle_data"]:
                df = pd.DataFrame(summary["vehicle_data"]).T
                st.bar_chart(df)

        except Exception as e:
            st.error(f"Fleet Error: {e}")

    else:
        st.info("Upload fleet files")


# ================= DRIVER =================
with tab2:

    file = st.file_uploader("Upload Driver File", type=["xlsx"])

    if file:
        try:
            df = process_driver_file(file)

            if df.empty:
                st.error("❌ Could not detect required columns")
            else:

                summary = driver_summary(df)

                # KPIs
                total_drivers = summary["driver"].nunique()
                total_days = int(summary["total_days"].sum())
                avg_days = round(total_days / total_drivers, 2) if total_drivers else 0

                col1, col2, col3 = st.columns(3)
                col1.metric("Drivers", total_drivers)
                col2.metric("Total Working Days", total_days)
                col3.metric("Avg Days", avg_days)

                st.markdown("---")

                st.subheader("🥇 Best Drivers")
                st.dataframe(summary.head(5))

                st.subheader("🐢 Worst Drivers")
                st.dataframe(summary.tail(5))

                st.markdown("---")

                st.subheader("🔄 Driver Changes per Vehicle")
                st.dataframe(vehicle_driver_changes(df).head(10))

                st.markdown("---")

                st.subheader("🏠 Driver Home Days")
                st.dataframe(driver_home_days(df).head(10))

                st.markdown("---")

                st.subheader("🚛 Drivers Who Switched Most Vehicles")
                st.dataframe(driver_vehicle_switch(df).head(10))

                st.markdown("---")

                st.subheader("📋 Full Driver Table")
                st.dataframe(summary)

        except Exception as e:
            st.error(f"Driver Error: {e}")

    else:
        st.info("Upload driver file")
