import os
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client


def get_client() -> Client:
    """Create Supabase client using service role key (ETL writes)."""
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)


def bucket_time_now() -> str:
    """Return current UTC time truncated to the nearest 15-minute interval as ISO string."""
    now = datetime.now(timezone.utc)
    minutes = (now.minute // 15) * 15
    bucketed = now.replace(minute=minutes, second=0, microsecond=0)
    return bucketed.isoformat()


def upsert_prices(client: Client, rows: list[dict]) -> None:
    client.table("prices").upsert(rows, on_conflict="coin_id,bucket_time").execute()


def upsert_fear_greed(client: Client, rows: list[dict]) -> None:
    client.table("fear_greed").upsert(rows, on_conflict="recorded_at").execute()


def upsert_onchain(client: Client, rows: list[dict]) -> None:
    client.table("onchain").upsert(rows, on_conflict="metric,recorded_at").execute()


def fear_greed_has_today(client: Client) -> bool:
    today = datetime.now(timezone.utc).date().isoformat()
    result = (client.table("fear_greed")
              .select("id")
              .eq("recorded_at", today)
              .limit(1)
              .execute())
    return len(result.data) > 0


def onchain_has_yesterday(client: Client) -> bool:
    yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    result = (client.table("onchain")
              .select("id")
              .eq("recorded_at", yesterday)
              .limit(1)
              .execute())
    return len(result.data) > 0
