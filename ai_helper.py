import pandas as pd


def process_excel(uploaded_file):
    # Read WITHOUT header assumption
    df = pd.read_excel(uploaded_file, header=None)

    # 🔥 Find the row where "Trip" exists
    header_row = None

    for i in range(len(df)):
        row_values = df.iloc[i].astype(str).str.lower().tolist()
        if any("trip" in val for val in row_values):
            header_row = i
            break

    if header_row is None:
        raise Exception("❌ Could not find 'Trip' column in file")

    # 🔥 Re-read with correct header
    df = pd.read_excel(uploaded_file, header=header_row)

    # Clean columns
    df.columns = [str(col).strip() for col in df.columns]

    # Remove empty rows
    df = df.dropna(how="all")

    # Find trip column
    trip_col = None
    for col in df.columns:
        if "trip" in col.lower():
            trip_col = col
            break

    if trip_col is None:
        raise Exception(f"Trip column not found. Columns: {df.columns}")

    # First column = vehicle
    vehicle_col = df.columns[0]

    df = df[[vehicle_col, trip_col]]
    df.columns = ["vehicle", "trips"]

    # Clean values
    df["trips"] = pd.to_numeric(df["trips"], errors="coerce").fillna(0)

    return df


def fleet_summary(df):
    total_vehicles = len(df)
    total_trips = int(df["trips"].sum())
    total_idle = int((df["trips"] == 0).sum())

    avg_trips = round(total_trips / total_vehicles, 2) if total_vehicles > 0 else 0

    efficiency = round(
        total_trips / (total_trips + total_idle), 2
    ) if (total_trips + total_idle) > 0 else 0

    return {
        "total_vehicles": total_vehicles,
        "total_trips": total_trips,
        "total_idle": total_idle,
        "avg_trips": avg_trips,
        "efficiency": efficiency
    }


def compare_files(df1, df2):
    return {
        "file1": fleet_summary(df1),
        "file2": fleet_summary(df2)
    }


def generate_insights(summary):
    return f"""
🚛 Fleet Performance Insights

Total Vehicles: {summary['total_vehicles']}
Total Trips: {summary['total_trips']}
Idle Vehicles: {summary['total_idle']}
Average Trips per Truck: {summary['avg_trips']}
Efficiency: {summary['efficiency']}

📊 Observations:
- Fleet utilisation needs improvement
- Idle trucks indicate inefficiency

✅ Suggestions:
- Reassign idle trucks
- Improve dispatch planning
"""
