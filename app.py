import streamlit as st
from ai_helper import fleet_summary, compare_files, generate_insights

st.title("🚚 Fleet AI Intelligence System")

files = st.file_uploader("Upload Excel files", type=["xlsx"], accept_multiple_files=True)

if files:

    summary = fleet_summary(files)

    st.metric("Total Trips", summary["total_trips"])
    st.metric("Total Idle", summary["total_idle"])

    st.subheader("🧠 AI Insights")
    st.success(generate_insights(summary))

    if len(files) >= 2:
        st.subheader("📊 Comparison")

        result = compare_files(files)

        st.write("Improved Trucks:")
        for v, diff in result["improved"]:
            st.write(f"{v} ↑ {diff}")

        st.write("Declined Trucks:")
        for v, diff in result["declined"]:
            st.write(f"{v} ↓ {diff}")
