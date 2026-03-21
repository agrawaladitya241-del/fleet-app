import streamlit as st
import pandas as pd

st.set_page_config(page_title="Fleet & Driver Dashboard", layout="wide")

st.title("🚛 Fleet & Driver Dashboard")

# SAFE IMPORTS
try:
    from ai_helper import smart_query, fleet_summary
    from driver_helper import process_driver_file, driver_summary, driver_query
except Exception as e:
    st.error(f"Import error: {e}")
    st.stop()

tab1, tab2 = st.tabs(["Fleet", "Driver"])

# ================= FLEET =================
with tab1:

    files = st.file_uploader(
        "Upload Fleet Files",
        type=["xlsx"],
        accept_multiple_files=True,
        key="fleet"
    )

    if files:
        try:
            summary = fleet_summary(files)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Vehicles", summary["total_vehicles"])
            col2.metric("Trips", summary["total_trips"])
            col3.metric("Idle", summary["total_idle"])
            col4.metric("Efficiency", summary["efficiency"])

            st.markdown("---")

            query = st.text_input("Ask Fleet", key="fleet_q")

            if query:
                st.success(smart_query(query, files))

            if summary["vehicle_data"]:
                df = pd.DataFrame(summary["vehicle_data"]).T
                st.bar_chart(df)
            else:
                st.warning("No vehicle data found")

        except Exception as e:
            st.error(f"Fleet Error: {e}")

    else:
        st.info("Upload fleet files")


# ================= DRIVER =================
with tab2:

    file = st.file_uploader(
        "Upload Driver File",
        type=["xlsx"],
        key="driver"
    )

    if file:
        try:
            df = process_driver_file(file)

            if df.empty:
                st.warning("Driver columns not detected properly")
            else:
                st.subheader("Driver Summary")
                stats = driver_summary(df)
                st.dataframe(stats)

                st.markdown("---")

                query = st.text_input("Ask Driver", key="driver_q")

                if query:
                    st.success(driver_query(query, df))

        except Exception as e:
            st.error(f"Driver Error: {e}")

    else:
        st.info("Upload driver file")
