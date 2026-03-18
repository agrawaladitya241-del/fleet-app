import openpyxl
import re
from openai import OpenAI
import streamlit as st

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


def clean_vehicle(v):
    return str(v).replace(" ", "").upper()


def process_file(file):
    wb = openpyxl.load_workbook(file)
    ws = wb.active

    vehicle_col, trips_col = None, None

    for row in ws.iter_rows(min_row=1, max_row=10):
        for i, cell in enumerate(row):
            if cell.value:
                t = str(cell.value).upper()
                if "VEHICLE" in t:
                    vehicle_col = i
                if "TRIP" in t:
                    trips_col = i

    data = {}

    for row in ws.iter_rows(min_row=2):
        vehicle = row[vehicle_col].value
        if not vehicle:
            continue

        vehicle = clean_vehicle(vehicle)
        if not vehicle.startswith("OD"):
            continue

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

        data[vehicle] = {"trips": trips, "idle": idle}

    return data


def merge(files):
    combined = {}

    for f in files:
        d = process_file(f)
        for v, stats in d.items():
            if v not in combined:
                combined[v] = {"trips": 0, "idle": 0}
            combined[v]["trips"] += stats["trips"]
            combined[v]["idle"] += stats["idle"]

    return combined


def ask_ai(question, files):
    data = merge(files)

    # convert data to readable text
    context = "\n".join([
        f"{v}: trips={d['trips']}, idle={d['idle']}"
        for v, d in data.items()
    ])

    prompt = f"""
You are a fleet management analyst.

Data:
{context}

User question:
{question}

Answer like a professional analyst:
- give insights
- identify problems
- suggest actions
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content
