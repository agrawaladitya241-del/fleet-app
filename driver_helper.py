import pandas as pd
from datetime import datetime


def process_driver_file(file):
    df = pd.read_excel(file)

    df.columns = df.columns.str.strip().str.lower()

    def find_col(names):
        for col in df.columns:
            for n in names:
                if n in col:
                    return col
        return None

    vehicle_col = find_col(["vehicle", "truck"])
    driver_col = find_col(["driver"])
    assigned_col = find_col(["assign", "date", "from"])
    removed_col = find_col(["remove", "to", "end"])

    if not vehicle_col or not driver_col or not assigned_col:
        return pd.DataFrame()

    cols = [vehicle_col, driver_col, assigned_col]
    if removed_col:
        cols.append(removed_col)

    df = df[cols]

    df.columns = ["vehicle", "driver", "assigned"] + (["removed"] if removed_col else [])

    df["assigned"] = pd.to_datetime(df["assigned"], errors="coerce")

    if "removed" in df.columns:
        df["removed"] = pd.to_datetime(df["removed"], errors="coerce")
    else:
        df["removed"] = pd.NaT

    today = pd.to_datetime(datetime.today().date())
    df["removed"] = df["removed"].fillna(today)

    return df


def driver_summary(df):
    df["working_days"] = (df["removed"] - df["assigned"]).dt.days
    df["working_days"] = df["working_days"].fillna(0).clip(lower=0)

    return df.groupby("driver").agg(
        total_days=("working_days", "sum"),
        vehicles=("vehicle", "nunique"),
        assignments=("vehicle", "count")
    ).reset_index()


def driver_home_days(df):
    results = []

    for driver in df["driver"].unique():
        d = df[df["driver"] == driver].sort_values(by="assigned")

        home_days = 0
        for i in range(len(d) - 1):
            gap = (d.iloc[i + 1]["assigned"] - d.iloc[i]["removed"]).days
            if gap > 0:
                home_days += gap

        results.append({"driver": driver, "home_days": home_days})

    return pd.DataFrame(results)


def vehicle_driver_changes(df):
    return df.groupby("vehicle")["driver"].nunique().reset_index(name="driver_changes")


def driver_vehicle_switch(df):
    return df.groupby("driver")["vehicle"].nunique().reset_index(name="vehicles_driven")
