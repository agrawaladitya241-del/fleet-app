# ai_helper.py

import re
import pandas as pd
from datetime import datetime


# ================================
# SMART DATE COLUMN DETECTOR (FIXED)
# ================================
def is_date_like(col):
    col_str = str(col).strip()

    # Case 1: pure numbers (1,2,3)
    if re.match(r'^\d{1,2}$', col_str):
        return True

    # Case 2: formats like 01-03, 01/03, 01.03
    if re.match(r'^\d{1,2}[-/\.]\d{1,2}$', col_str):
        return True

    # Case 3: try parsing as date
    try:
        pd.to_datetime(col_str, dayfirst=True)
        return True
    except:
        return False


def get_date_columns(df):
    date_cols = []

    for col in df.columns:
        if is_date_like(col):
            date_cols.append(col)

    # Sort columns properly
    try:
        date_cols = sorted(date_cols, key=lambda x: pd.to_datetime(str(x), dayfirst=True))
    except:
        pass

    return date_cols


# ================================
# INTENT PARSER
# ================================
def parse_query(query: str):
    query = query.lower()

    days_match = re.search(r'last (\d+)', query)
    days = int(days_match.group(1)) if days_match else 3

    if "dp" in query or "delay" in query:
        if "most" in query or "top" in query:
            return {"intent": "top_dp_days", "days": days}

    return {"intent": "unknown"}


# ================================
# QUERY ENGINE
# ================================
def run_query(intent_data, df):

    intent = intent_data["intent"]

    try:
        if intent == "top_dp_days":

            date_cols = get_date_columns(df)

            if not date_cols:
                return f"❌ No date columns found. Columns detected: {list(df.columns)}"

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
# INSIGHTS
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
        insights.append("⚠️ Could not analyze trends")

    return insights
