import pandas as pd

def process_driver_file(uploaded_file):
    df = pd.read_excel(uploaded_file)

    df.columns = df.columns.str.strip().str.lower()

    vehicle_col = [c for c in df.columns if "vehicle" in c][0]
    driver_col = [c for c in df.columns if "driver" in c][0]
    days_col = [c for c in df.columns if "day" in c][0]

    df = df[[vehicle_col, driver_col, days_col]]
    df.columns = ["vehicle", "driver", "days"]

    df["vehicle"] = df["vehicle"].astype(str).str.replace(" ", "").str.upper()
    df["driver"] = df["driver"].astype(str).str.strip()
    df["days"] = pd.to_numeric(df["days"], errors="coerce").fillna(0)

    return df


def driver_summary(df):

    driver_days = df.groupby("driver")["days"].sum().reset_index()

    driver_vehicle_count = df.groupby("driver")["vehicle"].nunique().reset_index()
    driver_vehicle_count.columns = ["driver", "vehicle_count"]

    driver_stats = pd.merge(driver_days, driver_vehicle_count, on="driver")

    vehicle_changes = df.groupby("vehicle")["driver"].nunique().reset_index()
    vehicle_changes.columns = ["vehicle", "driver_changes"]

    driver_changes = df.groupby("driver")["vehicle"].nunique().reset_index()
    driver_changes.columns = ["driver", "vehicle_changes"]

    return {
        "driver_stats": driver_stats.sort_values(by="days", ascending=False),
        "driver_changes": driver_changes.sort_values(by="vehicle_changes", ascending=False),
        "vehicle_changes": vehicle_changes.sort_values(by="driver_changes", ascending=False)
    }
