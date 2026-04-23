# Fleet Intelligence Dashboard

A month-aware Streamlit dashboard for tracking daily operations of a flatbed trailer fleet (TSK/TSM · Angul depot).

## What it does

Upload a multi-sheet Excel report (one sheet per month) and the app produces:

- **KPI snapshot** — active trips today, drivers home, waiting/idle vehicles, fleet utilization %
- **Daily status trend** — stacked bar chart of every vehicle's status across the month
- **Utilization trend** — productive-day percentage over time
- **Vehicle performance** — top performers, flagged vehicles needing follow-up, full sortable table
- **Driver performance** — aggregated by driver
- **Raw daily log** — filterable, downloadable as CSV

## Status taxonomy

The app classifies each daily cell into one of these operational states:

| Code | Meaning |
|---|---|
| DH   | Driver Home |
| DP   | Driver Problem |
| LP   | Loading Point |
| PARK | Parking |
| WAIT | Waiting (e.g. "Wait For Load", "WT FOR DO") |
| TNST | In Transit |
| UL   | Unloading Point |
| MT   | Empty Truck Movement |
| TRIP | Active laden trip |
| NO_DATA | No activity logged |

## Local setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the URL Streamlit prints (usually `http://localhost:8501`).

## Deploy to Streamlit Community Cloud (free, no login)

1. Push this repository to GitHub (public repo).
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. Click **New app**, select this repo, pick `app.py` as the entry point.
4. Click **Deploy**. You'll get a public URL like `https://your-app.streamlit.app` that anyone can use — no login required.
5. Every time you push to the main branch, the app redeploys automatically.

## Expected Excel file format

- One sheet per month, with sheet names starting with the month (e.g. `February`, `March`, `APRIL`).
- Each sheet's first row is the header:
  - Meta columns: `Sl No`, `Vehicle No`, `Model`, `Driver Name`, `Cont No`
  - Date columns: one per day (either real date cells or text like `01-Feb`, `03-Aprl`)
  - Optional `PLANT IN/OUT` columns between date columns
- One row per vehicle; each date cell contains a status description (e.g. `"UL Jamshedpur"`, `"MT CKL (DH)"`, `"Loading Point Wait For Load"`).

## Project structure

```
.
├── app.py           # Streamlit UI
├── data_loader.py   # Excel parsing: multi-sheet, messy headers, long-format output
├── analytics.py     # Status classification + summary tables
├── requirements.txt
└── README.md
```
