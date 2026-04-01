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
        name = f.name
        match = re.search(r'(\d{2})\.(\d{2})', name)
        if match:
            day, month = match.groups()
            date_key = int(month) * 100 + int(day)
            dated_files.append((date_key, f))
    if not dated_files:
        return files[-1]
    return sorted(dated_files, reverse=True)[0][1]


# ================= MONTHLY ANALYSIS =================
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

        if not vehicle or vehicle == "NAN":
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
                num = float(val)
                if num > 0:
                    trips += num
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


# ================= CONSISTENT =================
def get_consistent_vehicles(df):
    return df[
        (df["Days"] > df["Days"].mean() * 0.7) &
        (df["DP"] < df["DP"].mean()) &
        (df["DH"] < df["DH"].mean())
    ].sort_values(by="Trips", ascending=False)


# ================= PROBLEM =================
def get_problem_vehicles(df):
    return df[
        (df["DP"] > df["DP"].mean()) |
        (df["DH"] > df["DH"].mean())
    ].sort_values(by="DP", ascending=False)


# ================= REPEATED OFFENDERS =================
def get_repeated_offenders(df):

    high_dp = df[df["DP"] > df["DP"].mean()]
    high_dh = df[df["DH"] > df["DH"].mean()]

    return high_dp, high_dh


# ================= TREND DETECTION =================
def detect_trend(df):

    df = df.copy()

    df["Trend"] = df.apply(
        lambda x: "⬇️ Dropping"
        if x["Trips"] < df["Trips"].mean()
        else "⬆️ Good",
        axis=1
    )

    return df


# ================= SCORING =================
def add_score(df):

    df = df.copy()

    df["Score"] = (
        df["Trips"]
        - (df["DP"] * 5)
        - (df["DH"] * 3)
    )

    return df.sort_values(by="Score", ascending=False)


# ================= ALERT SYSTEM =================
def add_alerts(df):

    df = df.copy()

    def classify(row):
        if row["DP"] > df["DP"].mean():
            return "🔴 Critical"
        elif row["DH"] > df["DH"].mean():
            return "🟡 Warning"
        else:
            return "🟢 Good"

    df["Alert"] = df.apply(classify, axis=1)

    return df


# ================= APP =================
st.set_page_config(page_title="Fleet Intelligence System", layout="wide")
st.title("🚛 Fleet Intelligence System")

tab1, tab2 = st.tabs(["Fleet", "Driver"])


with tab1:

    files = st.file_uploader("Upload Fleet Files", type=["xlsx"], accept_multiple_files=True)

    if files:

        latest_file = get_latest_file(files)
        df = monthly_analysis(latest_file)

        # ================= METRICS =================
        col1, col2, col3 = st.columns(3)
        col1.metric("Avg DP", round(df["DP"].mean(), 2))
        col2.metric("Avg DH", round(df["DH"].mean(), 2))
        col3.metric("Avg Trips", round(df["Trips"].mean(), 2))

        # ================= CONSISTENT =================
        st.subheader("✅ Consistent Vehicles")
        st.dataframe(get_consistent_vehicles(df).head(10))

        # ================= PROBLEM =================
        st.subheader("❌ Problem Vehicles")
        st.dataframe(get_problem_vehicles(df).head(10))

        # ================= REPEATED =================
        st.subheader("🔁 Repeated Offenders")

        dp_off, dh_off = get_repeated_offenders(df)

        st.write("High Delay Vehicles")
        st.dataframe(dp_off.head(10))

        st.write("High Driver Home Vehicles")
        st.dataframe(dh_off.head(10))

        # ================= TREND =================
        st.subheader("📉 Trend Detection")
        st.dataframe(detect_trend(df).head(20))

        # ================= SCORE =================
        st.subheader("🏆 Performance Score")
        st.dataframe(add_score(df).head(10))

        # ================= ALERT =================
        st.subheader("🚨 Alerts")
        st.dataframe(add_alerts(df).head(20))


# ================= DRIVER =================
with tab2:

    file = st.file_uploader("Upload Driver File")

    if file:
        df = process_driver_file(file)

        save_driver_data(df)

        st.subheader("Driver Summary")
        st.dataframe(driver_summary(df))

        st.subheader("Driver Home Days")
        st.dataframe(driver_home_days(df))
