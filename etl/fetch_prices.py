import os
import requests
from datetime import datetime, timezone
from tenacity import retry, stop_after_attempt, wait_exponential
from etl.db import bucket_time_now

COINGECKO_BASE = "https://api.coingecko.com/api/v3"


def _headers() -> dict:
    key = os.environ.get("COINGECKO_API_KEY")
    return {"x-cg-demo-api-key": key} if key else {}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_top10_prices() -> list[dict]:
    """Fetch top-10 coins by market cap from CoinGecko. Raises on failure (critical)."""
    response = requests.get(
        f"{COINGECKO_BASE}/coins/markets",
        headers=_headers(),
        params={
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 10,
            "page": 1,
            "price_change_percentage": "24h,7d",
        },
        timeout=30,
    )
    response.raise_for_status()

    bucket = bucket_time_now()
    fetched = datetime.now(timezone.utc).isoformat()

    rows = []
    for coin in response.json():
        rows.append({
            "coin_id": coin["id"],
            "symbol": coin["symbol"].upper(),
            "rank": coin["market_cap_rank"],
            "price_usd": coin["current_price"],
            "market_cap": coin["market_cap"],
            "volume_24h": coin["total_volume"],
            "change_24h": coin.get("price_change_percentage_24h"),
            "change_7d": coin.get("price_change_percentage_7d_in_currency"),
            "bucket_time": bucket,
            "fetched_at": fetched,
        })
    return rows
