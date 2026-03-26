import sqlite3
import pandas as pd

DB_NAME = "fleet.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


# ================= FLEET TABLE =================
def save_fleet_data(data, date):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fleet (
            date TEXT,
            vehicle TEXT,
            trips INTEGER,
            idle INTEGER
        )
    """)

    for v, d in data.items():
        cursor.execute(
            "INSERT INTO fleet VALUES (?, ?, ?, ?)",
            (date, v, d["trips"], d["idle"])
        )

    conn.commit()
    conn.close()


# ================= DRIVER TABLE =================
def save_driver_data(df):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS driver (
            driver TEXT,
            vehicle TEXT,
            assigned TEXT,
            removed TEXT
        )
    """)

    for _, row in df.iterrows():
        cursor.execute(
            "INSERT INTO driver VALUES (?, ?, ?, ?)",
            (
                row["driver"],
                row["vehicle"],
                str(row["assigned"]),
                str(row["removed"])
            )
        )

    conn.commit()
    conn.close()


# ================= MONTHLY SUMMARY =================
def get_monthly_fleet():

    conn = get_connection()

    df = pd.read_sql("SELECT * FROM fleet", conn)

    conn.close()

    if df.empty:
        return pd.DataFrame()

    summary = df.groupby("vehicle").agg(
        total_trips=("trips", "sum"),
        total_idle=("idle", "sum")
    ).reset_index()

    return summary.sort_values(by="total_trips", ascending=False)
