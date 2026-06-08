import pandas as pd
import streamlit as st
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client


def _get_client() -> Client:
    """Supabase client using anon key (read-only for dashboard)."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)


# Ranges at or below this many days keep intraday (15-min) resolution;
# longer ranges collapse to one daily point to stay readable.
INTRADAY_MAX_DAYS = 7


def normalize_price_history(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse mixed daily/live snapshots into one daily point per UTC date."""
    if df.empty:
        return df

    normalized = df.copy()
    normalized["bucket_time"] = pd.to_datetime(normalized["bucket_time"], utc=True)
    normalized["date"] = normalized["bucket_time"].dt.floor("D")
    normalized = (normalized
                  .sort_values("bucket_time")
                  .groupby("date", as_index=False)
                  .agg(
                      price_usd=("price_usd", "last"),
                      volume_24h=("volume_24h", "last"),
                  )
                  .rename(columns={"date": "bucket_time"}))
    return normalized


def compute_period_changes(df: pd.DataFrame) -> pd.DataFrame:
    """Compute first-to-last percent change for each coin in a price window."""
    if df.empty:
        return pd.DataFrame(columns=["coin_id", "period_change"])

    prices = df.copy()
    prices["bucket_time"] = pd.to_datetime(prices["bucket_time"], utc=True)
    prices["price_usd"] = pd.to_numeric(prices["price_usd"], errors="coerce")
    prices = prices.dropna(subset=["coin_id", "bucket_time", "price_usd"])
    if prices.empty:
        return pd.DataFrame(columns=["coin_id", "period_change"])

    grouped = prices.sort_values("bucket_time").groupby("coin_id")
    first = grouped.first()["price_usd"]
    last = grouped.last()["price_usd"]
    changes = (((last - first) / first) * 100).replace([float("inf"), -float("inf")], pd.NA)
    return (changes.dropna()
                   .rename("period_change")
                   .reset_index())


@st.cache_data(ttl=300)
def get_price_period_changes(hours: int | None = None, days: int | None = None) -> pd.DataFrame:
    """Return percent change over a recent window for every coin in prices."""
    client = _get_client()
    if hours is not None:
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    elif days is not None:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    else:
        raise ValueError("hours or days is required")

    result = (client.table("prices")
              .select("coin_id,bucket_time,price_usd")
              .gte("bucket_time", since)
              .order("bucket_time")
              .execute())
    return compute_period_changes(pd.DataFrame(result.data))


@st.cache_data(ttl=300)
def get_latest_prices() -> pd.DataFrame:
    """Most recent COMPLETE price snapshot for each coin, sorted by rank.

    The overview cards need both the latest price AND its 24h/7d change. Backfill
    rows (hourly/daily history) intentionally have null change_24h/change_7d, and
    can carry the newest bucket_time — so simply taking the latest row would drop
    the change values from the cards. We therefore take, per coin, the most recent
    row that has a populated change_24h (i.e. a live ETL snapshot), keeping price
    and change consistent and from the same source.
    """
    client = _get_client()
    since = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    result = (client.table("prices")
              .select("*")
              .gte("bucket_time", since)
              .order("bucket_time")
              .execute())
    df = pd.DataFrame(result.data)
    if df.empty:
        return df

    complete = df[df["change_24h"].notna()]
    # Fall back to all rows if no complete snapshot exists yet (e.g. fresh DB)
    source = complete if not complete.empty else df
    latest = (source.sort_values("bucket_time")
                    .groupby("coin_id", as_index=False)
                    .tail(1))
    return latest.sort_values("rank")


@st.cache_data(ttl=300)
def get_price_history(coin_id: str, days: int = 7) -> pd.DataFrame:
    """Price + volume history for one coin over N days.

    Short ranges (<= INTRADAY_MAX_DAYS) keep the raw 15-minute snapshots so the
    intraday detail the ETL collects is actually visible. Longer ranges collapse
    to one point per UTC day to stay readable.
    """
    client = _get_client()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    result = (client.table("prices")
              .select("bucket_time,price_usd,volume_24h")
              .eq("coin_id", coin_id)
              .gte("bucket_time", since)
              .order("bucket_time")
              .execute())
    df = pd.DataFrame(result.data)
    if df.empty:
        return df
    df["bucket_time"] = pd.to_datetime(df["bucket_time"], utc=True)
    if days <= INTRADAY_MAX_DAYS:
        # intraday: resample to a uniform hourly grid so backfill (hourly) and
        # live ETL (15-min) snapshots don't produce uneven bar widths.
        hourly = (df.set_index("bucket_time")
                    .sort_index()
                    .resample("1h")
                    .agg(price_usd=("price_usd", "last"),
                         volume_24h=("volume_24h", "last"))
                    .dropna(subset=["price_usd"])
                    .reset_index())
        return hourly
    return normalize_price_history(df)


@st.cache_data(ttl=300)
def get_fear_greed_history(days: int = 30) -> pd.DataFrame:
    """Fear & Greed index for the last N days."""
    client = _get_client()
    since = (datetime.now(timezone.utc).date() - timedelta(days=days)).isoformat()
    result = (client.table("fear_greed")
              .select("*")
              .gte("recorded_at", since)
              .order("recorded_at")
              .execute())
    return pd.DataFrame(result.data)


@st.cache_data(ttl=300)
def get_onchain_history(metric: str = "n-unique-addresses", days: int = 30) -> pd.DataFrame:
    """On-chain metric history for the last N days."""
    client = _get_client()
    since = (datetime.now(timezone.utc).date() - timedelta(days=days)).isoformat()
    result = (client.table("onchain")
              .select("*")
              .eq("metric", metric)
              .gte("recorded_at", since)
              .order("recorded_at")
              .execute())
    return pd.DataFrame(result.data)


@st.cache_data(ttl=300)
def get_price_matrix(days: int = 30) -> pd.DataFrame:
    """Daily close price for every coin over N days, as a date x coin matrix.

    Used to compute the correlation heatmap. Stablecoins are excluded because
    their price is pegged near $1 and produces meaningless (near-zero/NaN)
    correlations that just add noise.
    """
    client = _get_client()
    since = (datetime.now(timezone.utc).date() - timedelta(days=days)).isoformat()
    result = (client.table("prices")
              .select("coin_id,bucket_time,price_usd")
              .gte("bucket_time", since)
              .order("bucket_time")
              .execute())
    df = pd.DataFrame(result.data)
    if df.empty:
        return df

    stablecoins = {"tether", "usd-coin", "dai", "first-digital-usd", "usds"}
    df = df[~df["coin_id"].isin(stablecoins)]

    df["bucket_time"] = pd.to_datetime(df["bucket_time"], utc=True)
    df["date"] = df["bucket_time"].dt.floor("D")
    # one close per coin per day, then pivot to date x coin
    daily = (df.sort_values("bucket_time")
               .groupby(["date", "coin_id"], as_index=False)
               .agg(price_usd=("price_usd", "last")))
    matrix = daily.pivot(index="date", columns="coin_id", values="price_usd")
    return matrix


@st.cache_data(ttl=300)
def get_last_updated() -> str:
    """Timestamp of the most recent ETL price insert."""
    client = _get_client()
    result = (client.table("prices")
              .select("fetched_at")
              .order("fetched_at", desc=True)
              .limit(1)
              .execute())
    return result.data[0]["fetched_at"] if result.data else "N/A"
