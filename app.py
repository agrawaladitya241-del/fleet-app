import pandas as pd


def process_driver_file(uploaded_file):
    df = pd.read_excel(uploaded_file)

    df.columns = df.columns.str.strip().str.lower()

    # SAFE COLUMN DETECTION
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


def driver_summary(df):
    if df.empty:
        return pd.DataFrame(columns=["driver", "days"])

    driver_days = df.groupby("driver")["days"].sum().reset_index()
    return driver_days.sort_values(by="days", ascending=False)


def driver_query(user_input, df):
    if df.empty:
        return "Driver data not found in file"

    text = user_input.lower()

    for driver in df["driver"].unique():
        if driver.lower() in text:
            d = df[df["driver"] == driver]
            total_days = int(d["days"].sum())
            vehicles = d["vehicle"].nunique()

            return f"{driver} → {total_days} days, {vehicles} vehicles"

    if "top" in text:
        top = df.groupby("driver")["days"].sum().sort_values(ascending=False).head(5)
        return "\n".join([f"{d} → {int(v)} days" for d, v in top.items()])

    return "Ask like: 'Rahul details' or 'top drivers'"
