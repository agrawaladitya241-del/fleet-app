import streamlit as st
import pandas as pd
from datetime import date

# ONLY import stable things
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


# ================= SAFE LOCAL FUNCTION (NO IMPORT ISSUES) =================
def extract_fleet_status(files):

    final = {}

    for file in files:
        df = pd.read_excel(file)
        df.columns = df.columns.astype(str)

        for _, row in df.iterrows():

            vehicle = None

            for col in df.columns:
                if "vehicle" in col.lower():
                    vehicle = str(row[col]).strip().upper()
                    break

            if not vehicle or vehicle == "NAN":
                continue

            row_values = [str(x).upper() for x in row if pd.notna(x)]

            dh = sum(1 for x in row_values if "DH" in x)
            dp = sum(1 for x in row_values if "DP" in x)

            current_status = ""
            for val in reversed(row_values):
                if val.strip():
                    current_status = val
                    break

            if "DH" in current_status:
                status_type = "Driver Home"
            elif "DP" in current_status:
                status_type = "Delay"
            else:
                status_type = "Active"

            if vehicle not in final:
                final[vehicle] = {
                    "DH": 0,
                    "DP": 0,
                    "status": current_status,
                    "status_type": status_type
                }

            final[vehicle]["DH"] += dh
            final[vehicle]["DP"] += dp
            final[vehicle]["status"] = current_status
            final[vehicle]["status_type"] = status_type

    return pd.DataFrame.from_dict(final, orient="index").reset_index().rename(columns={"index": "vehicle"})


# ================= APP =================
st.set_page_config(page_title="Fleet Intelligence System", layout="wide")
st.title("🚛 Fleet Intelligence System")

tab1, tab2, tab3 = st.tabs(["Fleet", "Driver", "Monthly Analytics"])


# ================= FLEET TAB =================
with tab1:

    files = st.file_uploader("Upload Fleet Files", type=["xlsx"], accept_multiple_files=True)

    if files:

        summary = fleet_summary(files)

        # NEW STATUS
        status_df = extract_fleet_status(files)

        save_fleet_data(summary["vehicle_data"], str(date.today()))

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Vehicles", summary["total_vehicles"])
        col2.metric("Trips", summary["total_trips"])
        col3.metric("Idle", summary["total_idle"])
        col4.metric("Efficiency", summary["efficiency"])

        # ===== STATUS DASHBOARD =====
        st.subheader("🚛 Fleet Status Dashboard")

        c1, c2, c3 = st.columns(3)
        c1.metric("Active Trucks", len(status_df[status_df["status_type"] == "Active"]))
        c2.metric("Driver Home (DH)", len(status_df[status_df["status_type"] == "Driver Home"]))
        c3.metric("Delayed (DP)", len(status_df[status_df["status_type"] == "Delay"]))

        st.subheader("📊 Vehicle Status Table")
        st.dataframe(status_df)

        st.subheader("🔥 Top DH Vehicles")
        st.dataframe(status_df.sort_values(by="DH", ascending=False).head(10))

        st.subheader("🔥 Top DP Vehicles")
        st.dataframe(status_df.sort_values(by="DP", ascending=False).head(10))

        # ===== SEARCH =====
        st.subheader("🔍 Fleet Search")
        query = st.text_input("Ask anything")

        if query:
            st.success(smart_query(query, files))

        df_chart = pd.DataFrame(summary["vehicle_data"]).T
        st.bar_chart(df_chart)

    # ===== FILE COMPARE =====
    st.subheader("📊 Compare Two Files")

    f1 = st.file_uploader("Previous File", key="f1")
    f2 = st.file_uploader("Current File", key="f2")

    if f1 and f2:
        st.dataframe(pd.DataFrame(compare_files(f1, f2)).T)


# ================= DRIVER TAB =================
with tab2:

    file = st.file_uploader("Upload Driver File")

    if file:
        df = process_driver_file(file)

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


# ================= MONTHLY TAB =================
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
