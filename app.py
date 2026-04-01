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


# ================= FLEET =================
def process_file(file):
    wb = openpyxl.load_workbook(file)
    ws = wb.active

    vehicle_col = trips_col = None

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
        if not row[vehicle_col].value:
            continue

        vehicle = str(row[vehicle_col].value).upper().replace(" ", "")

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


# ================= DRIVER INTELLIGENCE =================
def driver_intelligence(df):

    high_dh = df[df["DH"] > df["DH"].mean()]
    low_trips = df[df["Trips"] < df["Trips"].mean()]

    return high_dh, low_trips


# ================= ASSIGNMENT SUGGESTIONS =================
def assignment_suggestions(df):

    suggestions = []

    problem = df[df["DP"] > df["DP"].mean()]
    idle = df[df["Trips"] < df["Trips"].mean()]

    if len(problem) > 0:
        suggestions.append("⚠️ Reassign better drivers to high delay vehicles")

    if len(idle) > 0:
        suggestions.append("📉 Some vehicles underutilized — increase allocation")

    good = df[df["Trips"] > df["Trips"].mean()]
    if len(good) > 0:
        suggestions.append("✅ High performing vehicles can handle more load")

    return suggestions


# ================= MONTHLY SUMMARY =================
def monthly_summary(df):

    total = len(df)

    dp_vehicles = len(df[df["DP"] > 0])
    dh_vehicles = len(df[df["DH"] > 0])

    return {
        "total": total,
        "dp": dp_vehicles,
        "dh": dh_vehicles,
        "dp_percent": round((dp_vehicles / total) * 100, 2),
        "dh_percent": round((dh_vehicles / total) * 100, 2)
    }


# ================= REPORT =================
def generate_report(df):

    summary = monthly_summary(df)

    report = f"""
Fleet Monthly Report:

Total Vehicles: {summary['total']}
Vehicles with Delay (DP): {summary['dp']} ({summary['dp_percent']}%)
Vehicles with Driver Home (DH): {summary['dh']} ({summary['dh_percent']}%)

Overall, delays and driver issues indicate areas requiring operational attention.
"""

    return report


# ================= APP =================
st.set_page_config(layout="wide")
st.title("🚛 Fleet Intelligence System")

tab1, tab2 = st.tabs(["Fleet", "Driver"])


with tab1:

    files = st.file_uploader("Upload Fleet Files", type=["xlsx"], accept_multiple_files=True)

    if files:

        latest_file = get_latest_file(files)

        data = process_file(latest_file)
        df = monthly_analysis(latest_file)

        save_fleet_data(data, str(date.today()))

        # ================= SUMMARY =================
        summary = monthly_summary(df)

        c1, c2, c3 = st.columns(3)
        c1.metric("Total Vehicles", summary["total"])
        c2.metric("Vehicles with DP", summary["dp"])
        c3.metric("Vehicles with DH", summary["dh"])

        # ================= DRIVER INTELLIGENCE =================
        st.subheader("🧠 Driver Intelligence")

        dh_issues, low_perf = driver_intelligence(df)

        st.write("Driver Issues (High DH)")
        st.dataframe(dh_issues.head(10))

        st.write("Low Performance Vehicles")
        st.dataframe(low_perf.head(10))

        # ================= ASSIGNMENT =================
        st.subheader("🚛 Assignment Suggestions")

        for s in assignment_suggestions(df):
            st.info(s)

        # ================= REPORT =================
        st.subheader("📄 Monthly Report")
        st.text(generate_report(df))


with tab2:

    file = st.file_uploader("Upload Driver File")

    if file:
        df = process_driver_file(file)
        save_driver_data(df)

        st.subheader("Driver Summary")
        st.dataframe(driver_summary(df))

        st.subheader("Driver Home Days")
        st.dataframe(driver_home_days(df))
