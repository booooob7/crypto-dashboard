"""
One-time intraday backfill.

Fills the recent window with HOURLY price history so the dashboard's short-range
(<= 7 day) view shows intraday detail across the whole window, not just the days
since the 15-minute ETL started running.

CoinGecko's /coins/{id}/market_chart returns hourly granularity automatically for
a `days` value between 2 and 90 (no `interval` param needed on the free/demo tier).

Run: python -m etl.seed_intraday
Requires: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in environment.
Optional: COINGECKO_API_KEY
"""
import logging
import time
import requests
from datetime import datetime, timezone
from tenacity import (
    retry, stop_after_attempt, wait_exponential, retry_if_exception_type,
)

from etl.db import get_client, upsert_prices
from etl.seed_historical import fetch_live_top10, _headers, COINGECKO_BASE

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

BACKFILL_DAYS = 7


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=10, max=60),
    retry=retry_if_exception_type(requests.RequestException),
    reraise=True,
)
def _fetch_market_chart(coin_id: str, days: int) -> dict:
    """Fetch hourly market_chart, backing off on 429/5xx rate-limit responses."""
    resp = requests.get(
        f"{COINGECKO_BASE}/coins/{coin_id}/market_chart",
        headers=_headers(),
        params={"vs_currency": "usd", "days": days},  # 2-90d → hourly automatically
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def seed_intraday(coin: dict, days: int = BACKFILL_DAYS) -> list[dict]:
    """Fetch hourly price history for one coin and return rows with real timestamps."""
    coin_id = coin["id"]
    log.info(f"  Backfilling {coin_id} ({days}d hourly)…")
    data = _fetch_market_chart(coin_id, days)

    fetched = datetime.now(timezone.utc).isoformat()
    prices   = {p[0]: p[1] for p in data["prices"]}
    volumes  = {p[0]: p[1] for p in data.get("total_volumes", [])}
    mkt_caps = {p[0]: p[1] for p in data.get("market_caps", [])}

    rows = []
    for ts_ms in prices:
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        # Align to the 15-min bucket grid so rows coexist with live ETL snapshots
        minute = (dt.minute // 15) * 15
        bucket = dt.replace(minute=minute, second=0, microsecond=0).isoformat()
        rows.append({
            "coin_id":     coin_id,
            "symbol":      coin["symbol"],
            "rank":        coin["rank"],
            "price_usd":   prices[ts_ms],
            "market_cap":  mkt_caps.get(ts_ms),
            "volume_24h":  volumes.get(ts_ms),
            "change_24h":  None,
            "change_7d":   None,
            "bucket_time": bucket,
            "fetched_at":  fetched,
        })
    return rows


def run() -> None:
    client = get_client()
    log.info("Resolving live top-10 by market cap…")
    top10 = fetch_live_top10()
    log.info(f"  Top-10: {', '.join(c['id'] for c in top10)}")

    for coin in top10:
        try:
            rows = seed_intraday(coin, days=BACKFILL_DAYS)
            upsert_prices(client, rows)
            log.info(f"  → {len(rows)} hourly rows upserted for {coin['id']}")
        except Exception as exc:
            log.error(f"  Failed to backfill {coin['id']}: {exc}")
        time.sleep(8)  # courtesy pause — CoinGecko free rate limit

    log.info("Intraday backfill complete.")


if __name__ == "__main__":
    run()
