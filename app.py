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

        if df is not None:
            dataframes.append(df)

    # SINGLE FILE
    if len(dataframes) == 1:
        df = dataframes[0]

        st.subheader("📊 Fleet Summary")

        summary = fleet_summary(df)

        st.write(summary)

        st.subheader("🤖 AI Insights")

        insights = generate_insights(summary)

        st.write(insights)

    # MULTIPLE FILES
    elif len(dataframes) >= 2:
        st.subheader("📊 Comparison")

        result = compare_files(dataframes[0], dataframes[1])

        st.write(result)

        st.subheader("🤖 AI Insights")

        insights = generate_insights(result["file1"])

        st.write(insights)

else:
    st.info("Upload Excel files to start")
