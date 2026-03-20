import pandas as pd


def process_driver_file(uploaded_file):
    df = pd.read_excel(uploaded_file)

    df.columns = df.columns.str.strip().str.lower()

    vehicle_col = [c for c in df.columns if "vehicle" in c][0]
    driver_col = [c for c in df.columns if "driver" in c][0]
    assign_col = [c for c in df.columns if "assign" in c][0]
    remove_col = [c for c in df.columns if "remove" in c or "change" in c][0]
    days_col = [c for c in df.columns if "day" in c][0]

    df = df[[vehicle_col, driver_col, assign_col, remove_col, days_col]]
    df.columns = ["vehicle", "driver", "assign_date", "remove_date", "days"]

    df["vehicle"] = df["vehicle"].astype(str).str.replace(" ", "").str.upper()
    df["driver"] = df["driver"].astype(str).str.strip()

    df["assign_date"] = pd.to_datetime(df["assign_date"], errors="coerce", dayfirst=True)
    df["remove_date"] = pd.to_datetime(df["remove_date"], errors="coerce", dayfirst=True)

    df["days"] = pd.to_numeric(df["days"], errors="coerce").fillna(0)

    return df


# 🔥 DH CALCULATION (FIXED)
def calculate_driver_dh(df):

    dh_result = {}

    for driver, group in df.groupby("driver"):

        # 🔥 SORT PROPERLY
        group = group.sort_values(by="assign_date").reset_index(drop=True)

        dh_days = 0

        for i in range(len(group) - 1):

            current_remove = group.loc[i, "remove_date"]
            next_assign = group.loc[i + 1, "assign_date"]

            # 🔥 ignore missing values
            if pd.isna(current_remove) or pd.isna(next_assign):
                continue

            gap = (next_assign - current_remove).days

            # 🔥 only valid gaps
            if gap > 0:
                dh_days += gap

        dh_result[driver] = dh_days

    return dh_result


# 🔥 DRIVER SUMMARY WITH HIGH LEAVE FLAG
def driver_summary(df):

    driver_days = df.groupby("driver")["days"].sum().reset_index()

    driver_vehicle_count = df.groupby("driver")["vehicle"].nunique().reset_index()
    driver_vehicle_count.columns = ["driver", "vehicle_count"]

    driver_stats = pd.merge(driver_days, driver_vehicle_count, on="driver")

    # 🔥 add DH
    dh_map = calculate_driver_dh(df)
    driver_stats["dh_days"] = driver_stats["driver"].map(dh_map)

    # 🔥 HIGH LEAVE FLAG
    driver_stats["status"] = driver_stats["dh_days"].apply(
        lambda x: "⚠️ High Leave" if x > 10 else "OK"
    )

    return driver_stats.sort_values(by="dh_days", ascending=False)


# 🔥 SMART QUERY
def driver_query(user_input, df):

    text = user_input.lower()

    drivers = df["driver"].unique()
    matched_driver = None

    for d in drivers:
        if d.lower() in text:
            matched_driver = d
            break

    dh_map = calculate_driver_dh(df)

    if matched_driver:

        driver_df = df[df["driver"] == matched_driver]

        total_days = int(driver_df["days"].sum())
        vehicles = driver_df["vehicle"].nunique()
        changes = len(driver_df)
        dh_days = dh_map.get(matched_driver, 0)

        return f"""
Driver: {matched_driver}

Working Days: {total_days}
Driver Home Days (DH): {dh_days}
Vehicles Driven: {vehicles}
Assignments: {changes}
"""

    # 🔥 HIGH LEAVE DRIVERS
    if "high" in text or "leave" in text:

        high = {k: v for k, v in dh_map.items() if v > 10}

        if not high:
            return "No high leave drivers found"

        return "\n".join([f"{d} → {v} DH days" for d, v in high.items()])

    return "Ask like: 'Mithun details' or 'high leave drivers'"
