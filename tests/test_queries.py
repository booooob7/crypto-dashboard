import pandas as pd


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
    assert normalized.iloc[-1]["volume_24h"] == 61e9
