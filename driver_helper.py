import pandas as pd
from datetime import datetime


# ================= EXISTING LOGIC (UNCHANGED) =================
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


def vehicle_home_days(df):
    home_df = driver_home_days(df)
    driver_home_map = dict(zip(home_df["driver"], home_df["home_days"]))

    df["home_days"] = df["driver"].map(driver_home_map)

    return df.groupby("vehicle")["home_days"].sum().reset_index()


# ================= NEW LOGIC (DP / DH / STATUS) =================
def extract_dp_dh_status(file):
    df = pd.read_excel(file)
    df.columns = df.columns.astype(str)

    results = []

    for _, row in df.iterrows():

        row_values = [str(x).upper() for x in row if pd.notna(x)]

        dh_count = sum(1 for x in row_values if "DH" in x)
        dp_count = sum(1 for x in row_values if "DP" in x)

        # Get driver + vehicle safely
        driver = ""
        vehicle = ""

        for col in df.columns:
            if "driver" in col.lower():
                driver = row[col]
            if "vehicle" in col.lower() or "truck" in col.lower():
                vehicle = row[col]

        # Last non-empty cell
        current_status = ""
        for val in reversed(row_values):
            if val.strip():
                current_status = val
                break

        # Status classification
        if "DH" in current_status:
            status_type = "Driver Home"
        elif "DP" in current_status:
            status_type = "Delay"
        else:
            status_type = "Active"

        results.append({
            "driver": driver,
            "vehicle": vehicle,
            "DH": dh_count,
            "DP": dp_count,
            "current_status": current_status,
            "status_type": status_type
        })

    return pd.DataFrame(results)


# ================= DRIVER SEARCH (UNCHANGED) =================
def driver_query(user_input, df):

    text = user_input.lower()

    summary = driver_summary(df)
    home = driver_home_days(df)
    switch = driver_vehicle_switch(df)

    merged = summary.merge(home, on="driver", how="left")
    merged = merged.merge(switch, on="driver", how="left")

    for driver in merged["driver"]:
        if driver.lower() in text:
            d = merged[merged["driver"] == driver].iloc[0]
            return f"{driver} → Days: {d['total_days']}, Home: {d['home_days']}, Vehicles: {d['vehicles_driven']}"

    if "top" in text:
        top = merged.sort_values(by="total_days", ascending=False).head(5)
        return "\n".join([f"{r['driver']} → {r['total_days']} days" for _, r in top.iterrows()])

    if "home" in text:
        top = merged.sort_values(by="home_days", ascending=False).head(5)
        return "\n".join([f"{r['driver']} → {r['home_days']} home days" for _, r in top.iterrows()])

    if "vehicle" in text or "switch" in text:
        top = merged.sort_values(by="vehicles_driven", ascending=False).head(5)
        return "\n".join([f"{r['driver']} → {r['vehicles_driven']} vehicles" for _, r in top.iterrows()])

    return "Try: top drivers, home days, or driver name"
