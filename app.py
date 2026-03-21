import streamlit as st
import pandas as pd

st.set_page_config(page_title="Fleet & Driver Dashboard", layout="wide")

st.title("🚛 Fleet & Driver Dashboard")

# SAFE IMPORTS
try:
    from ai_helper import smart_query, fleet_summary
    from driver_helper import process_driver_file, driver_summary, driver_query
except Exception as e:
    st.error(f"Import error: {e}")
    st.stop()

tab1, tab2 = st.tabs(["Fleet", "Driver"])

# ================= FLEET =================
with tab1:

    files = st.file_uploader(
        "Upload Fleet Files",
        type=["xlsx"],
        accept_multiple_files=True,
        key="fleet"
    )

    if files:
        try:
            summary = fleet_summary(files)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Vehicles", summary["total_vehicles"])
            col2.metric("Trips", summary["total_trips"])
            col3.metric("Idle", summary["total_idle"])
            col4.metric("Efficiency", summary["efficiency"])

            st.markdown("---")

            query = st.text_input("Ask Fleet", key="fleet_q")

            if query:
                st.success(smart_query(query, files))

            if summary["vehicle_data"]:
                df = pd.DataFrame(summary["vehicle_data"]).T
                st.bar_chart(df)
            else:
                st.warning("No vehicle data found")

        except Exception as e:
            st.error(f"Fleet Error: {e}")

    else:
        st.info("Upload fleet files")


# ================= DRIVER =================
# ================= DRIVER =================
with tab2:

    file = st.file_uploader(
        "Upload Driver File",
        type=["xlsx"],
        key="driver"
    )

    if file:
        try:
            df = process_driver_file(file)

            if df.empty:
                st.warning("Driver columns not detected properly")
            else:

                # ================= KPI =================
                total_drivers = df["driver"].nunique()
                total_days = int(df["days"].sum())
                avg_days = round(total_days / total_drivers, 2) if total_drivers else 0
                total_assignments = len(df)

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Drivers", total_drivers)
                col2.metric("Total Days", total_days)
                col3.metric("Avg Days", avg_days)
                col4.metric("Assignments", total_assignments)

                st.markdown("---")

                # ================= SUMMARY =================
                summary = driver_summary(df)

                # BEST DRIVERS
                st.subheader("🥇 Best Drivers")
                st.dataframe(summary.head(5))

                # WORST DRIVERS
                st.subheader("🐢 Worst Drivers")
                st.dataframe(summary.tail(5))

                st.markdown("---")

                # ================= DRIVER CHANGES =================
                changes = vehicle_driver_changes(df)

                st.subheader("🔄 Vehicles with Most Driver Changes")
                st.dataframe(changes.head(10))

                st.markdown("---")

                # ================= HOME DAYS =================
                home = driver_home_days(df)

                st.subheader("🏠 Drivers with Highest Home Days")
                st.dataframe(home.head(10))

                st.markdown("---")

                # ================= FULL TABLE =================
                st.subheader("📋 Full Driver Data")
                st.dataframe(summary)

        except Exception as e:
            st.error(f"Driver Error: {e}")

    else:
        st.info("Upload driver file")
