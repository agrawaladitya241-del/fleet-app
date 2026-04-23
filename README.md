# Fleet Intelligence Dashboard

Multi-month operational dashboard for a flatbed trailer fleet (TSK/TSM · Angul depot).

## What it does

Upload the monthly Excel report and the app produces:

- **Overview** — Live KPIs (active trips, drivers home, idle/waiting, fleet utilization, accident vehicles) and a daily status trend chart
- **Vehicles** — Per-vehicle performance with manual vs computed trip counts, top performers, flagged vehicles needing follow-up, and a drill-down showing the exact DH/DP days for any vehicle
- **Drivers** — Aggregated metrics grouped by driver
- **Routes** — Route-level analysis (e.g. TSK-PDP, TSM-JSPR). Shows average plant dwell time per route and per-truck deviation so you can spot slow/fast trucks on the same route
- **Accident Vehicles** — Dedicated view of grounded vehicles with accident date ranges
- **Audit / Verify** — Search panel (Excel-Find equivalent) and status-by-status cell listing so you can cross-check every count against the source sheet
- **Raw Data** — Full daily log and parsed Plant In/Out log, both downloadable as CSV

## Status taxonomy

Each daily cell is classified into one of these operational states (precedence top-down):

| Code | Meaning |
|---|---|
| ACCIDENT | Vehicle grounded due to accident |
| SERVICE | Vehicle grounded for service/repair (clutch, tyre, engine, etc.) |
| DH | Driver Home |
| DP | Driver Problem |
| LP | Loading Point |
| PARK | Parking |
| WAIT | Waiting (Wait For Load / WT FOR DO etc.) |
| TNST | In Transit |
| UL | Unloading Point |
| MT | Empty Truck Movement |
| TRIP | Active laden trip |
| NO_DATA | Empty cell |

## Trip counting

A trip is defined as a cell starting with `TSK-`, `TSM-`, or `JSPL-` followed by a destination. This heuristic matches the human-entered Trip column in the Excel file with ~90% accuracy.

When a month sheet has a manual `Trip` column (like March), the app shows both counts side-by-side so you can verify. When it doesn't (like April), only the computed count is shown with a clear warning.

## Local setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy to Streamlit Community Cloud (free, no login)

1. Push this repo to GitHub (public).
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in with GitHub.
3. Click "New app" → pick this repo → `app.py` as the entry point → Deploy.
4. You'll get a public URL anyone can use.

Pushes to the main branch auto-redeploy within ~1 minute.

## Expected Excel format

- One sheet per month, name starting with the month (`February`, `March`, `APRIL`, etc.).
- Header columns: `Sl No`, `Vehicle No`, `Model`, `Driver Name`, `Cont No`, then one column per day of the month.
- Optional `PLANT IN/OUT` columns interleaved with date columns (contain IN/OUT timestamps or service notes).
- Optional `Trip` column at the end with the manual trip count per vehicle.
- Yellow-highlighted cells = recognized trip routes (e.g. `TSK-PDP`), used for route analysis.
- `ACCIDENT` / `Accidental Work` in cells = grounded vehicle.

Hidden rows and columns in the Excel file are read correctly — they're just hidden visually, not deleted.

## Project structure

```
.
├── app.py           # Streamlit UI (7 tabs)
├── data_loader.py   # Excel parsing (multi-sheet, messy headers, timestamp extraction)
├── analytics.py     # Status classification, trip counting, route extraction, accident detection
├── requirements.txt
└── README.md
```
