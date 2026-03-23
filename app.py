import streamlit as st
import pandas as pd

from ai_helper import smart_query, fleet_summary, compare_files

st.set_page_config(page_title="Fleet Dashboard", layout="wide")

st.title("🚚 Fleet Dashboard")

files = st.file_uploader("Upload Excel files", type=["xlsx"], accept_multiple_files=True)

if files:

    st.session_state["files"] = files

    summary = fleet_summary(files)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Vehicles", summary["total_vehicles"])
    col2.metric("Trips", summary["total_trips"])
    col3.metric("Idle", summary["total_idle"])
    col4.metric("Efficiency", summary["efficiency"])

    st.markdown("---")

    # 🔥 SEARCH (WORKING)
    st.subheader("🔍 Search")

    query = st.text_input("Ask anything")

    if query:
        st.success(smart_query(query, st.session_state["files"]))

    st.markdown("---")

    df = pd.DataFrame(summary["vehicle_data"]).T
    st.bar_chart(df)

    st.markdown("---")

    # 🔥 COMPARISON
    st.subheader("📊 Compare Two Files")

    f1 = st.file_uploader("Previous File", type=["xlsx"], key="f1")
    f2 = st.file_uploader("Current File", type=["xlsx"], key="f2")

    if f1 and f2:
        comp = compare_files(f1, f2)
        st.dataframe(pd.DataFrame(comp).T)

else:
    st.info("Upload files to start")
