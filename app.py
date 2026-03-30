import streamlit as st
import pandas as pd
from datetime import date
import openpyxl

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


# ================= FLEET PROCESSING =================
def process_file(uploaded_file):
    wb = openpyxl.load_workbook(uploaded_file)
    ws = wb.active

    vehicle_col = None
    trips_col = None

    for row in ws.iter_rows(min_row=1, max_row=10):
        for i, cell in enumerate(row):
            if cell.value:
                text = str(cell.value).upper()
                if "VEHICLE" in text:
                    vehicle_col = i
                if "TRIP" in text:
                    trips_col = i

    data = {}

    if vehicle_col is None or trips_col is None:
        return data

    for row in ws.iter_rows(min_row=2):

        vehicle_raw = row[vehicle_col].value
        if not vehicle_raw:
            continue

        vehicle = str(vehicle_raw).replace(" ", "").upper()

        try:
            trips = int(row[trips_col].value)
        except:
            trips = 0

        idle = 0
        for i, cell in enumerate(row):
            if i in [vehicle_col, trips_col]:
                continue

            val = str(cell.value).upper() if cell.value else ""
            if "WAIT" in val or "PARK" in val:
                idle += 1

        if vehicle not in data:
            data[vehicle] = {"trips": 0, "idle": 0}

        data[vehicle]["trips"] += trips
        data[vehicle]["idle"] += idle

    return data


def merge_files(files):
    final = {}
    for f in files:
        data = process_file(f)
        for v, d in data.items():
            if v not in final:
                final[v] = {"trips": 0, "idle": 0}
            final[v]["trips"] += d["trips"]
            final[v]["idle"] += d["idle"]
    return final


def fleet_summary(files):
    data = merge_files(files)

    total_vehicles = len(data)
    total_trips = sum(v["trips"] for v in data.values())
    total_idle = sum(v["idle"] for v in data.values())

    efficiency = round(total_trips / (total_trips + total_idle), 3) if (total_trips + total_idle) else 0

    return {
        "total_vehicles": total_vehicles,
        "total_trips": total_trips,
        "total_idle": total_idle,
        "efficiency": efficiency,
        "vehicle_data": data
    }


# ================= DH / DP STATUS =================
def extract_fleet_status(files):

    final = {}

    for file in files:
        df = pd.read_excel(file)

        for _, row in df.iterrows():

            vehicle = None
            for col in df.columns:
                if "vehicle" in str(col).lower():
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
                final[vehicle] = {"DH": 0, "DP": 0, "status": "", "status_type": ""}

            final[vehicle]["DH"] += dh
            final[vehicle]["DP"] += dp
            final[vehicle]["status"] = current_status
            final[vehicle]["status_type"] = status_type

    return pd.DataFrame(final).T.reset_index().rename(columns={"index": "vehicle"})


# ================= COMPARE FUNCTION =================
def compare_files(file1, file2):

    data1 = process_file(file1)
    data2 = process_file(file2)

    result = {}

    vehicles = set(data1.keys()).union(set(data2.keys()))

    for v in vehicles:
        d1 = data1.get(v, {"trips": 0, "idle": 0})
        d2 = data2.get(v, {"trips": 0, "idle": 0})

        result[v] = {
            "trip_change": d2["trips"] - d1["trips"],
            "idle_change": d2["idle"] - d1["idle"]
        }

    return result


# ================= APP =================
st.set_page_config(page_title="Fleet Intelligence System", layout="wide")
st.title("🚛 Fleet Intelligence System")

tab1, tab2, tab3 = st.tabs(["Fleet", "Driver", "Monthly"])


# ================= FLEET TAB =================
with tab1:

    files = st.file_uploader("Upload Fleet Files", type=["xlsx"], accept_multiple_files=True)

    if files:

        summary = fleet_summary(files)
        status_df = extract_fleet_status(files)

        save_fleet_data(summary["vehicle_data"], str(date.today()))

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Vehicles", summary["total_vehicles"])
        col2.metric("Trips", summary["total_trips"])
        col3.metric("Idle", summary["total_idle"])
        col4.metric("Efficiency", summary["efficiency"])

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

    # ===== COMPARE FILES =====
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

        st.subheader("Driver Summary")
        st.dataframe(driver_summary(df))

        st.subheader("Driver Home Days")
        st.dataframe(driver_home_days(df))


# ================= MONTHLY TAB =================
with tab3:

    monthly = get_monthly_fleet()

    if not monthly.empty:
        st.dataframe(monthly)
    else:
        st.info("No data yet")
