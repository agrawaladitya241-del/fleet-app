import pandas as pd

def process_driver_file(uploaded_file):
    df = pd.read_excel(uploaded_file)

    df.columns = df.columns.str.strip()

    # Date cleaning
    df["Assigned On"] = pd.to_datetime(df["Assigned On"], errors="coerce")
    df["Removed On"] = pd.to_datetime(df["Removed On"], errors="coerce")

    # Fill missing removed dates
    df["Removed On"].fillna(pd.Timestamp.today(), inplace=True)

    # Calculate days
    df["calculated_days"] = (df["Removed On"] - df["Assigned On"]).dt.days
    df["total_days"] = df["Days Assigned"].fillna(df["calculated_days"])

    return df


def driver_summary(df):
    driver_stats = (
        df.groupby("Driver Name")["total_days"]
        .sum()
        .reset_index()
        .rename(columns={"total_days": "total_working_days"})
    )

    return driver_stats


def vehicle_summary(df):
    vehicle_run = (
        df.groupby("Vehicle No")["total_days"]
        .sum()
        .reset_index()
    )

    vehicle_run["running_months"] = (vehicle_run["total_days"] / 30).round(1)

    return vehicle_run


def driver_changes(df):
    return df.groupby("Vehicle No").size().reset_index(name="driver_changes")


def driver_query(df):
    # Optional placeholder (so import doesn't break)
    return {"status": "ok"}
