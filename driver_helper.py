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


# 🔥 NEW: Partial vehicle match (last 4 digits)
def find_vehicle_by_partial(data, user_input):
    text = user_input.replace(" ", "")
    match = re.findall(r'\d{4}', text)

    if not match:
        return None

    last_digits = match[0]

    for vehicle in data.keys():
        if vehicle.endswith(last_digits):
            return vehicle

    return None


# 🔥 Excel Find-level counting
def count_keyword_in_sheet(uploaded_file, keyword):
    wb = openpyxl.load_workbook(uploaded_file)
    ws = wb.active

    keyword = keyword.upper()
    count = 0

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

    # Detect columns
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
        rm = 0

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
            elif "RM" in val:
                rm += 1

        if vehicle not in data:
            data[vehicle] = {
                "trips": 0,
                "idle": 0,
                "dh": 0,
                "dp": 0,
                "ac": 0,
                "rm": 0
            }

        data[vehicle]["trips"] += trips
        data[vehicle]["idle"] += idle
        data[vehicle]["dh"] += dh
        data[vehicle]["dp"] += dp
        data[vehicle]["ac"] += ac
        data[vehicle]["rm"] += rm

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
                    "ac": 0,
                    "rm": 0
                }

            for key in stats:
                final_data[v][key] += stats[key]

    return final_data


def fleet_summary(files):
    data = merge_files(files)

    total_vehicles = len(data)
    total_trips = sum(v["trips"] for v in data.values())
    total_idle = sum(v["idle"] for v in data.values())

    # Excel Find accurate totals
    total_dh = sum(count_keyword_in_sheet(f, "DH") for f in files)
    total_dp = sum(count_keyword_in_sheet(f, "DP") for f in files)
    total_ac = sum(count_keyword_in_sheet(f, "AC") for f in files)
    total_rm = sum(count_keyword_in_sheet(f, "RM") for f in files)

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
        "total_rm": total_rm,
        "avg_trips": avg_trips,
        "efficiency": efficiency,
        "vehicle_data": data
    }


def smart_query(user_input, files):
    summary = fleet_summary(files)
    data = summary["vehicle_data"]

    text = user_input.lower()

    # FULL or PARTIAL vehicle detection
    vehicle = extract_vehicle(user_input)

    if not vehicle:
        vehicle = find_vehicle_by_partial(data, user_input)

    if vehicle and vehicle in data:
        d = data[vehicle]
        return f"""
{vehicle} Status:
Trips: {d['trips']}
Idle: {d['idle']}
Driver Home (DH): {d['dh']}
Driver Problem (DP): {d['dp']}
Accident (AC): {d['ac']}
Repair/Maintenance (RM): {d['rm']}
"""

    # Smart mapping
    mapping = {
        "dp": ["driver problem", "dp"],
        "dh": ["driver home", "dh"],
        "ac": ["accident", "ac"],
        "rm": ["repair", "maintenance", "rm"],
        "park": ["parking", "park"],
        "wait": ["waiting", "wait"]
    }

    for key, words in mapping.items():
        for w in words:
            if w in text:
                total = summary.get(f"total_{key}", 0)
                return f"{key.upper()} total: {total}"

    # fallback keyword search
    words = text.split()
    ignore = {"how", "many", "days", "is", "are", "the", "in", "of", "for"}

    for word in words:
        if word not in ignore:
            keyword = word.upper()
            total = sum(count_keyword_in_sheet(f, keyword) for f in files)
            if total > 0:
                return f"{keyword} appears {total} times"

    return "Ask anything about fleet data"
