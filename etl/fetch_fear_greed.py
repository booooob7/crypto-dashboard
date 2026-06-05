import requests
from datetime import datetime, timezone
from tenacity import retry, stop_after_attempt, wait_exponential

FANDG_BASE = "https://api.alternative.me"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_fear_greed(limit: int = 30) -> list[dict]:
    """Fetch Fear & Greed index history from Alternative.me. Non-critical enrichment."""
    response = requests.get(
        f"{FANDG_BASE}/fng/",
        params={"limit": limit, "format": "json"},
        timeout=30,
    )
    response.raise_for_status()

    fetched = datetime.now(timezone.utc).isoformat()
    rows = []
    for entry in response.json()["data"]:
        ts = int(entry.get("timestamp", 0))
        if ts == 0:
            continue  # skip entries with missing timestamp
        recorded = datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()
        rows.append({
            "value": int(entry["value"]),
            "label": entry["value_classification"],
            "recorded_at": recorded,
            "fetched_at": fetched,
        })
    return rows
