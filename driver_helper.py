import pandas as pd
from datetime import datetime


def process_driver_file(file):
    df = pd.read_excel(file)

    df.columns = df.columns.str.strip().str.lower()

    # 🔥 SMART COLUMN DETECTION
    def find_col(names):
        for col in df.columns:
            for n in names:
                if n in col:
                    return col
        return None

    vehicle_col = find_col(["vehicle", "truck", "veh"])
    driver_col = find_col(["driver", "name"])
    assigned_col = find_col(["assign", "from", "start", "date"])
    removed_col = find_col(["remove", "to", "end", "till"])

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

    # 🔥 fill missing removed with today
    today = pd.to_datetime(datetime.today().date())
    df["removed"] = df["removed"].fillna(today)

    return df


# ================= DRIVER SUMMARY =================
def driver_summary(df):

    if df.empty:
        return pd.DataFrame(columns=["driver", "total_days", "vehicles", "assignments"])

    df["working_days"] = (df["removed"] - df["assigned"]).dt.days
    df["working_days"] = df["working_days"].fillna(0).clip(lower=0)

    summary = df.groupby("driver").agg(
        total_days=("working_days", "sum"),
        vehicles=("vehicle", "nunique"),
        assignments=("vehicle", "count")
    ).reset_index()

    return summary.sort_values(by="total_days", ascending=False)


# ================= DRIVER HOME DAYS =================
def driver_home_days(df):

    if df.empty:
        return pd.DataFrame(columns=["driver", "home_days"])

    results = []

    for driver in df["driver"].unique():

        d = df[df["driver"] == driver].sort_values(by="assigned")

        home_days = 0

        for i in range(len(d) - 1):
            prev_removed = d.iloc[i]["removed"]
            next_assigned = d.iloc[i + 1]["assigned"]

            if pd.notna(prev_removed) and pd.notna(next_assigned):
                gap = (next_assigned - prev_removed).days
                if gap > 0:
                    home_days += gap

        results.append({
            "driver": driver,
            "home_days": home_days
        })

    return pd.DataFrame(results).sort_values(by="home_days", ascending=False)


# ================= VEHICLE DRIVER CHANGES =================
def vehicle_driver_changes(df):

    if df.empty:
        return pd.DataFrame(columns=["vehicle", "driver_changes"])

    changes = df.groupby("vehicle")["driver"].nunique()

    return changes.reset_index(name="driver_changes").sort_values(by="driver_changes", ascending=False)


# ================= DRIVER VEHICLE SWITCH =================
def driver_vehicle_switch(df):

    if df.empty:
        return pd.DataFrame(columns=["driver", "vehicles_driven"])

    switches = df.groupby("driver")["vehicle"].nunique()

    return switches.reset_index(name="vehicles_driven").sort_values(by="vehicles_driven", ascending=False)
