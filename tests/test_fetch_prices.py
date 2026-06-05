import pytest
from unittest.mock import patch, MagicMock

MOCK_RESPONSE = [
    {
        "id": "bitcoin",
        "symbol": "btc",
        "market_cap_rank": 1,
        "current_price": 65000.0,
        "market_cap": 1_280_000_000_000,
        "total_volume": 25_000_000_000,
        "price_change_percentage_24h": 2.5,
        "price_change_percentage_7d_in_currency": -1.2,
    },
    {
        "id": "ethereum",
        "symbol": "eth",
        "market_cap_rank": 2,
        "current_price": 3800.0,
        "market_cap": 456_000_000_000,
        "total_volume": 12_000_000_000,
        "price_change_percentage_24h": -0.5,
        "price_change_percentage_7d_in_currency": 3.1,
    },
]


def _mock_get(response_data):
    mock_resp = MagicMock()
    mock_resp.json.return_value = response_data
    mock_resp.raise_for_status.return_value = None
    return mock_resp


def test_fetch_top10_returns_correct_shape():
    from etl.fetch_prices import fetch_top10_prices
    with patch("requests.get", return_value=_mock_get(MOCK_RESPONSE)):
        rows = fetch_top10_prices()

    assert len(rows) == 2
    row = rows[0]
    assert row["coin_id"] == "bitcoin"
    assert row["symbol"] == "BTC"
    assert row["rank"] == 1
    assert row["price_usd"] == 65000.0
    assert row["change_24h"] == 2.5
    assert row["change_7d"] == -1.2
    assert "bucket_time" in row
    assert "fetched_at" in row


def test_fetch_top10_uses_api_key_when_env_set(monkeypatch):
    monkeypatch.setenv("COINGECKO_API_KEY", "test-key-abc")
    with patch("requests.get", return_value=_mock_get(MOCK_RESPONSE)) as mock_get:
        from etl import fetch_prices
        import importlib
        importlib.reload(fetch_prices)
        fetch_prices.fetch_top10_prices()
        headers = mock_get.call_args.kwargs.get("headers", {})
        assert headers.get("x-cg-demo-api-key") == "test-key-abc"


def test_fetch_top10_no_key_uses_empty_headers(monkeypatch):
    monkeypatch.delenv("COINGECKO_API_KEY", raising=False)
    with patch("requests.get", return_value=_mock_get(MOCK_RESPONSE)) as mock_get:
        from etl import fetch_prices
        import importlib
        importlib.reload(fetch_prices)
        fetch_prices.fetch_top10_prices()
        headers = mock_get.call_args.kwargs.get("headers", {})
        assert "x-cg-demo-api-key" not in headers


def test_fetch_top10_raises_on_empty_response():
    from etl.fetch_prices import fetch_top10_prices
    with patch("requests.get", return_value=_mock_get([])):
        with pytest.raises(ValueError):
            fetch_top10_prices()


def test_fetch_top10_skips_rows_missing_price():
    incomplete = [
        {"id": "bitcoin", "symbol": "btc", "market_cap_rank": 1,
         "current_price": 65000.0},
        {"id": "ethereum", "symbol": "eth", "market_cap_rank": 2,
         "current_price": None},  # missing price → skipped
    ]
    from etl.fetch_prices import fetch_top10_prices
    with patch("requests.get", return_value=_mock_get(incomplete)):
        rows = fetch_top10_prices()
    assert len(rows) == 1
    assert rows[0]["coin_id"] == "bitcoin"
