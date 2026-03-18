import openpyxl
import re

SHEET_NAME = "March"


def clean_vehicle(v):
    if isinstance(v, str):
        return v.replace(" ", "").upper()
    return ""


def extract_vehicle(text):
    text = text.upper().replace(" ", "")
    match = re.findall(r'[A-Z]{2}[0-9]{2}[A-Z]{2}[0-9]{4}', text)
    if match:
        return match[0]
    return None


def fleet_summary(uploaded_file):
    wb = openpyxl.load_workbook(uploaded_file)
    ws = wb[SHEET_NAME]

    vehicle_col = None
    trips_col = None

    # find columns
    for row in ws.iter_rows(min_row=1, max_row=10):
        for i, cell in enumerate(row):
            if cell.value:
                text = str(cell.value).upper()
                if "VEHICLE" in text:
                    vehicle_col = i
                if "TRIP" in text:
                    trips_col = i

    if vehicle_col is None or trips_col is None:
        return {
            "total_vehicles": 0,
            "total_trips": 0,
            "total_idle": 0,
            "avg_trips": 0,
            "avg_idle": 0,
            "efficiency": 0,
            "vehicle_data": {}
        }

    data = {}

    for row in ws.iter_rows(min_row=2):

        vehicle_raw = row[vehicle_col].value

        if not vehicle_raw:
            continue

        vehicle = clean_vehicle(vehicle_raw)

        if not vehicle.startswith("OD"):
            continue

        # trips
        trips_cell = row[trips_col].value
        try:
            trips = int(trips_cell)
        except:
            trips = 0

        idle = 0

        for i, cell in enumerate(row):
            if i == vehicle_col or i == trips_col:
                continue

            value = str(cell.value).upper() if cell.value else ""

            if "WAIT" in value or "PARK" in value:
                idle += 1

        data[vehicle] = {"trips": trips, "idle": idle}

    total_vehicles = len(data)

    if total_vehicles == 0:
        return {
            "total_vehicles": 0,
            "total_trips": 0,
            "total_idle": 0,
            "avg_trips": 0,
            "avg_idle": 0,
            "efficiency": 0,
            "vehicle_data": {}
        }

    total_trips = sum(v["trips"] for v in data.values())
    total_idle = sum(v["idle"] for v in data.values())

    avg_trips = round(total_trips / total_vehicles, 2)
    avg_idle = round(total_idle / total_vehicles, 2)

    efficiency = round(total_trips / (total_trips + total_idle), 3)

    return {
        "total_vehicles": total_vehicles,
        "total_trips": total_trips,
        "total_idle": total_idle,
        "avg_trips": avg_trips,
        "avg_idle": avg_idle,
        "efficiency": efficiency,
        "vehicle_data": data
    }


def ask_ai(user_input, uploaded_file):
    vehicle = extract_vehicle(user_input)

    if not vehicle:
        return "I could not detect vehicle number."

    summary = fleet_summary(uploaded_file)
    data = summary["vehicle_data"]

    if vehicle not in data:
        return "Vehicle not found."

    trips = data[vehicle]["trips"]
    idle = data[vehicle]["idle"]

    if (trips + idle) == 0:
        efficiency = 0
    else:
        efficiency = round(trips / (trips + idle), 2)

    return f"""
Vehicle: {vehicle}

Trips: {trips}
Idle Days: {idle}
Efficiency: {efficiency}
"""


def get_top_worst(uploaded_file):
    summary = fleet_summary(uploaded_file)
    data = summary["vehicle_data"]

    sorted_data = sorted(data.items(), key=lambda x: x[1]["trips"], reverse=True)

    top = sorted_data[:5]
    worst = sorted_data[-5:]

    return top, worst