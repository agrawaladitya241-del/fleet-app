import streamlit as st
from driver_helper import (
    process_driver_file,
    driver_summary,
    vehicle_summary,
    driver_changes
)

st.set_page_config(page_title="Fleet Dashboard", layout="wide")

st.title("🚛 Fleet & Driver Dashboard")

# -------------------------------
# FILE UPLOAD
# -------------------------------
uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file is not None:

    df = process_driver_file(uploaded_file)

    # -------------------------------
    # CALCULATIONS
    # -------------------------------
    driver_stats = driver_summary(df)
    vehicle_run = vehicle_summary(df)
    changes = driver_changes(df)

    least_change_truck = changes.sort_values(by="driver_changes").iloc[0]

    # -------------------------------
    # TABS
    # -------------------------------
    tab1, tab2, tab3 = st.tabs(["📊 Drivers", "🚛 Vehicles", "🔄 Stability"])

    # -------------------------------
    # DRIVER TAB
    # -------------------------------
    with tab1:
        st.subheader("Driver Performance")

        THRESHOLD = 300

        def highlight(row):
            if row["total_working_days"] > THRESHOLD:
                return ["background-color: #ff4d4d"] * len(row)
            return [""] * len(row)

        st.dataframe(
            driver_stats.style.apply(highlight, axis=1),
            use_container_width=True
        )

    # -------------------------------
    # VEHICLE TAB
    # -------------------------------
    with tab2:
        st.subheader("Vehicle Running Months")

        st.dataframe(
            vehicle_run.sort_values(by="running_months", ascending=False),
            use_container_width=True
        )

    # -------------------------------
    # STABILITY TAB
    # -------------------------------
    with tab3:
        st.subheader("Driver Changes")

        st.dataframe(
            changes.sort_values(by="driver_changes"),
            use_container_width=True
        )

        st.success(
            f"🏆 Most Stable Truck: {least_change_truck['Vehicle No']} "
            f"({least_change_truck['driver_changes']} changes)"
        )

        st.subheader("⚠️ High Change Trucks")
        st.dataframe(
            changes[changes["driver_changes"] > 5],
            use_container_width=True
        )

    # -------------------------------
    # RAW DATA
    # -------------------------------
    with st.expander("🔍 Raw Data"):
        st.dataframe(df)

else:
    st.info("Upload your Excel file to begin.")
