import pandas as pd


def process_excel(uploaded_file):
    df = pd.read_excel(uploaded_file)

    # Clean column names
    df.columns = [str(col).strip() for col in df.columns]

    # Remove empty rows
    df = df.dropna(how="all")

    # First column = vehicle
    vehicle_col = df.columns[0]

    # 🔥 Find Trip column more intelligently
    trip_col = None
    for col in df.columns:
        if str(col).strip().lower() in ["trip", "trips"]:
            trip_col = col
            break

    # If still not found → TAKE LAST COLUMN (fallback)
    if trip_col is None:
        trip_col = df.columns[-1]

    df = df[[vehicle_col, trip_col]]
    df.columns = ["vehicle", "trips"]

    # 🔥 FORCE CLEAN VALUES
    df["trips"] = (
        df["trips"]
        .astype(str)
        .str.extract(r"(\d+)")[0]   # extract numbers
    )

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

✅ Actions:
- Reassign idle trucks
- Balance workload
- Improve dispatch planning
"""
