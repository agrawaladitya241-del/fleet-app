import pandas as pd


def process_driver_file(uploaded_file):
    df = pd.read_excel(uploaded_file)

    df.columns = df.columns.str.strip().str.lower()

    vehicle_col = [c for c in df.columns if "vehicle" in c][0]
    driver_col = [c for c in df.columns if "driver" in c][0]
    days_col = [c for c in df.columns if "day" in c][0]

    df = df[[vehicle_col, driver_col, days_col]]
    df.columns = ["vehicle", "driver", "days"]

    df["vehicle"] = df["vehicle"].astype(str)
    df["driver"] = df["driver"].astype(str)
    df["days"] = pd.to_numeric(df["days"], errors="coerce").fillna(0)

    return df


def driver_summary(df):
    driver_days = df.groupby("driver")["days"].sum().reset_index()
    driver_days = driver_days.sort_values(by="days", ascending=False)
    return driver_days


def driver_query(user_input, df):
    text = user_input.lower()

    for driver in df["driver"].unique():
        if driver.lower() in text:
            d = df[df["driver"] == driver]
            total_days = int(d["days"].sum())
            vehicles = d["vehicle"].nunique()

            return f"""
Driver: {driver}
Working Days: {total_days}
Vehicles Driven: {vehicles}
"""

    if "top" in text:
        top = df.groupby("driver")["days"].sum().sort_values(ascending=False).head(5)
        return "\n".join([f"{d} → {int(v)} days" for d, v in top.items()])

    return "Ask like: 'Rahul details' or 'top drivers'"
