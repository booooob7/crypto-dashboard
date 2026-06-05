# Crypto Dashboard — Deployment Handoff (for Codex)

This is a complete, self-contained briefing. Read this one file and you have everything
needed to take the project from "code complete + reviewed" to "live public URL".

**Project root:** `/Users/chiutzufu/Desktop/Claude/crypto-dashboard`
**Status:** Code complete. 3 rounds of Codex review passed. 22 tests passing. HEAD = `05d1fed`.
**Goal of handoff:** Deploy to a public URL (Streamlit Cloud) with a live data pipeline.

---

## 1. What This Project Is

A university assignment: *"Deployment of a Dashboard with its own Data Pipeline."*
A cryptocurrency market dashboard with an automated ETL pipeline.

**Grading (11 pts total):**
- Data Pipeline/ETL — 0–4 (complexity & creativity)
- Visualization — 0–3 (complexity & creativity)
- Data refresh mechanism — 0–2 (complexity)
- Communicate (exec summary + presentation) — 0–2

**Hard constraints:**
- No BI tools (Tableau/Power BI). ✅ We use Streamlit + Plotly.
- Must be deployed to a **public URL** — localhost is NOT allowed. ← this is the whole point of deployment.
- One-page A4 executive summary required (already written: `docs/executive-summary.md`).
- In-class demo with the live URL.

---

## 2. Architecture

```
[Public APIs]            [ETL Layer]              [Storage]          [Presentation]
CoinGecko       ──┐
Alternative.me  ──┼──→  GitHub Actions      ──→  Supabase       ──→  Streamlit Cloud
Blockchain.com  ──┘      cron */15 * * * *        PostgreSQL          (public URL)
```

- **ETL**: GitHub Actions runs `python -m etl.run_etl` every 15 min. Writes to Supabase using the **service role key**.
- **Storage**: Supabase free-tier PostgreSQL. 3 tables: `prices`, `fear_greed`, `onchain`.
- **Dashboard**: Streamlit Cloud runs `dashboard/app.py`, reads from Supabase using the **anon key**. Renders Plotly charts.
- **Refresh**: cron every 15 min + manual refresh button in the dashboard sidebar.

**Tech stack:** Python 3.11, Streamlit, Plotly, supabase-py, requests, tenacity, pytest.

---

## 3. Data Sources (all free, no key required; CoinGecko key optional)

| Source | Data | Auth |
|--------|------|------|
| CoinGecko `/coins/markets`, `/coins/{id}/market_chart` | Top-10 price, market cap, volume, 24h/7d change, 90d history | None (optional Demo key) |
| Alternative.me `/fng/` | Fear & Greed Index (current + history) | None |
| Blockchain.com `/charts/n-unique-addresses` | On-chain active addresses | None |

---

## 4. File Map

```
crypto-dashboard/
├── .github/workflows/etl.yml      # GitHub Actions cron (every 15 min)
├── sql/schema.sql                 # 3 CREATE TABLE statements — run in Supabase SQL editor
├── etl/
│   ├── db.py                      # Supabase client (SERVICE ROLE), upsert helpers, staleness checks
│   ├── fetch_prices.py            # CoinGecko top-10 (CRITICAL source, validates + retries)
│   ├── fetch_fear_greed.py        # Alternative.me (enrichment)
│   ├── fetch_onchain.py           # Blockchain.com (enrichment)
│   ├── run_etl.py                 # ETL entry point — `python -m etl.run_etl`
│   └── seed_historical.py         # ONE-TIME seed — `python -m etl.seed_historical`
├── dashboard/
│   ├── queries.py                 # Supabase reads (ANON key, st.cache_data ttl=300)
│   ├── charts.py                  # Plotly builders (Chinese labels)
│   └── app.py                     # Streamlit entry point — `streamlit run dashboard/app.py`
├── tools/preview_app.py           # THROWAWAY local preview (synthetic data) — NOT for deployment
├── docs/executive-summary.md      # Assignment deliverable
├── requirements.txt               # Pinned major/minor ranges
└── .streamlit/secrets.toml.example
```

UI is localized to Traditional Chinese (display strings + chart labels only — no data keys/columns changed).

---

## 5. Database Schema (`sql/schema.sql`)

Three tables. Key design points reviewers already validated:

- `prices`: `UNIQUE (coin_id, bucket_time)` — ETL upserts with `on_conflict="coin_id,bucket_time"`. `bucket_time` = 15-min-aligned UTC.
- `fear_greed`: `UNIQUE (recorded_at)` — `on_conflict="recorded_at"`.
- `onchain`: `UNIQUE (metric, recorded_at)` — `on_conflict="metric,recorded_at"`.

All timestamps UTC. RLS is intentionally **disabled** for assignment simplicity (documented in schema.sql header; anon read-policy SQL is included there if you ever enable RLS).

---

## 6. Secrets & Security (CRITICAL — do not get this wrong)

Two different Supabase keys, never mixed:

| Where | Secret name | Key | Purpose |
|-------|-------------|-----|---------|
| GitHub Actions repo secrets | `SUPABASE_URL` | project URL | — |
| GitHub Actions repo secrets | `SUPABASE_SERVICE_ROLE_KEY` | **service_role** | ETL writes (bypasses RLS) |
| GitHub Actions repo secrets | `COINGECKO_API_KEY` | demo key | optional, higher rate limit |
| Streamlit Cloud secrets | `SUPABASE_URL` | project URL | — |
| Streamlit Cloud secrets | `SUPABASE_ANON_KEY` | **anon/public** | dashboard reads only |

> ⚠️ The **service role key must NEVER** appear in Streamlit code, Streamlit secrets, the browser, or any committed file. `.gitignore` already excludes `.streamlit/secrets.toml` and `.env`.

Code reads these via `os.environ[...]` (ETL) and `st.secrets[...]` (dashboard). Confirmed by review: service role only in `etl/db.py` + workflow yml; anon only in `dashboard/queries.py`.

---

## 7. Deployment Steps (what you, Codex, will guide the user through)

The user must perform all web-UI/account actions themselves (you cannot log into their
Supabase/GitHub/Streamlit accounts). You CAN run local scripts once they paste real keys,
and you CAN use `gh` CLI for the GitHub parts if available.

### Step A — Supabase (user, web UI)
1. supabase.com → New Project (pick a nearby region, save the DB password).
2. SQL Editor → paste entire `sql/schema.sql` → Run. Verify 3 tables in Table Editor.
3. Project Settings → API → copy: **Project URL**, **anon public key**, **service_role secret key**.

### Step B — Seed + first ETL (you can run locally with the user's keys)
```bash
cd /Users/chiutzufu/Desktop/Claude/crypto-dashboard
export SUPABASE_URL="https://<ref>.supabase.co"
export SUPABASE_SERVICE_ROLE_KEY="<service-role-key>"
export COINGECKO_API_KEY="<optional-demo-key>"   # optional

.venv/bin/python -m etl.seed_historical   # ~90d history for live top-10, F&G, on-chain
.venv/bin/python -m etl.run_etl           # one live snapshot
```
Verify rows land in Supabase `prices` / `fear_greed` / `onchain`.

> Note on `.venv`: it was created with system-site-packages and emits harmless pandas/numpy/pyarrow
> ABI warnings locally. Not a blocker — cloud installs from the clean pinned `requirements.txt`.
> If you prefer a clean run: `python -m venv /tmp/cd && /tmp/cd/bin/pip install -r requirements.txt`.

### Step C — GitHub (user, or you via `gh`)
1. Create repo `crypto-dashboard`.
2. `git remote add origin … && git branch -M main && git push -u origin main`
   (Repo is already a git repo at HEAD `05d1fed` — just add remote + push.)
3. Repo → Settings → Secrets and variables → Actions → add `SUPABASE_URL`,
   `SUPABASE_SERVICE_ROLE_KEY`, and optionally `COINGECKO_API_KEY`.
4. Actions tab → ETL Pipeline → Run workflow (manual trigger) → confirm green run.

### Step D — Streamlit Cloud (user, web UI)
1. share.streamlit.io → sign in with GitHub → New app.
2. Repo = `crypto-dashboard`, branch = `main`, main file path = `dashboard/app.py`.
3. App Settings → Secrets → paste:
   ```toml
   SUPABASE_URL = "https://<ref>.supabase.co"
   SUPABASE_ANON_KEY = "<anon-key>"
   ```
4. Deploy → get the public `*.streamlit.app` URL. This is the demo URL.

---

## 8. Smoke Test (before demo)

- [ ] Open the public Streamlit URL in incognito — all 4 sections render with real data:
      overview cards, price+volume chart (try 7D/30D/90D and the coin selector),
      Fear & Greed gauge + 30D trend, on-chain active addresses.
- [ ] GitHub Actions shows green runs appearing every ~15 min.
- [ ] Open the URL 5 min before the in-class demo (Streamlit free apps sleep when idle).

---

## 9. Known Risks (already documented, watch during demo window)

| Risk | Mitigation |
|------|-----------|
| GitHub Actions free minutes (~2,880 runs/mo vs 2,000 min cap) | keep each run < 45s; drop to */20 or */30 if needed |
| Streamlit Cloud app sleeps when idle | open URL 5 min before demo |
| Supabase free project pauses after 7 days idle | visit dashboard weekly; ensure awake before demo |
| Blockchain.com on-chain API flaky | it's enrichment-only; ETL logs a warning and continues |
| Top-10 membership shifts | `rank` stored at fetch time; seed uses live top-10 |

---

## 10. Review History (context — all resolved)

- **Review 2** (`docs/ai-review/crypto-dashboard-codex-review2.md`): 7 findings → all fixed (commit `990fdd7`), summary in `crypto-dashboard-claude-fixes2.md`.
- **Review 3** (`docs/ai-review/crypto-dashboard-codex-review3.md`): no blocking issues, verdict "可以進部署". One minor hardening fix applied (commit `05d1fed`).

`python -m pytest -q` → **22 passed**.

---

## 11. Commands Reference

```bash
# Tests
.venv/bin/python -m pytest -q

# Local dashboard against real Supabase (needs .streamlit/secrets.toml with URL + ANON key)
.venv/bin/streamlit run dashboard/app.py

# Local UI-only preview (synthetic data, no DB needed)
.venv/bin/streamlit run tools/preview_app.py

# ETL (needs SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY env vars)
.venv/bin/python -m etl.seed_historical
.venv/bin/python -m etl.run_etl
```
