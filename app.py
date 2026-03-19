import streamlit as st
import pandas as pd
from ai_helper import smart_query, fleet_summary

st.set_page_config(page_title="Fleet AI", layout="wide")

st.title("🚚 Fleet Intelligence Dashboard")

# MULTIPLE FILE UPLOAD
uploaded_files = st.file_uploader("Upload one or more Excel files", type=["xlsx"], accept_multiple_files=True)

if uploaded_files:

    summary = fleet_summary(uploaded_files)

    # KPI
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Vehicles", summary["total_vehicles"])
    col2.metric("Trips", summary["total_trips"])
    col3.metric("Idle", summary["total_idle"])
    col4.metric("Efficiency", summary["efficiency"])

    st.markdown("---")

    # SMART QUERY
    st.subheader("💬 Ask in natural language")

    query = st.text_input("Ask anything about fleet")

    if query:
        answer = smart_query(query, uploaded_files)
        st.success(answer)

    st.markdown("---")

    # GRAPH
    st.subheader("📊 Fleet Graph")

    df = pd.DataFrame(summary["vehicle_data"]).T
    st.bar_chart(df)

else:
    st.info("Upload Excel files to start")
