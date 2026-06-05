from unittest.mock import MagicMock, patch
import requests


def _mock_get(data):
    mock_resp = MagicMock()
    mock_resp.json.return_value = data
    mock_resp.raise_for_status.return_value = None
    return mock_resp


def _mock_http_error_response(status_code: int):
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = requests.HTTPError(
        f"{status_code} error",
        response=MagicMock(status_code=status_code),
    )
    return mock_resp


def test_seed_price_history_deduplicates_rows_by_coin_and_bucket_time():
    from etl.seed_historical import seed_price_history

    duplicate_day_response = {
        "prices": [
            [1704067200000, 65000.0],
            [1704070800000, 65100.0],
            [1704153600000, 66000.0],
        ],
        "total_volumes": [
            [1704067200000, 25_000_000_000],
            [1704070800000, 26_000_000_000],
            [1704153600000, 27_000_000_000],
        ],
        "market_caps": [
            [1704067200000, 1_250_000_000_000],
            [1704070800000, 1_260_000_000_000],
            [1704153600000, 1_270_000_000_000],
        ],
    }

    coin = {"id": "bitcoin", "symbol": "BTC", "rank": 1}
    with patch("requests.get", return_value=_mock_get(duplicate_day_response)):
        rows = seed_price_history(coin, days=90)

    bucket_keys = [(row["coin_id"], row["bucket_time"]) for row in rows]
    assert len(bucket_keys) == len(set(bucket_keys))
    assert len(rows) == 2
    assert rows[0]["price_usd"] == 65100.0


def test_seed_price_history_retries_429_then_succeeds():
    from etl.seed_historical import seed_price_history

    response = {
        "prices": [[1704067200000, 65000.0]],
        "total_volumes": [[1704067200000, 25_000_000_000]],
        "market_caps": [[1704067200000, 1_250_000_000_000]],
    }

    coin = {"id": "bitcoin", "symbol": "BTC", "rank": 1}
    with patch("requests.get", side_effect=[_mock_http_error_response(429), _mock_get(response)]):
        with patch("time.sleep"):
            rows = seed_price_history(coin, days=90)

    assert len(rows) == 1
    assert rows[0]["coin_id"] == "bitcoin"
