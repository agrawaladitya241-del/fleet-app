import pandas as pd
from openai import OpenAI
import streamlit as st

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def process_excel(uploaded_file):
    df = pd.read_excel(uploaded_file)

    df.columns = df.columns.str.strip()

    vehicle_col = df.columns[0]
    trip_col = None

    for col in df.columns:
        if "trip" in col.lower():
            trip_col = col

    if trip_col is None:
        return None

    df = df[[vehicle_col, trip_col]]
    df.columns = ["vehicle", "trips"]

    df["trips"] = pd.to_numeric(df["trips"], errors="coerce").fillna(0)

    return df


def fleet_summary(df):
    total_vehicles = len(df)
    total_trips = int(df["trips"].sum())

    total_idle = int((df["trips"] == 0).sum())

    avg_trips = round(total_trips / total_vehicles, 2) if total_vehicles > 0 else 0

    efficiency = round(total_trips / (total_trips + total_idle), 2) if (total_trips + total_idle) > 0 else 0

    return {
        "total_vehicles": total_vehicles,
        "total_trips": total_trips,
        "total_idle": total_idle,
        "avg_trips": avg_trips,
        "efficiency": efficiency
    }


def compare_files(df1, df2):
    summary1 = fleet_summary(df1)
    summary2 = fleet_summary(df2)

    return {
        "file1": summary1,
        "file2": summary2
    }


def generate_insights(summary):
    prompt = f"""
    Fleet Summary:
    Vehicles: {summary['total_vehicles']}
    Trips: {summary['total_trips']}
    Idle: {summary['total_idle']}
    Avg Trips: {summary['avg_trips']}
    Efficiency: {summary['efficiency']}

    Give business insights and suggestions.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content
