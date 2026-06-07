# Executive Summary — Cryptocurrency Market Dashboard

**Assignment:** Deployment of a Dashboard with its own Data Pipeline
**Live App:** <https://crypto-dashboard-dm9wvnvtvq8pexhlkyqbyj.streamlit.app/>

---

## Overview

This project delivers a real-time cryptocurrency market dashboard backed by a fully automated ETL pipeline. Market data is collected from three public APIs, cleaned, and stored in a cloud PostgreSQL database every 15 minutes. A Streamlit web application reads from that database and renders interactive visualisations for end users.

---

## Architecture

```
[CoinGecko API]          ┐
[Alternative.me API]     ├─► GitHub Actions (cron) ─► ETL Script ─► Supabase PostgreSQL ─► Streamlit Cloud
[Blockchain.com API]     ┘
```

---

## Tech Stack

| Layer | Technology | Role |
|---|---|---|
| Orchestration | GitHub Actions (cron) | Triggers ETL every 15 minutes |
| Data Sources | CoinGecko, Alternative.me, Blockchain.com | Price, sentiment, on-chain data |
| ETL | Python (`requests`, `pandas`) | Fetch, clean, deduplicate, load |
| Database | Supabase PostgreSQL | Persistent storage (3 tables) |
| Dashboard | Streamlit + Plotly | Interactive web UI |
| Hosting | Streamlit Cloud | Public deployment |

---

## Data Pipeline (ETL)

Three independent API sources feed a single pipeline script executed by GitHub Actions:

- **CoinGecko** → `prices` table — 15-minute OHLCV snapshots; unique constraint on `(coin_id, bucket_time)` prevents duplicates.
- **Alternative.me** → `fear_greed` table — daily Fear & Greed Index score (0–100).
- **Blockchain.com** → `onchain` table — daily Bitcoin active addresses, transaction count, and estimated USD transfer volume.

Data cleaning includes type coercion, null filtering, and upsert logic so repeated runs are idempotent.

---

## Data Refresh Mechanism

| Mechanism | Trigger | Frequency |
|---|---|---|
| GitHub Actions cron | Automatic | Every 15 minutes, 24/7 |
| Dashboard refresh button | User-initiated | On demand (clears cached reads) |

The cron job is the primary data-ingestion path; the in-app button clears Streamlit's cached database reads so users can immediately view the latest data already written by the pipeline.

---

## Dashboard Visualisations

The Streamlit app provides four interactive sections:

1. **Market Overview Cards** — live price, 24 h change, and market cap for selected coins.
2. **Price History Chart** — Plotly line chart with per-coin selector and 7D / 30D / 90D time-range toggle.
3. **Fear & Greed Gauge** — current index rendered as a Plotly gauge plus a 30-day trend line.
4. **On-Chain Activity** — selectable Bitcoin network metrics for active addresses, daily transactions, and estimated USD transfer volume.

All charts are rendered with Plotly and support hover tooltips, vertical crosshair inspection, zoom, and pan.
