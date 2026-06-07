import logging
from etl.db import (
    get_client, upsert_prices, upsert_fear_greed, upsert_onchain,
    fear_greed_has_today, onchain_has_yesterday,
)
from etl.fetch_prices import fetch_top10_prices
from etl.fetch_fear_greed import fetch_fear_greed
from etl.fetch_onchain import ONCHAIN_METRICS, fetch_all_onchain

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)


def run() -> None:
    """Main ETL entry point. Called by GitHub Actions every 15 minutes."""
    client = get_client()

    # ── CRITICAL: prices always fetch ────────────────────────────────────────
    log.info("Fetching prices from CoinGecko…")
    rows = fetch_top10_prices()  # raises on failure → GitHub Action fails visibly
    upsert_prices(client, rows)
    log.info(f"Upserted {len(rows)} price rows")

    # ── ENRICHMENT: Fear & Greed — fetch only when today's row is missing ───
    if not fear_greed_has_today(client):
        log.info("Fetching Fear & Greed…")
        try:
            rows = fetch_fear_greed(limit=2)
            upsert_fear_greed(client, rows)
            log.info(f"Upserted {len(rows)} fear/greed rows")
        except Exception as exc:
            log.warning(f"Fear & Greed fetch failed (non-critical): {exc}")
    else:
        log.info("Fear & Greed already up-to-date, skipping")

    # ── ENRICHMENT: on-chain — fetch only when yesterday's row is missing ───
    if not all(onchain_has_yesterday(client, metric) for metric in ONCHAIN_METRICS):
        log.info("Fetching on-chain metrics…")
        try:
            rows = fetch_all_onchain()
            upsert_onchain(client, rows)
            log.info(f"Upserted {len(rows)} on-chain rows")
        except Exception as exc:
            log.warning(f"On-chain fetch failed (non-critical): {exc}")
    else:
        log.info("On-chain metrics already up-to-date, skipping")


if __name__ == "__main__":
    run()
