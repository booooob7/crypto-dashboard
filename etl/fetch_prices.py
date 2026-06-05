import logging
import os
import requests
from datetime import datetime, timezone
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception,
)
from etl.db import bucket_time_now

log = logging.getLogger(__name__)

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
EXPECTED_COIN_COUNT = 10


def _is_transient_request_error(exc: BaseException) -> bool:
    """Return True for network errors plus 429/5xx responses worth retrying."""
    if not isinstance(exc, requests.RequestException):
        return False
    response = getattr(exc, "response", None)
    if response is None:
        return True
    status_code = getattr(response, "status_code", None)
    return status_code == 429 or (status_code is not None and status_code >= 500)


def _headers() -> dict:
    key = os.environ.get("COINGECKO_API_KEY")
    return {"x-cg-demo-api-key": key} if key else {}


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=5, min=5, max=60),
    retry=retry_if_exception(_is_transient_request_error),
)
def fetch_top10_prices() -> list[dict]:
    """Fetch top-10 coins by market cap from CoinGecko. Raises on failure (critical).

    Retries only transient network/HTTP errors (requests.RequestException, which
    covers 429/5xx via raise_for_status). Validation errors (empty or malformed
    payload) raise immediately without retry — retrying would not fix bad data
    and would only delay the visible failure the ETL is meant to surface.
    """
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

    payload = response.json()
    if not isinstance(payload, list) or len(payload) == 0:
        raise ValueError(
            "CoinGecko returned an empty or malformed price list "
            f"(type={type(payload).__name__}, len={len(payload) if hasattr(payload, '__len__') else 'n/a'})"
        )

    bucket = bucket_time_now()
    fetched = datetime.now(timezone.utc).isoformat()

    rows = []
    for coin in payload:
        # Required fields — skip rows missing the critical price/identity data
        if not coin.get("id") or not coin.get("symbol") or coin.get("current_price") is None:
            continue
        rows.append({
            "coin_id": coin["id"],
            "symbol": coin["symbol"].upper(),
            "rank": coin.get("market_cap_rank"),
            "price_usd": coin["current_price"],
            "market_cap": coin.get("market_cap"),
            "volume_24h": coin.get("total_volume"),
            "change_24h": coin.get("price_change_percentage_24h"),
            "change_7d": coin.get("price_change_percentage_7d_in_currency"),
            "bucket_time": bucket,
            "fetched_at": fetched,
        })

    if len(rows) == 0:
        raise ValueError("CoinGecko response contained no usable price rows after validation")
    if len(rows) < EXPECTED_COIN_COUNT:
        log.warning("Expected %d coins, only got %d usable rows", EXPECTED_COIN_COUNT, len(rows))

    return rows
