import streamlit as st
import pandas as pd
from ai_helper import smart_query, fleet_summary

st.set_page_config(page_title="Fleet AI", layout="wide")

st.title("🚚 Fleet Intelligence Dashboard")

# Upload multiple files
uploaded_files = st.file_uploader(
    "Upload one or more Excel files",
    type=["xlsx"],
    accept_multiple_files=True
)

if uploaded_files:

    # 🔥 Process data
    summary = fleet_summary(uploaded_files)
    data = summary["vehicle_data"]

    # ================= KPI =================
    st.subheader("📊 Fleet Summary")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Vehicles", summary["total_vehicles"])
    col2.metric("Total Trips", summary["total_trips"])
    col3.metric("Total Idle", summary["total_idle"])
    col4.metric("Efficiency", summary["efficiency"])

    st.markdown("---")

    # ================= QUERY =================
    st.subheader("💬 Ask in Natural Language")

    query = st.text_input("Ask anything about fleet (e.g. total trips, best trucks, OD02BC1810)")

    if query:
        answer = smart_query(query, uploaded_files)
        st.success(answer)

    st.markdown("---")

    # ================= DATAFRAME =================
    st.subheader("📋 Vehicle Data")

    df = pd.DataFrame([
        {"Vehicle": v, "Trips": d["trips"], "Idle": d["idle"]}
        for v, d in data.items()
    ])

    df = df.sort_values(by="Trips", ascending=False)

    st.dataframe(df, use_container_width=True)

    st.markdown("---")

    # ================= GRAPH =================
    st.subheader("📊 Fleet Performance Graph")

    chart_df = df.set_index("Vehicle")

    st.bar_chart(chart_df[["Trips", "Idle"]])

    st.markdown("---")

    # ================= TOP / WORST =================
    st.subheader("🏆 Performance Insights")

    col1, col2 = st.columns(2)

    # Top 5
    top_5 = df.head(5)
    col1.markdown("### 🔝 Top 5 Trucks")
    col1.dataframe(top_5, use_container_width=True)

    # Worst 5
    worst_5 = df.tail(5)
    col2.markdown("### ⚠️ Worst 5 Trucks")
    col2.dataframe(worst_5, use_container_width=True)

else:
    st.info("Upload Excel files to start")
