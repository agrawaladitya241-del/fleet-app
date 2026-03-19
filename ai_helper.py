import pandas as pd


def process_excel(uploaded_file):
    df = pd.read_excel(uploaded_file)

    # Clean column names
    df.columns = [str(col).strip().lower() for col in df.columns]

    # Remove empty rows
    df = df.dropna(how="all")

    # First column = vehicle
    vehicle_col = df.columns[0]

    # Find trip column (flexible)
    trip_col = None
    for col in df.columns:
        if "trip" in col:   # catches trip, trips, Trip etc.
            trip_col = col
            break

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
    summary1 = fleet_summary(df1)
    summary2 = fleet_summary(df2)

    return {
        "file1": summary1,
        "file2": summary2
    }


def generate_insights(summary):
    return f"""
🚛 Fleet Performance Insights

Total Vehicles: {summary['total_vehicles']}
Total Trips: {summary['total_trips']}
Idle Vehicles: {summary['total_idle']}
Average Trips per Truck: {summary['avg_trips']}
Efficiency: {summary['efficiency']}

📊 Key Observations:
- Some trucks are underutilised
- Idle vehicles reduce productivity
- Performance varies across fleet

⚠️ Issues:
- Dispatch inefficiency
- Uneven workload distribution

✅ Recommendations:
- Use idle trucks better
- Balance trip allocation
- Improve planning
"""
