import streamlit as st
import pandas as pd

st.set_page_config(page_title="Fleet Dashboard", layout="wide")

st.title("🚛 Fleet & Driver Performance Dashboard")

# -------------------------------
# FILE UPLOAD
# -------------------------------
uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file)

    # -------------------------------
    # DATA CLEANING
    # -------------------------------
    df.columns = df.columns.str.strip()

    df["Assigned On"] = pd.to_datetime(df["Assigned On"], errors="coerce")
    df["Removed On"] = pd.to_datetime(df["Removed On"], errors="coerce")

    # Fill missing Removed On with today
    df["Removed On"].fillna(pd.Timestamp.today(), inplace=True)

    # Calculate days safely
    df["calculated_days"] = (df["Removed On"] - df["Assigned On"]).dt.days
    df["total_days"] = df["Days Assigned"].fillna(df["calculated_days"])

    # -------------------------------
    # DRIVER LEAVE / ASSIGNMENT SUMMARY
    # -------------------------------
    driver_stats = (
        df.groupby("Driver Name")["total_days"]
        .sum()
        .reset_index()
        .rename(columns={"total_days": "total_working_days"})
    )

    # Threshold for highlighting
    THRESHOLD = 300

    driver_stats["status"] = driver_stats["total_working_days"].apply(
        lambda x: "⚠️ High Load" if x > THRESHOLD else "✅ Normal"
    )

    # -------------------------------
    # VEHICLE RUNNING MONTHS
    # -------------------------------
    vehicle_run = (
        df.groupby("Vehicle No")["total_days"]
        .sum()
        .reset_index()
    )

    vehicle_run["running_months"] = (vehicle_run["total_days"] / 30).round(1)

    # -------------------------------
    # DRIVER CHANGES PER VEHICLE
    # -------------------------------
    driver_changes = (
        df.groupby("Vehicle No")
        .size()
        .reset_index(name="driver_changes")
    )

    # Least driver change truck
    least_change_truck = driver_changes.sort_values(by="driver_changes").iloc[0]

    # -------------------------------
    # UI LAYOUT
    # -------------------------------
    tab1, tab2, tab3 = st.tabs(["📊 Driver Stats", "🚛 Vehicle Usage", "🔄 Stability"])

    # -------------------------------
    # TAB 1: DRIVER STATS
    # -------------------------------
    with tab1:
        st.subheader("Driver Performance")

        def highlight_driver(row):
            if row["total_working_days"] > THRESHOLD:
                return ["background-color: #ff4d4d"] * len(row)
            return [""] * len(row)

        st.dataframe(
            driver_stats.style.apply(highlight_driver, axis=1),
            use_container_width=True
        )

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Total Drivers", driver_stats["Driver Name"].nunique())

        with col2:
            st.metric(
                "High Load Drivers",
                (driver_stats["total_working_days"] > THRESHOLD).sum()
            )

    # -------------------------------
    # TAB 2: VEHICLE USAGE
    # -------------------------------
    with tab2:
        st.subheader("Vehicle Running Duration (Months)")

        st.dataframe(
            vehicle_run.sort_values(by="running_months", ascending=False),
            use_container_width=True
        )

        st.subheader("Top 5 Most Used Vehicles")

        st.dataframe(
            vehicle_run.sort_values(by="running_months", ascending=False).head(5),
            use_container_width=True
        )

    # -------------------------------
    # TAB 3: DRIVER CHANGES
    # -------------------------------
    with tab3:
        st.subheader("Driver Changes per Vehicle")

        st.dataframe(
            driver_changes.sort_values(by="driver_changes"),
            use_container_width=True
        )

        st.subheader("🏆 Most Stable Truck")

        st.success(
            f"Vehicle: {least_change_truck['Vehicle No']} | "
            f"Driver Changes: {least_change_truck['driver_changes']}"
        )

        st.subheader("⚠️ High Change Vehicles")

        high_change = driver_changes[driver_changes["driver_changes"] > 5]

        st.dataframe(high_change, use_container_width=True)

    # -------------------------------
    # RAW DATA (DEBUG)
    # -------------------------------
    with st.expander("🔍 View Raw Data"):
        st.dataframe(df, use_container_width=True)

else:
    st.info("Please upload your Excel file to proceed.")
    
