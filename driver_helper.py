import pandas as pd


def process_driver_file(file):
    df = pd.read_excel(file)

    df.columns = df.columns.str.strip().str.lower()

    # detect columns automatically
    vehicle_col = [c for c in df.columns if "vehicle" in c][0]
    driver_col = [c for c in df.columns if "driver" in c][0]

    date_cols = [c for c in df.columns if "date" in c]
    days_col = [c for c in df.columns if "day" in c][0]

    df = df[[vehicle_col, driver_col, days_col] + date_cols]

    df.columns = ["vehicle", "driver", "days"] + date_cols

    df["vehicle"] = df["vehicle"].astype(str)
    df["driver"] = df["driver"].astype(str)
    df["days"] = pd.to_numeric(df["days"], errors="coerce").fillna(0)

    # convert dates
    for c in date_cols:
        df[c] = pd.to_datetime(df[c], errors="coerce")

    return df


# ================= DRIVER SUMMARY =================
def driver_summary(df):

    if df.empty:
        return pd.DataFrame()

    # total working days
    driver_days = df.groupby("driver")["days"].sum()

    # vehicles handled
    vehicles = df.groupby("driver")["vehicle"].nunique()

    # assignments count
    assignments = df.groupby("driver").size()

    summary = pd.DataFrame({
        "total_days": driver_days,
        "vehicles": vehicles,
        "assignments": assignments
    }).reset_index()

    return summary.sort_values(by="total_days", ascending=False)


# ================= VEHICLE DRIVER CHANGES =================
def vehicle_driver_changes(df):

    if df.empty:
        return pd.DataFrame()

    changes = df.groupby("vehicle")["driver"].nunique()

    return changes.reset_index(name="driver_changes").sort_values(by="driver_changes", ascending=False)


# ================= DRIVER HOME DAYS (GAPS) =================
def driver_home_days(df):

    if df.empty:
        return pd.DataFrame()

    results = []

    for driver in df["driver"].unique():
        d = df[df["driver"] == driver].sort_values(by=df.columns[3])  # first date column

        home_days = 0

        for i in range(len(d) - 1):
            end = d.iloc[i][df.columns[4]] if len(df.columns) > 4 else None
            next_start = d.iloc[i + 1][df.columns[3]]

            if pd.notna(end) and pd.notna(next_start):
                gap = (next_start - end).days
                if gap > 0:
                    home_days += gap

        results.append({"driver": driver, "home_days": home_days})

    return pd.DataFrame(results).sort_values(by="home_days", ascending=False)


# ================= SMART QUERY =================
def driver_query(user_input, df):

    if df.empty:
        return "No driver data found"

    text = user_input.lower()

    summary = driver_summary(df)

    # specific driver
    for driver in df["driver"].unique():
        if driver.lower() in text:
            d = summary[summary["driver"] == driver].iloc[0]
            return (
                f"{driver} → Days: {int(d['total_days'])}, "
                f"Vehicles: {int(d['vehicles'])}, "
                f"Assignments: {int(d['assignments'])}"
            )

    if "best" in text or "top" in text:
        top = summary.head(5)
        return "\n".join([f"{r.driver} → {int(r.total_days)} days" for r in top.itertuples()])

    if "worst" in text:
        worst = summary.tail(5)
        return "\n".join([f"{r.driver} → {int(r.total_days)} days" for r in worst.itertuples()])

    if "home" in text:
        home = driver_home_days(df)
        top = home.head(5)
        return "\n".join([f"{r.driver} → {int(r.home_days)} days" for r in top.itertuples()])

    if "change" in text:
        changes = vehicle_driver_changes(df)
        top = changes.head(5)
        return "\n".join([f"{r.vehicle} → {int(r.driver_changes)} changes" for r in top.itertuples()])

    return "Ask about best drivers, worst drivers, home days, or driver name"
