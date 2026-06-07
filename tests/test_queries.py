from unittest.mock import MagicMock, patch

import pandas as pd


_RAW_ROWS = [
    {"bucket_time": "2026-06-07T00:00:00Z", "price_usd": 70000.0, "volume_24h": 40e9},
    {"bucket_time": "2026-06-07T14:00:00Z", "price_usd": 71000.0, "volume_24h": 41e9},
    {"bucket_time": "2026-06-07T14:15:00Z", "price_usd": 71200.0, "volume_24h": 42e9},
    {"bucket_time": "2026-06-08T00:00:00Z", "price_usd": 69000.0, "volume_24h": 39e9},
]


def _mock_client_returning(rows):
    client = MagicMock()
    (client.table.return_value
     .select.return_value
     .eq.return_value
     .gte.return_value
     .order.return_value
     .execute.return_value.data) = rows
    return client


def test_get_price_history_short_range_keeps_intraday_rows():
    import dashboard.queries as q
    q.get_price_history.clear()
    with patch.object(q, "_get_client", return_value=_mock_client_returning(_RAW_ROWS)):
        df = q.get_price_history("bitcoin", days=7)
    # intraday: all 4 raw snapshots preserved (no daily collapse)
    assert len(df) == 4


def test_get_price_history_long_range_collapses_to_daily():
    import dashboard.queries as q
    q.get_price_history.clear()
    with patch.object(q, "_get_client", return_value=_mock_client_returning(_RAW_ROWS)):
        df = q.get_price_history("bitcoin", days=30)
    # daily: 4 raw rows over 2 UTC dates collapse to 2 points
    assert len(df) == 2
    assert df.iloc[-1]["price_usd"] == 69000.0


def test_normalize_price_history_to_daily_buckets_fills_mixed_frequency_gaps():
    from dashboard.queries import normalize_price_history

    df = pd.DataFrame({
        "bucket_time": pd.to_datetime([
            "2026-06-05T00:00:00Z",
            "2026-06-06T00:00:00Z",
            "2026-06-07T14:00:00Z",
            "2026-06-07T14:15:00Z",
        ]),
        "price_usd": [70000.0, 61000.0, 62500.0, 62600.0],
        "volume_24h": [40e9, 55e9, 30e9, 31e9],
    })

    normalized = normalize_price_history(df)

    assert normalized["bucket_time"].dt.date.astype(str).tolist() == [
        "2026-06-05",
        "2026-06-06",
        "2026-06-07",
    ]
    assert normalized.iloc[-1]["price_usd"] == 62600.0
    assert normalized.iloc[-1]["volume_24h"] == 31e9
