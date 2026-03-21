import pandas as pd


def process_driver_file(file):
    df = pd.read_excel(file)

    df.columns = df.columns.str.strip().str.lower()

    # detect columns safely
    vehicle_cols = [c for c in df.columns if "vehicle" in c]
    driver_cols = [c for c in df.columns if "driver" in c]
    days_cols = [c for c in df.columns if "day" in c]

    if not vehicle_cols or not driver_cols or not days_cols:
        return pd.DataFrame(columns=["vehicle", "driver", "days"])

    vehicle_col = vehicle_cols[0]
    driver_col = driver_cols[0]
    days_col = days_cols[0]

    df = df[[vehicle_col, driver_col, days_col]]
    df.columns = ["vehicle", "driver", "days"]

    df["vehicle"] = df["vehicle"].astype(str)
    df["driver"] = df["driver"].astype(str)
    df["days"] = pd.to_numeric(df["days"], errors="coerce").fillna(0)

    return df


# ================= DRIVER SUMMARY =================
def driver_summary(df):

    if df.empty:
        return pd.DataFrame(columns=["driver", "total_days", "vehicles", "assignments"])

    driver_days = df.groupby("driver")["days"].sum()
    vehicles = df.groupby("driver")["vehicle"].nunique()
    assignments = df.groupby("driver").size()

    summary = pd.DataFrame({
        "total_days": driver_days,
        "vehicles": vehicles,
        "assignments": assignments
    }).reset_index()

    return summary.sort_values(by="total_days", ascending=False)


# ================= DRIVER CHANGES =================
def vehicle_driver_changes(df):

    if df.empty:
        return pd.DataFrame(columns=["vehicle", "driver_changes"])

    changes = df.groupby("vehicle")["driver"].nunique()

    return changes.reset_index(name="driver_changes").sort_values(by="driver_changes", ascending=False)


# ================= DRIVER HOME DAYS (SIMPLIFIED) =================
def driver_home_days(df):

    if df.empty:
        return pd.DataFrame(columns=["driver", "home_days"])

    # simple logic: fewer working days = more home days (relative)
    max_days = df.groupby("driver")["days"].sum().max()

    driver_days = df.groupby("driver")["days"].sum()

    home_days = max_days - driver_days

    result = pd.DataFrame({
        "driver": driver_days.index,
        "home_days": home_days
    })

    return result.sort_values(by="home_days", ascending=False)


# ================= SMART QUERY =================
def driver_query(user_input, df):

    if df.empty:
        return "No driver data"

    text = user_input.lower()
    summary = driver_summary(df)

    for driver in df["driver"].unique():
        if driver.lower() in text:
            d = summary[summary["driver"] == driver].iloc[0]
            return f"{driver} → Days: {int(d['total_days'])}, Vehicles: {int(d['vehicles'])}"

    if "best" in text:
        top = summary.head(5)
        return "\n".join([f"{r.driver} → {int(r.total_days)} days" for r in top.itertuples()])

    if "worst" in text:
        worst = summary.tail(5)
        return "\n".join([f"{r.driver} → {int(r.total_days)} days" for r in worst.itertuples()])

    return "Ask about drivers"
