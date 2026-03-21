import pandas as pd


def process_driver_file(file):
    df = pd.read_excel(file)

    df.columns = df.columns.str.strip().str.lower()

    # detect columns
    vehicle_col = [c for c in df.columns if "vehicle" in c][0]
    driver_col = [c for c in df.columns if "driver" in c][0]

    assigned_col = [c for c in df.columns if "assign" in c][0]
    removed_col = [c for c in df.columns if "remov" in c][0]

    df = df[[vehicle_col, driver_col, assigned_col, removed_col]]
    df.columns = ["vehicle", "driver", "assigned", "removed"]

    df["assigned"] = pd.to_datetime(df["assigned"], errors="coerce")
    df["removed"] = pd.to_datetime(df["removed"], errors="coerce")

    return df


# ================= DRIVER SUMMARY =================
def driver_summary(df):

    if df.empty:
        return pd.DataFrame()

    df["working_days"] = (df["removed"] - df["assigned"]).dt.days.fillna(0)

    summary = df.groupby("driver").agg(
        total_days=("working_days", "sum"),
        vehicles=("vehicle", "nunique"),
        assignments=("vehicle", "count")
    ).reset_index()

    return summary.sort_values(by="total_days", ascending=False)


# ================= DRIVER HOME DAYS =================
def driver_home_days(df):

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

    changes = df.groupby("vehicle")["driver"].nunique()

    return changes.reset_index(name="driver_changes").sort_values(by="driver_changes", ascending=False)
