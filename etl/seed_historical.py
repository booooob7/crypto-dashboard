"""
One-time historical seed script.
Run: python -m etl.seed_historical
Requires: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in environment.
Optional: COINGECKO_API_KEY
"""
import logging
import os
import time
import requests
from datetime import datetime, timezone
from etl.db import get_client, upsert_prices, upsert_fear_greed, upsert_onchain
from etl.fetch_fear_greed import fetch_fear_greed
from etl.fetch_onchain import fetch_all_onchain

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

COINGECKO_BASE = "https://api.coingecko.com/api/v3"

# Top-10 CoinGecko IDs — update if composition changes
TOP_10_IDS = [
    "bitcoin", "ethereum", "tether", "binancecoin", "solana",
    "usd-coin", "xrp", "dogecoin", "toncoin", "cardano",
]

SYMBOL_MAP = {
    "bitcoin": "BTC", "ethereum": "ETH", "tether": "USDT",
    "binancecoin": "BNB", "solana": "SOL", "usd-coin": "USDC",
    "xrp": "XRP", "dogecoin": "DOGE", "toncoin": "TON", "cardano": "ADA",
}


def _headers() -> dict:
    key = os.environ.get("COINGECKO_API_KEY")
    return {"x-cg-demo-api-key": key} if key else {}


def seed_price_history(coin_id: str, days: int = 90) -> list[dict]:
    """Fetch daily price history for one coin from CoinGecko market_chart endpoint."""
    log.info(f"  Seeding {coin_id} ({days}d)…")
    resp = requests.get(
        f"{COINGECKO_BASE}/coins/{coin_id}/market_chart",
        headers=_headers(),
        params={"vs_currency": "usd", "days": days, "interval": "daily"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    fetched = datetime.now(timezone.utc).isoformat()
    prices   = {p[0]: p[1] for p in data["prices"]}
    volumes  = {p[0]: p[1] for p in data["total_volumes"]}
    mkt_caps = {p[0]: p[1] for p in data["market_caps"]}

    rows = []
    for ts_ms in prices:
        dt = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)
        bucket = dt.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        rows.append({
            "coin_id":     coin_id,
            "symbol":      SYMBOL_MAP.get(coin_id, coin_id[:3].upper()),
            "rank":        None,
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
    """Seed 90 days of historical data. Run once before relying on scheduled ETL."""
    client = get_client()

    # Seed price history for top 10
    for coin_id in TOP_10_IDS:
        try:
            rows = seed_price_history(coin_id, days=90)
            upsert_prices(client, rows)
            log.info(f"  → {len(rows)} rows upserted for {coin_id}")
        except Exception as exc:
            log.error(f"  Failed to seed {coin_id}: {exc}")
        time.sleep(2)  # courtesy pause — CoinGecko free rate limit

    # Seed Fear & Greed 90-day history
    log.info("Seeding Fear & Greed history…")
    try:
        rows = fetch_fear_greed(limit=90)
        upsert_fear_greed(client, rows)
        log.info(f"  → {len(rows)} rows upserted")
    except Exception as exc:
        log.error(f"  F&G seed failed: {exc}")

    # Seed on-chain (optional — may fail if Blockchain.com is flaky)
    log.info("Seeding on-chain metrics…")
    try:
        rows = fetch_all_onchain()
        upsert_onchain(client, rows)
        log.info(f"  → {len(rows)} rows upserted")
    except Exception as exc:
        log.warning(f"  On-chain seed failed (non-critical): {exc}")

    log.info("Seed complete.")


if __name__ == "__main__":
    run()
