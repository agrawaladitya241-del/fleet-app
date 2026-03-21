import pandas as pd
from datetime import datetime


def process_driver_file(file):
    df = pd.read_excel(file)

    # clean column names
    df.columns = df.columns.str.strip().str.lower()

    # 🔥 FORCE MATCH (NO GUESSING FAILURE)
    vehicle_col = None
    driver_col = None
    assigned_col = None
    removed_col = None

    for col in df.columns:
        if "vehicle" in col:
            vehicle_col = col
        elif "driver" in col:
            driver_col = col
        elif "assign" in col or "from" in col:
            assigned_col = col
        elif "remov" in col or "to" in col:
            removed_col = col

    # if required columns missing → return empty safely
    if not vehicle_col or not driver_col or not assigned_col:
        return pd.DataFrame()

    # select columns
    cols = [vehicle_col, driver_col, assigned_col]
    if removed_col:
        cols.append(removed_col)

    df = df[cols]

    # rename
    df.columns = ["vehicle", "driver", "assigned"] + (["removed"] if removed_col else [])

    # convert to datetime
    df["assigned"] = pd.to_datetime(df["assigned"], errors="coerce")

    if "removed" in df.columns:
        df["removed"] = pd.to_datetime(df["removed"], errors="coerce")
    else:
        df["removed"] = pd.NaT

    # 🔥 FIX: if removed missing → assume today
    today = pd.to_datetime(datetime.today().date())
    df["removed"] = df["removed"].fillna(today)

    return df


# ================= DRIVER SUMMARY =================
def driver_summary(df):

    if df.empty:
        return pd.DataFrame(columns=["driver", "total_days", "vehicles", "assignments"])

    # 🔥 calculate working days ONLY from dates
    df["working_days"] = (df["removed"] - df["assigned"]).dt.days

    df["working_days"] = df["working_days"].fillna(0)
    df["working_days"] = df["working_days"].clip(lower=0)

    summary = df.groupby("driver").agg(
        total_days=("working_days", "sum"),
        vehicles=("vehicle", "nunique"),
        assignments=("vehicle", "count")
    ).reset_index()

    return summary.sort_values(by="total_days", ascending=False)


# ================= HOME DAYS =================
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


# ================= DRIVER CHANGES =================
def vehicle_driver_changes(df):

    if df.empty:
        return pd.DataFrame(columns=["vehicle", "driver_changes"])

    changes = df.groupby("vehicle")["driver"].nunique()

    return changes.reset_index(name="driver_changes").sort_values(by="driver_changes", ascending=False)
