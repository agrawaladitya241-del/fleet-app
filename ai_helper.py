# ai_helper.py

import re

# ================================
# SAFE COLUMN FINDER (prevents crashes)
# ================================
def get_column(df, possible_names):
    for col in df.columns:
        for name in possible_names:
            if name.lower() in col.lower():
                return col
    return None


# ================================
# INTENT PARSER
# ================================
def parse_query(query: str):
    query = query.lower()

    if "delay" in query or "delayed" in query:
        return {"intent": "delayed_trucks"}

    if "idle" in query and "top" in query:
        numbers = re.findall(r'\d+', query)
        top_n = int(numbers[0]) if numbers else 5
        return {"intent": "top_idle", "n": top_n}

    if "active" in query:
        return {"intent": "active_trucks"}

    return {"intent": "unknown"}


# ================================
# QUERY ENGINE
# ================================
def run_query(intent_data, df):
    intent = intent_data["intent"]

    remarks_col = get_column(df, ["remarks", "comment"])
    idle_col = get_column(df, ["idle"])
    trips_col = get_column(df, ["trip"])

    try:
        if intent == "delayed_trucks":
            if remarks_col:
                return df[df[remarks_col].astype(str).str.contains("DP", na=False)]
            return "❌ Remarks column not found"

        if intent == "top_idle":
            if idle_col:
                n = intent_data.get("n", 5)
                return df.sort_values(by=idle_col, ascending=False).head(n)
            return "❌ Idle column not found"

        if intent == "active_trucks":
            if trips_col:
                return df[df[trips_col] > 0]
            return "❌ Trips column not found"

        return "❌ Query not understood"

    except Exception as e:
        return f"Error: {e}"


# ================================
# INSIGHTS ENGINE
# ================================
def generate_insights(df):
    insights = []

    idle_col = get_column(df, ["idle"])
    remarks_col = get_column(df, ["remarks", "comment"])

    try:
        if idle_col:
            avg_idle = df[idle_col].mean()
            high_idle = df[df[idle_col] > avg_idle]

            if not high_idle.empty:
                insights.append(f"⚠️ {len(high_idle)} vehicles have above-average idle time")

        if remarks_col:
            delays = df[df[remarks_col].astype(str).str.contains("DP", na=False)]
            if len(delays) > 5:
                insights.append("🚨 High number of delayed trucks today")

    except:
        insights.append("⚠️ Insight generation partially failed")

    return insights
