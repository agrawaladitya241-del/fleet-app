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


def process_file(uploaded_file):
    wb = openpyxl.load_workbook(uploaded_file)
    ws = wb.active

    vehicle_col = None
    trips_col = None

    # detect columns
    for row in ws.iter_rows(min_row=1, max_row=10):
        for i, cell in enumerate(row):
            if cell.value:
                text = str(cell.value).upper()
                if "VEHICLE" in text:
                    vehicle_col = i
                if "TRIP" in text:
                    trips_col = i

    data = {}

    if vehicle_col is None:
        return data

    for row in ws.iter_rows(min_row=2):

        vehicle_raw = row[vehicle_col].value
        if not vehicle_raw:
            continue

        vehicle = clean_vehicle(vehicle_raw)

        if not vehicle.startswith("OD"):
            continue

        trips = 0
        if trips_col is not None:
            try:
                trips = int(row[trips_col].value)
            except:
                trips = 0

        dp = dh = ac = rm = park = 0

        # 🔥 Excel FIND LOGIC
        for cell in row:
            val = str(cell.value).upper() if cell.value else ""

            if "DP" in val:
                dp += 1
            if "DH" in val:
                dh += 1
            if "AC" in val:
                ac += 1
            if "RM" in val:
                rm += 1
            if "PARK" in val or "WAIT" in val:
                park += 1

        if vehicle not in data:
            data[vehicle] = {
                "trips": 0,
                "dp": 0,
                "dh": 0,
                "ac": 0,
                "rm": 0,
                "park": 0
            }

        data[vehicle]["trips"] += trips
        data[vehicle]["dp"] += dp
        data[vehicle]["dh"] += dh
        data[vehicle]["ac"] += ac
        data[vehicle]["rm"] += rm
        data[vehicle]["park"] += park

    return data


def merge_files(files):
    final = {}

    for f in files:
        d = process_file(f)

        for v, stats in d.items():
            if v not in final:
                final[v] = {
                    "trips": 0,
                    "dp": 0,
                    "dh": 0,
                    "ac": 0,
                    "rm": 0,
                    "park": 0
                }

            for k in stats:
                final[v][k] += stats[k]

    return final


def fleet_summary(files):
    data = merge_files(files)

    total_vehicles = len(data)
    total_trips = sum(v["trips"] for v in data.values())
    total_idle = sum(v["park"] for v in data.values())

    efficiency = 0
    if (total_trips + total_idle) > 0:
        efficiency = round(total_trips / (total_trips + total_idle), 3)

    return {
        "total_vehicles": total_vehicles,
        "total_trips": total_trips,
        "total_idle": total_idle,
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
        return (
            f"{vehicle} → Trips: {d['trips']}, "
            f"DP: {d['dp']}, DH: {d['dh']}, "
            f"AC: {d['ac']}, RM: {d['rm']}, PARK: {d['park']}"
        )

    if "dp" in text:
        return f"Total DP days: {sum(v['dp'] for v in data.values())}"

    if "dh" in text:
        return f"Total DH days: {sum(v['dh'] for v in data.values())}"

    if "accident" in text or "ac" in text:
        return f"Total AC cases: {sum(v['ac'] for v in data.values())}"

    if "rm" in text or "repair" in text:
        return f"Total RM days: {sum(v['rm'] for v in data.values())}"

    if "park" in text or "idle" in text:
        return f"Total idle days: {sum(v['park'] for v in data.values())}"

    if "best" in text:
        top = sorted(data.items(), key=lambda x: x[1]["trips"], reverse=True)[:5]
        return "\n".join([f"{v} → {d['trips']} trips" for v, d in top])

    if "worst" in text:
        worst = sorted(data.items(), key=lambda x: x[1]["trips"])[:5]
        return "\n".join([f"{v} → {d['trips']} trips" for v, d in worst])

    return "Ask about DP, DH, RM, AC, PARK, trips or vehicle number."
    password = st.text_input("Enter Password", type="password")

if password != "yourpass":
    st.stop()
