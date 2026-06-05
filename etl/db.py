import os
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client


def get_client() -> Client:
    """Create Supabase client using service role key for ETL writes.

    Uses SERVICE_ROLE_KEY intentionally to bypass Row Level Security (RLS).
    This allows ETL operations to write to protected tables.
    In contrast, the frontend uses ANON_KEY which respects RLS.

    Returns:
        Client: Configured Supabase client instance.
    """
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)


def bucket_time_now() -> str:
    """Return current UTC time truncated to the nearest 15-minute interval as ISO string.

    Prices are aggregated into 15-minute buckets to provide consistent time-series data.
    This function aligns the current time to the start of the nearest 15-minute bucket.
    For example: 14:37:42 -> 14:30:00, 14:48:15 -> 14:45:00

    Returns:
        str: ISO 8601 formatted timestamp (UTC, with timezone info).
    """
    now = datetime.now(timezone.utc)
    minutes = (now.minute // 15) * 15
    bucketed = now.replace(minute=minutes, second=0, microsecond=0)
    return bucketed.isoformat()


def upsert_prices(client: Client, rows: list[dict]) -> None:
    """Upsert price records into the prices table.

    Inserts new price records or updates existing ones (identified by coin_id and bucket_time).
    All exceptions from the Supabase client propagate to the caller.
    The caller (run_etl.py) is responsible for deciding whether errors are critical.

    Args:
        client: Supabase client instance.
        rows: List of dictionaries with keys: coin_id, bucket_time, price_usd, etc.

    Raises:
        Any exception from the Supabase client (e.g., connection errors, constraint violations).
    """
    client.table("prices").upsert(rows, on_conflict="coin_id,bucket_time").execute()


def upsert_fear_greed(client: Client, rows: list[dict]) -> None:
    """Upsert fear and greed index records into the fear_greed table.

    Inserts new records or updates existing ones (identified by recorded_at).
    All exceptions from the Supabase client propagate to the caller.
    The caller (run_etl.py) is responsible for deciding whether errors are critical.

    Args:
        client: Supabase client instance.
        rows: List of dictionaries with keys: value, label, recorded_at, etc.

    Raises:
        Any exception from the Supabase client (e.g., connection errors, constraint violations).
    """
    client.table("fear_greed").upsert(rows, on_conflict="recorded_at").execute()


def upsert_onchain(client: Client, rows: list[dict]) -> None:
    """Upsert on-chain metrics into the onchain table.

    Inserts new records or updates existing ones (identified by metric and recorded_at).
    All exceptions from the Supabase client propagate to the caller.
    The caller (run_etl.py) is responsible for deciding whether errors are critical.

    Args:
        client: Supabase client instance.
        rows: List of dictionaries with keys: metric, value, recorded_at, etc.

    Raises:
        Any exception from the Supabase client (e.g., connection errors, constraint violations).
    """
    client.table("onchain").upsert(rows, on_conflict="metric,recorded_at").execute()


def fear_greed_has_today(client: Client) -> bool:
    """Check if fear and greed index data exists for today.

    Queries the fear_greed table to see if a record with today's date exists.
    Used by ETL to avoid redundant API calls if data is already fetched.

    Args:
        client: Supabase client instance.

    Returns:
        bool: True if at least one record exists for today, False otherwise.
    """
    today = datetime.now(timezone.utc).date().isoformat()
    result = (client.table("fear_greed")
              .select("id")
              .eq("recorded_at", today)
              .limit(1)
              .execute())
    return len(result.data) > 0


def onchain_has_yesterday(client: Client) -> bool:
    """Check if on-chain metrics data exists for yesterday.

    Queries the onchain table to see if records with yesterday's date exist.
    Used by ETL to avoid redundant API calls if data is already fetched.
    On-chain data is checked for yesterday (not today) because on-chain metrics
    are published and finalized once per day at a fixed time.

    Args:
        client: Supabase client instance.

    Returns:
        bool: True if at least one record exists for yesterday, False otherwise.
    """
    yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()
    result = (client.table("onchain")
              .select("id")
              .eq("recorded_at", yesterday)
              .limit(1)
              .execute())
    return len(result.data) > 0
