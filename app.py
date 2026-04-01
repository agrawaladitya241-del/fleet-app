import streamlit as st
import pandas as pd
from datetime import date
import openpyxl
import re

from driver_helper import (
    process_driver_file,
    driver_summary,
    driver_home_days
)
from database import save_fleet_data, save_driver_data


# ================= GET LATEST FILE =================
def get_latest_file(files):
    dated_files = []
    for f in files:
        match = re.search(r'(\d{2})\.(\d{2})', f.name)
        if match:
            day, month = match.groups()
            date_key = int(month) * 100 + int(day)
            dated_files.append((date_key, f))
    if not dated_files:
        return files[-1]
    return sorted(dated_files, reverse=True)[0][1]


# ================= ORIGINAL FLEET PROCESS =================
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

    for row in ws.iter_rows(min_row=2):

        vehicle_raw = row[vehicle_col].value
        if not vehicle_raw:
            continue

        vehicle = str(vehicle_raw).replace(" ", "").upper()

        try:
            trips = float(row[trips_col].value)
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


# ================= FLEET SUMMARY =================
def fleet_summary(file):
    data = process_file(file)

    total_vehicles = len(data)
    total_trips = sum(v["trips"] for v in data.values())
    total_idle = sum(v["idle"] for v in data.values())

    efficiency = round(total_trips / (total_trips + total_idle), 3) if (total_trips + total_idle) else 0

    return data, total_vehicles, int(total_trips), total_idle, efficiency


# ================= STATUS =================
def extract_fleet_status(file):

    df = pd.read_excel(file)
    final = {}

    for _, row in df.iterrows():

        vehicle = None
        for col in df.columns:
            if "vehicle" in str(col).lower():
                vehicle = str(row[col]).strip().upper()
                break

        if not vehicle:
            continue

        values = [str(x).upper() for x in row if pd.notna(x)]

        dp = sum(1 for x in values if "DP" in x)
        dh = sum(1 for x in values if "DH" in x)

        current_status = values[-1]

        if "DP" in current_status:
            status = "Delay"
        elif "DH" in current_status:
            status = "Driver Home"
        else:
            status = "Active"

        final[vehicle] = {"DP": dp, "DH": dh, "status_type": status}

    return pd.DataFrame(final).T.reset_index().rename(columns={"index": "vehicle"})


# ================= MONTHLY =================
def monthly_analysis(file):

    df = pd.read_excel(file)

    vehicle_col = None
    for col in df.columns:
        if "vehicle" in str(col).lower():
            vehicle_col = col
            break

    results = []

    for _, row in df.iterrows():

        vehicle = str(row[vehicle_col]).strip().upper()
        if not vehicle:
            continue

        dp = dh = trips = days = 0

        for val in row:
            if pd.isna(val):
                continue

            val_str = str(val).upper()
            days += 1

            if "DP" in val_str:
                dp += 1
            elif "DH" in val_str:
                dh += 1

            try:
                trips += float(val)
            except:
                pass

        results.append({
            "vehicle": vehicle,
            "DP": dp,
            "DH": dh,
            "Trips": trips,
            "Days": days
        })

    return pd.DataFrame(results)


# ================= MANAGER FUNCTIONS =================
def get_consistent(df):
    return df[
        (df["Trips"] > df["Trips"].mean()) &
        (df["DP"] < df["DP"].mean()) &
        (df["DH"] < df["DH"].mean())
    ]


def get_problem(df):
    return df[
        (df["DP"] > df["DP"].mean()) |
        (df["DH"] > df["DH"].mean())
    ]


def get_critical(df):
    return df[
        (df["DP"] > df["DP"].mean() * 1.5) |
        (df["DH"] > df["DH"].mean() * 1.5)
    ]


def add_score(df):
    df = df.copy()
    df["Score"] = df["Trips"] - (df["DP"] * 5) - (df["DH"] * 3)
    return df.sort_values(by="Score", ascending=False)


def recommendations(df):
    recs = []
    if len(df[df["DP"] > df["DP"].mean()]) > 0:
        recs.append("⚠️ High delay vehicles detected")
    if len(df[df["DH"] > df["DH"].mean()]) > 0:
        recs.append("⚠️ Driver availability issues detected")
    return recs


# ================= SMART QUERY =================
def smart_query(q, df):
    q = q.lower()

    if "dp" in q:
        return df.sort_values(by="DP", ascending=False).head(10)
    if "dh" in q:
        return df.sort_values(by="DH", ascending=False).head(10)
    if "trip" in q:
        return df.sort_values(by="Trips", ascending=False).head(10)
    if "score" in q:
        return add_score(df).head(10)

    return "Query not understood"


# ================= APP =================
st.set_page_config(layout="wide")
st.title("🚛 Fleet Intelligence System")

tab1, tab2 = st.tabs(["Fleet", "Driver"])


with tab1:

    files = st.file_uploader("Upload Fleet Files", type=["xlsx"], accept_multiple_files=True)

    if files:

        latest_file = get_latest_file(files)

        data, total_v, trips, idle, eff = fleet_summary(latest_file)
        status_df = extract_fleet_status(latest_file)
        monthly_df = monthly_analysis(latest_file)

        save_fleet_data(data, str(date.today()))

        # ORIGINAL METRICS
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Vehicles", total_v)
        c2.metric("Trips", trips)
        c3.metric("Idle", idle)
        c4.metric("Efficiency", eff)

        # STATUS
        st.subheader("Fleet Status")
        st.dataframe(status_df)

        # MANAGER DASHBOARD
        st.divider()
        st.subheader("Manager Dashboard")

        st.dataframe(get_critical(monthly_df).head(10))

        st.subheader("Consistent Vehicles")
        st.dataframe(get_consistent(monthly_df).head(10))

        st.subheader("Problem Vehicles")
        st.dataframe(get_problem(monthly_df).head(10))

        st.subheader("Performance Ranking")
        st.dataframe(add_score(monthly_df).head(10))

        st.subheader("Recommendations")
        for r in recommendations(monthly_df):
            st.warning(r)

        # QUERY
        st.subheader("Smart Query")
        q = st.text_input("Ask query")

        if st.button("Run Query"):
            res = smart_query(q, monthly_df)
            if isinstance(res, str):
                st.warning(res)
            else:
                st.dataframe(res)


with tab2:

    file = st.file_uploader("Upload Driver File")

    if file:
        df = process_driver_file(file)
        save_driver_data(df)

        st.subheader("Driver Summary")
        st.dataframe(driver_summary(df))

        st.subheader("Driver Home Days")
        st.dataframe(driver_home_days(df))
