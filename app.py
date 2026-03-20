import streamlit as st
from driver_helper import process_driver_file, driver_summary, driver_query

st.set_page_config(page_title="Fleet Dashboard", layout="wide")

st.title("🚛 Fleet & Driver Dashboard")

# -------------------------------
# FILE UPLOAD
# -------------------------------
uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])

if uploaded_file is not None:

    df = process_driver_file(uploaded_file)

    # -------------------------------
    # DRIVER SUMMARY (YOUR ORIGINAL LOGIC)
    # -------------------------------
    result = driver_summary(df)

    # -------------------------------
    # DISPLAY
    # -------------------------------
    tab1, tab2, tab3 = st.tabs(["📊 Driver Stats", "🔄 Changes", "🤖 Query"])

    # -------------------------------
    # TAB 1: DRIVER STATS
    # -------------------------------
    with tab1:
        st.subheader("Driver Stats")
        st.dataframe(result["driver_stats"], use_container_width=True)

    # -------------------------------
    # TAB 2: CHANGES
    # -------------------------------
    with tab2:
        st.subheader("Driver Changes")
        st.dataframe(result["driver_changes"], use_container_width=True)

        st.subheader("Vehicle Driver Changes")
        st.dataframe(result["vehicle_changes"], use_container_width=True)

    # -------------------------------
    # TAB 3: SMART QUERY
    # -------------------------------
    with tab3:
        user_input = st.text_input("Ask about driver")

        if user_input:
            response = driver_query(user_input, df)
            st.text(response)

    # -------------------------------
    # RAW DATA
    # -------------------------------
    with st.expander("🔍 Raw Data"):
        st.dataframe(df)

else:
    st.info("Upload your Excel file to begin.")
