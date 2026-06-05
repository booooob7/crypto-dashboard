import pandas as pd
import streamlit as st
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client


def _get_client() -> Client:
    """Supabase client using anon key (read-only for dashboard)."""
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_ANON_KEY"]
    return create_client(url, key)


@st.cache_data(ttl=300)
def get_latest_prices() -> pd.DataFrame:
    """Most recent price snapshot for each coin, sorted by rank."""
    client = _get_client()
    result = (client.table("prices")
              .select("*")
              .order("bucket_time", desc=True)
              .limit(200)
              .execute())
    df = pd.DataFrame(result.data)
    if df.empty:
        return df
    df = (df.sort_values("bucket_time", ascending=False)
            .groupby("coin_id")
            .first()
            .reset_index())
    return df.sort_values("rank")


@st.cache_data(ttl=300)
def get_price_history(coin_id: str, days: int = 7) -> pd.DataFrame:
    """Price + volume history for one coin over N days."""
    client = _get_client()
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    result = (client.table("prices")
              .select("bucket_time,price_usd,volume_24h")
              .eq("coin_id", coin_id)
              .gte("bucket_time", since)
              .order("bucket_time")
              .execute())
    df = pd.DataFrame(result.data)
    if not df.empty:
        df["bucket_time"] = pd.to_datetime(df["bucket_time"], utc=True)
    return df


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
def get_last_updated() -> str:
    """Timestamp of the most recent ETL price insert."""
    client = _get_client()
    result = (client.table("prices")
              .select("fetched_at")
              .order("fetched_at", desc=True)
              .limit(1)
              .execute())
    return result.data[0]["fetched_at"] if result.data else "N/A"
