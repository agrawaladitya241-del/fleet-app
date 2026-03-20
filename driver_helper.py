import streamlit as st
import pandas as pd

st.set_page_config(page_title="Driver Performance", layout="wide")

st.title("📊 Driver Performance Dashboard")

# -------------------------------
# SAMPLE DATA (Replace with your file later)
# -------------------------------
data = [
    {"driver": "Amit", "start_date": "2024-04-01", "end_date": "2024-04-03"},
    {"driver": "Amit", "start_date": "2024-04-10", "end_date": "2024-04-12"},
    {"driver": "Rahul", "start_date": "2024-04-05", "end_date": "2024-04-14"},
    {"driver": "Rahul", "start_date": "2024-04-20", "end_date": "2024-04-22"},
    {"driver": "Vikram", "start_date": "2024-04-07", "end_date": "2024-04-07"},
]

df = pd.DataFrame(data)

# -------------------------------
# CLEANING
# -------------------------------
df["start_date"] = pd.to_datetime(df["start_date"])
df["end_date"] = pd.to_datetime(df["end_date"])

# -------------------------------
# CALCULATE LEAVE DAYS
# -------------------------------
df["leave_days"] = (df["end_date"] - df["start_date"]).dt.days + 1

# -------------------------------
# DRIVER TOTAL LEAVES
# -------------------------------
driver_stats = df.groupby("driver")["leave_days"].sum().reset_index()

driver_stats.rename(columns={"leave_days": "total_leave_days"}, inplace=True)

# -------------------------------
# FLAG HIGH LEAVE DRIVERS
# -------------------------------
THRESHOLD = 5  # you can change this

driver_stats["status"] = driver_stats["total_leave_days"].apply(
    lambda x: "⚠️ High Leave" if x > THRESHOLD else "✅ Normal"
)

# -------------------------------
# DISPLAY RAW DATA
# -------------------------------
st.subheader("📄 Leave Records")
st.dataframe(df, use_container_width=True)

# -------------------------------
# HIGHLIGHT FUNCTION
# -------------------------------
def highlight_rows(row):
    if row["total_leave_days"] > THRESHOLD:
        return ["background-color: #ff4d4d"] * len(row)
    return [""] * len(row)

# -------------------------------
# DISPLAY DRIVER STATS
# -------------------------------
st.subheader("📊 Driver Summary")

styled_df = driver_stats.style.apply(highlight_rows, axis=1)

st.dataframe(styled_df, use_container_width=True)

# -------------------------------
# METRICS
# -------------------------------
col1, col2 = st.columns(2)

with col1:
    st.metric("Total Drivers", driver_stats["driver"].nunique())

with col2:
    st.metric("High Leave Drivers", (driver_stats["total_leave_days"] > THRESHOLD).sum())

# -------------------------------
# DEBUG (SAFE)
# -------------------------------
st.subheader("🔍 Debug Info")
st.write("Columns:", df.columns.tolist())
st.write("Driver Stats Columns:", driver_stats.columns.tolist())
