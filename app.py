import streamlit as st
from ai_helper import process_excel, fleet_summary, compare_files, generate_insights

st.set_page_config(page_title="Fleet AI", layout="wide")

st.title("🚛 Fleet AI Intelligence System")

files = st.file_uploader(
    "Upload Excel files",
    type=["xlsx"],
    accept_multiple_files=True
)

if files:

    dataframes = []

    for file in files:
        df = process_excel(file)

        if df is None:
            st.error("❌ 'Trip' column not found in file")
        else:
            dataframes.append(df)

    # SINGLE FILE ANALYSIS
    if len(dataframes) == 1:
        df = dataframes[0]

        st.subheader("📊 Fleet Summary")

        summary = fleet_summary(df)

        st.metric("Total Vehicles", summary["total_vehicles"])
        st.metric("Total Trips", summary["total_trips"])
        st.metric("Idle Vehicles", summary["total_idle"])
        st.metric("Avg Trips", summary["avg_trips"])
        st.metric("Efficiency", summary["efficiency"])

        st.subheader("🤖 Insights")

        insights = generate_insights(summary)

        st.text(insights)

    # MULTIPLE FILE COMPARISON
    elif len(dataframes) >= 2:
        st.subheader("📊 Comparison")

        result = compare_files(dataframes[0], dataframes[1])

        st.write("File 1 Summary:", result["file1"])
        st.write("File 2 Summary:", result["file2"])

        st.subheader("🤖 Insights")

        insights = generate_insights(result["file1"])

        st.text(insights)

else:
    st.info("Upload Excel files to start")
