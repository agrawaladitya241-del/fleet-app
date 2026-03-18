import streamlit as st
import pandas as pd
from ai_helper import ask_ai, fleet_summary, get_top_worst

st.set_page_config(page_title="Fleet Dashboard", layout="wide")

# HEADER
st.markdown("## 🚚 Fleet Performance Dashboard")
st.markdown("---")

# FILE UPLOAD
uploaded_file = st.file_uploader("📂 Upload Daily Fleet Report", type=["xlsx"])

if uploaded_file:

    summary = fleet_summary(uploaded_file)

    # KPI CARDS
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Vehicles", summary["total_vehicles"])
    col2.metric("Total Trips", summary["total_trips"])
    col3.metric("Idle Days", summary["total_idle"])
    col4.metric("Efficiency", summary["efficiency"])

    st.markdown("---")

    # AI QUERY
    st.subheader("🤖 Vehicle Query")

    query = st.text_input("Ask about any vehicle")

    if query:
        answer = ask_ai(query, uploaded_file)
        st.success(answer)

    st.markdown("---")

    # TOP & WORST
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🏆 Top Trucks")
        top, worst = get_top_worst(uploaded_file)
        for v, stats in top:
            st.write(f"{v} → Trips: {stats['trips']}")

    with col2:
        st.subheader("🐢 Underperforming Trucks")
        for v, stats in worst:
            st.write(f"{v} → Trips: {stats['trips']}")

    st.markdown("---")

    # GRAPH
    st.subheader("📈 Trips vs Idle")

    vehicles = []
    trips = []
    idle = []

    for v, stats in summary["vehicle_data"].items():
        vehicles.append(v)
        trips.append(stats["trips"])
        idle.append(stats["idle"])

    df = pd.DataFrame({
        "Vehicle": vehicles,
        "Trips": trips,
        "Idle": idle
    })

    st.bar_chart(df.set_index("Vehicle"))

else:
    st.info("Upload your daily Excel file to start")