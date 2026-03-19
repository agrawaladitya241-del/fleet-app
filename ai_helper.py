import openpyxl
import re


def clean_vehicle(v):
    if isinstance(v, str):
        return v.replace(" ", "").upper()
    return ""


def extract_vehicle(text):
    text = text.upper().replace(" ", "")
    match = re.findall(r'[A-Z]{2}[0-9]{2}[A-Z]{2}[0-9]{4}', text)
    return match[0] if match else None


# 🔥 EXACT EXCEL FIND LOGIC
def count_keyword_in_sheet(uploaded_file, keyword):
    wb = openpyxl.load_workbook(uploaded_file)
    ws = wb.active

    count = 0
    keyword = keyword.upper()

    for row in ws.iter_rows():
        for cell in row:
            if cell.value:
                val = str(cell.value).upper()
                count += val.count(keyword)

    return count


def process_file(uploaded_file):
    wb = openpyxl.load_workbook(uploaded_file)
    ws = wb.active

    vehicle_col = None
    trips_col = None
    header_row = 1

    # Find columns
    for i, row in enumerate(ws.iter_rows(min_row=1, max_row=15), start=1):
        for j, cell in enumerate(row):
            if cell.value:
                text = str(cell.value).upper()
                if "VEHICLE" in text:
                    vehicle_col = j
                    header_row = i
                if "TRIP" in text:
                    trips_col = j
                    header_row = i

    if vehicle_col is None or trips_col is None:
        return {}

    data = {}

    for row in ws.iter_rows(min_row=header_row + 1):

        vehicle_raw = row[vehicle_col].value
        if not vehicle_raw:
            continue

        vehicle = clean_vehicle(vehicle_raw)
        if not vehicle.startswith("OD"):
            continue

        try:
            trips = int(row[trips_col].value)
        except:
            trips = 0

        idle = 0
        dh = 0
        dp = 0
        ac = 0

        for i, cell in enumerate(row):
            if i in [vehicle_col, trips_col]:
                continue

            val = str(cell.value).upper() if cell.value else ""

            if "WAIT" in val or "PARK" in val:
                idle += 1
            elif "DH" in val:
                dh += 1
            elif "DP" in val:
                dp += 1
            elif "AC" in val:
                ac += 1

        if vehicle not in data:
            data[vehicle] = {
                "trips": 0,
                "idle": 0,
                "dh": 0,
                "dp": 0,
                "ac": 0
            }

        data[vehicle]["trips"] += trips
        data[vehicle]["idle"] += idle
        data[vehicle]["dh"] += dh
        data[vehicle]["dp"] += dp
        data[vehicle]["ac"] += ac

    return data


def merge_files(files):
    final_data = {}

    for f in files:
        file_data = process_file(f)

        for v, stats in file_data.items():
            if v not in final_data:
                final_data[v] = {
                    "trips": 0,
                    "idle": 0,
                    "dh": 0,
                    "dp": 0,
                    "ac": 0
                }

            final_data[v]["trips"] += stats["trips"]
            final_data[v]["idle"] += stats["idle"]
            final_data[v]["dh"] += stats["dh"]
            final_data[v]["dp"] += stats["dp"]
            final_data[v]["ac"] += stats["ac"]

    return final_data


def fleet_summary(files):
    data = merge_files(files)

    # 🔥 VEHICLE BASED
    total_vehicles = len(data)
    total_trips = sum(v["trips"] for v in data.values())
    total_idle = sum(v["idle"] for v in data.values())

    # 🔥 EXCEL FIND BASED (ACCURATE)
    total_dh = sum(count_keyword_in_sheet(f, "DH") for f in files)
    total_dp = sum(count_keyword_in_sheet(f, "DP") for f in files)
    total_ac = sum(count_keyword_in_sheet(f, "AC") for f in files)

    avg_trips = round(total_trips / total_vehicles, 2) if total_vehicles else 0

    efficiency = round(
        total_trips / (total_trips + total_idle), 3
    ) if (total_trips + total_idle) else 0

    return {
        "total_vehicles": total_vehicles,
        "total_trips": total_trips,
        "total_idle": total_idle,
        "total_dh": total_dh,
        "total_dp": total_dp,
        "total_ac": total_ac,
        "avg_trips": avg_trips,
        "efficiency": efficiency,
        "vehicle_data": data
    }


def smart_query(user_input, files):
    summary = fleet_summary(files)
    data = summary["vehicle_data"]

    text = user_input.lower()

    vehicle = extract_vehicle(user_input)
    if vehicle and vehicle in data:
        d = data[vehicle]
        return f"{vehicle} → Trips: {d['trips']}, Idle: {d['idle']}, DH: {d['dh']}, DP: {d['dp']}, AC: {d['ac']}"

    if "total" in text and "trip" in text:
        return f"Total trips: {summary['total_trips']}"

    if "idle" in text:
        return f"Total idle: {summary['total_idle']}"

    if "dh" in text or "driver home" in text:
        return f"Total DH days: {summary['total_dh']}"

    if "dp" in text or "driver problem" in text:
        return f"Total DP days: {summary['total_dp']}"

    if "ac" in text or "accident" in text:
        return f"Total AC days: {summary['total_ac']}"

    if "best" in text or "top" in text:
        top = sorted(data.items(), key=lambda x: x[1]["trips"], reverse=True)[:5]
        return "\n".join([f"{v} → {d['trips']} trips" for v, d in top])

    if "worst" in text or "low" in text:
        worst = sorted(data.items(), key=lambda x: x[1]["trips"])[:5]
        return "\n".join([f"{v} → {d['trips']} trips" for v, d in worst])

    return "Ask about trips, idle, DH, DP, AC or vehicle number."
