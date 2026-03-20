import pandas as pd

# -------------------------------
# PROCESS FILE
# -------------------------------
def process_driver_file(uploaded_file):
    df = pd.read_excel(uploaded_file)

    df.columns = df.columns.str.strip()

    # Convert dates
    if "Assigned On" in df.columns:
        df["Assigned On"] = pd.to_datetime(df["Assigned On"], errors="coerce")

    if "Removed On" in df.columns:
        df["Removed On"] = pd.to_datetime(df["Removed On"], errors="coerce")

    # Fill missing Removed On
    if "Removed On" in df.columns:
        df["Removed On"].fillna(pd.Timestamp.today(), inplace=True)

    # Calculate days
    if "Assigned On" in df.columns and "Removed On" in df.columns:
        df["calculated_days"] = (df["Removed On"] - df["Assigned On"]).dt.days

    if "Days Assigned" in df.columns:
        df["total_days"] = df["Days Assigned"].fillna(df.get("calculated_days", 0))
    else:
        df["total_days"] = df.get("calculated_days", 0)

    return df


# -------------------------------
# DRIVER SUMMARY
# -------------------------------
def driver_summary(df):
    if "Driver Name" not in df.columns:
        return pd.DataFrame()

    summary = (
        df.groupby("Driver Name")["total_days"]
        .sum()
        .reset_index()
        .rename(columns={"total_days": "total_working_days"})
    )

    return summary


# -------------------------------
# DRIVER QUERY (ADVANCED INSIGHTS)
# -------------------------------
def driver_query(df):
    result = {}

    # Vehicle running months
    if "Vehicle No" in df.columns:
        vehicle_run = (
            df.groupby("Vehicle No")["total_days"]
            .sum()
            .reset_index()
        )
        vehicle_run["running_months"] = (vehicle_run["total_days"] / 30).round(1)
        result["vehicle_run"] = vehicle_run

        # Driver changes
        changes = df.groupby("Vehicle No").size().reset_index(name="driver_changes")
        result["driver_changes"] = changes

        # Least change truck
        if not changes.empty:
            result["least_change_truck"] = changes.sort_values(by="driver_changes").iloc[0]

    return result
