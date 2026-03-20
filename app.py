import streamlit as st
import pandas as pd

# Fleet module
from ai_helper import smart_query, fleet_summary

# Driver module
from driver_helper import process_driver_file, driver_summary, driver_query

st.set_page_config(page_title="Fleet AI", layout="wide")

st.title("🚚 Fleet Intelligence System")

# ================= TABS =================
tab1, tab2 = st.tabs(["🚛 Fleet Dashboard", "👨‍✈️ Driver Analytics"])

# ================= TAB 1 =================
with tab1:

    uploaded_files = st.file_uploader(
        "Upload Fleet Excel files",
        type=["xlsx"],
        accept_multiple_files=True
    )

    if uploaded_files:

        summary = fleet_summary(uploaded_files)
        data = summary["vehicle_data"]

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Vehicles", summary["total_vehicles"])
        col2.metric("Trips", summary["total_trips"])
        col3.metric("Idle", summary["total_idle"])
        col4.metric("Efficiency", summary["efficiency"])

        st.markdown("---")

        st.subheader("💬 Ask About Fleet")

        query = st.text_input("Ask anything about fleet")

        if query:
            st.success(smart_query(query, uploaded_files))

        st.markdown("---")

        df = pd.DataFrame([
            {"Vehicle": v, **d}
            for v, d in data.items()
        ])

        st.dataframe(df)

    else:
        st.info("Upload fleet files")

# ================= TAB 2 =================
with tab2:

    driver_file = st.file_uploader(
        "Upload Driver Assignment Excel",
        type=["xlsx"]
    )

    if driver_file:

        df = process_driver_file(driver_file)
        result = driver_summary(df)

        st.subheader("📊 Driver Performance")
        st.dataframe(result["driver_stats"])

        st.markdown("---")

        st.subheader("💬 Ask About Drivers")

        d_query = st.text_input("Ask (e.g. total working days of Rahul)")

        if d_query:
            st.success(driver_query(d_query, df))

        st.markdown("---")

        col1, col2 = st.columns(2)

        col1.subheader("🔄 Drivers with Most Vehicle Changes")
        col1.dataframe(result["driver_changes"].head(10))

        col2.subheader("🚛 Vehicles with Most Driver Changes")
        col2.dataframe(result["vehicle_changes"].head(10))

    else:
        st.info("Upload driver file")
