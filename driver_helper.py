import pandas as pd


def process_driver_file(uploaded_file):
    df = pd.read_excel(uploaded_file)

    df.columns = df.columns.str.strip().str.lower()

    # detect columns automatically
    vehicle_col = [c for c in df.columns if "vehicle" in c][0]
    driver_col = [c for c in df.columns if "driver" in c][0]
    assign_col = [c for c in df.columns if "assign" in c][0]
    remove_col = [c for c in df.columns if "remove" in c or "change" in c][0]
    days_col = [c for c in df.columns if "day" in c][0]

    df = df[[vehicle_col, driver_col, assign_col, remove_col, days_col]]

    df.columns = ["vehicle", "driver", "assign_date", "remove_date", "days"]

    df["vehicle"] = df["vehicle"].astype(str).str.replace(" ", "").str.upper()
    df["driver"] = df["driver"].astype(str).str.strip()

    df["assign_date"] = pd.to_datetime(df["assign_date"], errors="coerce")
    df["remove_date"] = pd.to_datetime(df["remove_date"], errors="coerce")

    df["days"] = pd.to_numeric(df["days"], errors="coerce").fillna(0)

    return df


# 🔥 DRIVER SUMMARY
def driver_summary(df):

    driver_days = df.groupby("driver")["days"].sum().reset_index()

    driver_vehicle_count = df.groupby("driver")["vehicle"].nunique().reset_index()
    driver_vehicle_count.columns = ["driver", "vehicle_count"]

    driver_stats = pd.merge(driver_days, driver_vehicle_count, on="driver")

    vehicle_changes = df.groupby("vehicle")["driver"].nunique().reset_index()
    vehicle_changes.columns = ["vehicle", "driver_changes"]

    driver_changes = df.groupby("driver")["vehicle"].nunique().reset_index()
    driver_changes.columns = ["driver", "vehicle_changes"]

    return {
        "driver_stats": driver_stats.sort_values(by="days", ascending=False),
        "driver_changes": driver_changes.sort_values(by="vehicle_changes", ascending=False),
        "vehicle_changes": vehicle_changes.sort_values(by="driver_changes", ascending=False)
    }


# 🔥 DH CALCULATION (CORE LOGIC)
def calculate_driver_dh(df):

    dh_result = {}

    for driver, group in df.groupby("driver"):

        # sort by assignment date
        group = group.sort_values(by="assign_date").reset_index(drop=True)

        dh_days = 0

        for i in range(len(group) - 1):

            current_remove = group.loc[i, "remove_date"]
            next_assign = group.loc[i + 1, "assign_date"]

            if pd.notna(current_remove) and pd.notna(next_assign):

                gap = (next_assign - current_remove).days

                if gap > 0:
                    dh_days += gap

        dh_result[driver] = dh_days

    return dh_result


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

    # DRIVER DETAILS
    if matched_driver:

        driver_df = df[df["driver"] == matched_driver]

        total_days = int(driver_df["days"].sum())
        vehicles = driver_df["vehicle"].nunique()
        changes = len(driver_df)
        dh_days = dh_map.get(matched_driver, 0)

        vehicle_breakdown = driver_df.groupby("vehicle")["days"].sum()

        breakdown_text = "\n".join(
            [f"{v} → {int(days)} days" for v, days in vehicle_breakdown.items()]
        )

        return f"""
Driver: {matched_driver}

Total Working Days: {total_days}
Vehicles Driven: {vehicles}
Assignments: {changes}
Driver Home Days (DH): {dh_days}

--- Vehicle-wise Work ---
{breakdown_text}
"""

    # TOP DRIVERS
    if "top" in text or "most" in text:
        top = df.groupby("driver")["days"].sum().sort_values(ascending=False).head(5)
        return "\n".join([f"{d} → {int(v)} days" for d, v in top.items()])

    return "Ask like: 'Mithun details' or 'driver working days'"
