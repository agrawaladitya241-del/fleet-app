import pandas as pd

def process_driver_file(uploaded_file):
    df = pd.read_excel(uploaded_file)

    df.columns = df.columns.str.strip()

    df["Assigned On"] = pd.to_datetime(df["Assigned On"], errors="coerce")
    df["Removed On"] = pd.to_datetime(df["Removed On"], errors="coerce")

    df["Removed On"].fillna(pd.Timestamp.today(), inplace=True)

    df["calculated_days"] = (df["Removed On"] - df["Assigned On"]).dt.days
    df["total_days"] = df["Days Assigned"].fillna(df["calculated_days"])

    return df


def driver_summary(df):
    return (
        df.groupby("Driver Name")["total_days"]
        .sum()
        .reset_index()
        .rename(columns={"total_days": "total_working_days"})
    )


def driver_query(df):
    vehicle_run = (
        df.groupby("Vehicle No")["total_days"]
        .sum()
        .reset_index()
    )
    vehicle_run["running_months"] = (vehicle_run["total_days"] / 30).round(1)

    driver_changes = (
        df.groupby("Vehicle No")
        .size()
        .reset_index(name="driver_changes")
    )

    least_change_truck = driver_changes.sort_values(by="driver_changes").iloc[0]

    return {
        "vehicle_run": vehicle_run,
        "driver_changes": driver_changes,
        "least_change_truck": least_change_truck
    }
