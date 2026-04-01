# ai_helper.py

import re


# ================================
# COLUMN FINDER
# ================================
def get_column(df, possible_names):
    for col in df.columns:
        for name in possible_names:
            if name.lower() in col.lower():
                return col
    return None


# ================================
# INTENT PARSER (UPGRADED)
# ================================
def parse_query(query: str):
    query = query.lower()

    # 🔥 NEW: DP ranking
    if "dp" in query or "delay" in query:
        if "most" in query or "top" in query:
            numbers = re.findall(r'\d+', query)
            top_n = int(numbers[0]) if numbers else 5
            return {"intent": "top_dp", "n": top_n}

        return {"intent": "delayed_trucks"}

    # Idle
    if "idle" in query and ("top" in query or "most" in query):
        numbers = re.findall(r'\d+', query)
        top_n = int(numbers[0]) if numbers else 5
        return {"intent": "top_idle", "n": top_n}

    # Active
    if "active" in query:
        return {"intent": "active_trucks"}

    return {"intent": "unknown"}


# ================================
# QUERY ENGINE (UPGRADED)
# ================================
def run_query(intent_data, df):
    intent = intent_data["intent"]

    dp_col = get_column(df, ["dp"])
    idle_col = get_column(df, ["idle"])
    status_col = get_column(df, ["status_type"])

    try:
        # 🔥 NEW: TOP DP VEHICLES
        if intent == "top_dp":
            if dp_col:
                n = intent_data.get("n", 5)
                return df.sort_values(by=dp_col, ascending=False).head(n)
            return "❌ DP column not found"

        # Delayed trucks
        if intent == "delayed_trucks":
            if status_col:
                return df[df[status_col] == "Delay"]
            return "❌ Status column not found"

        # Top idle
        if intent == "top_idle":
            if idle_col:
                n = intent_data.get("n", 5)
                return df.sort_values(by=idle_col, ascending=False).head(n)
            return "❌ Idle column not found"

        # Active
        if intent == "active_trucks":
            if status_col:
                return df[df[status_col] == "Active"]
            return "❌ Status column not found"

        return "❌ Query not understood"

    except Exception as e:
        return f"Error: {e}"


# ================================
# INSIGHTS ENGINE
# ================================
def generate_insights(df):
    insights = []

    dp_col = get_column(df, ["dp"])
    status_col = get_column(df, ["status_type"])

    try:
        if dp_col:
            high_dp = df[df[dp_col] > df[dp_col].mean()]
            if not high_dp.empty:
                insights.append(f"⚠️ {len(high_dp)} vehicles have high delays")

        if status_col:
            delays = df[df[status_col] == "Delay"]
            if len(delays) > 5:
                insights.append("🚨 High number of delayed trucks today")

    except:
        insights.append("⚠️ Insight generation failed")

    return insights
