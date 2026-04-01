# ai_helper.py

import re
import pandas as pd


# ================================
# FIND DATE COLUMNS (like 01, 02, 31)
# ================================
def get_date_columns(df):
    date_cols = []
    for col in df.columns:
        col_str = str(col)
        if re.match(r'^\d{1,2}$', col_str):  # columns like 1, 2, 31
            date_cols.append(col)
    return sorted(date_cols, key=lambda x: int(x))


# ================================
# INTENT PARSER (ADVANCED)
# ================================
def parse_query(query: str):
    query = query.lower()

    # detect "last N days"
    days_match = re.search(r'last (\d+)', query)
    days = int(days_match.group(1)) if days_match else None

    if "dp" in query or "delay" in query:
        if "most" in query or "top" in query:
            return {"intent": "top_dp_days", "days": days or 3}

        return {"intent": "delayed_trucks"}

    return {"intent": "unknown"}


# ================================
# QUERY ENGINE (SMART)
# ================================
def run_query(intent_data, df):

    intent = intent_data["intent"]

    try:
        # 🔥 TOP DP IN LAST N DAYS
        if intent == "top_dp_days":

            date_cols = get_date_columns(df)

            if not date_cols:
                return "❌ No date columns found"

            n_days = intent_data.get("days", 3)
            last_cols = date_cols[-n_days:]

            df_copy = df.copy()

            def count_dp(row):
                return sum(1 for col in last_cols if "DP" in str(row[col]).upper())

            df_copy["DP_Count"] = df_copy.apply(count_dp, axis=1)

            return df_copy.sort_values(by="DP_Count", ascending=False).head(10)

        return "❌ Query not understood"

    except Exception as e:
        return f"Error: {e}"


# ================================
# INSIGHTS ENGINE
# ================================
def generate_insights(df):

    insights = []

    try:
        date_cols = get_date_columns(df)

        if len(date_cols) >= 3:
            last_cols = date_cols[-3:]

            total_dp = 0

            for col in last_cols:
                total_dp += df[col].astype(str).str.contains("DP", na=False).sum()

            if total_dp > 10:
                insights.append("🚨 High delays in last 3 days")

    except:
        insights.append("⚠️ Could not analyze date-wise trends")

    return insights
