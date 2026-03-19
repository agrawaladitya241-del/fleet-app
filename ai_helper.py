import pandas as pd


def process_excel(uploaded_file):
    # 🔥 Read with header auto-detection fix
    df = pd.read_excel(uploaded_file, header=0)

    # Drop empty rows
    df = df.dropna(how="all")

    # Reset index
    df = df.reset_index(drop=True)

    # Clean column names
    df.columns = [str(col).strip() for col in df.columns]

    # DEBUG (important)
    print("COLUMNS FOUND:", df.columns)

    # Try to find Trip column
    trip_col = None
    for col in df.columns:
        if "trip" in col.lower():
            trip_col = col
            break

    # If not found → show error clearly
    if trip_col is None:
        raise Exception(f"Trip column not found. Columns detected: {df.columns}")

    # First column = vehicle
    vehicle_col = df.columns[0]

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
    return {
        "file1": fleet_summary(df1),
        "file2": fleet_summary(df2)
    }


def generate_insights(summary):
    return f"""
Fleet Summary:

Vehicles: {summary['total_vehicles']}
Trips: {summary['total_trips']}
Idle: {summary['total_idle']}

Observation:
Fleet utilisation needs improvement.
"""
