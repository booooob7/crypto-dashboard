import requests
from datetime import datetime, timezone
from tenacity import retry, stop_after_attempt, wait_exponential

BLOCKCHAIN_BASE = "https://api.blockchain.info/charts"
ONCHAIN_METRICS = (
    "n-unique-addresses",
    "n-transactions",
    "estimated-transaction-volume-usd",
)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_metric(metric_name: str, timespan: str = "30days") -> list[dict]:
    """Fetch one on-chain metric from Blockchain.com. Non-critical enrichment."""
    response = requests.get(
        f"{BLOCKCHAIN_BASE}/{metric_name}",
        params={"timespan": timespan, "format": "json", "sampled": "true"},
        timeout=30,
    )
    response.raise_for_status()

    fetched = datetime.now(timezone.utc).isoformat()
    rows = []
    for point in response.json().get("values", []):
        if "x" not in point or "y" not in point:
            continue  # skip malformed data points
        ts = int(point["x"])
        recorded = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
        rows.append({
            "metric": metric_name,
            "value": float(point["y"]),
            "recorded_at": recorded,
            "fetched_at": fetched,
        })
    return rows


def fetch_all_onchain() -> list[dict]:
    """Fetch the dashboard's BTC on-chain metric set."""
    rows = []
    for metric in ONCHAIN_METRICS:
        rows.extend(fetch_metric(metric))
    return rows
