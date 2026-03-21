import streamlit as st

st.title("Debug Mode")

try:
    from ai_helper import smart_query, fleet_summary
    st.success("ai_helper loaded ✅")
except Exception as e:
    st.error(f"ai_helper error: {e}")

try:
    from driver_helper import process_driver_file, driver_summary, driver_query
    st.success("driver_helper loaded ✅")
except Exception as e:
    st.error(f"driver_helper error: {e}")
