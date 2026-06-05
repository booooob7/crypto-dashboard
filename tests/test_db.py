import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone


def test_bucket_time_now_is_15min_aligned():
    from etl.db import bucket_time_now
    result = bucket_time_now()
    dt = datetime.fromisoformat(result)
    assert dt.tzinfo is not None, "must be timezone-aware"
    assert dt.minute % 15 == 0, f"minute {dt.minute} not aligned to 15"
    assert dt.second == 0
    assert dt.microsecond == 0


def test_fear_greed_has_today_returns_true_when_row_exists():
    from etl.db import fear_greed_has_today
    mock_client = MagicMock()
    (mock_client.table.return_value
     .select.return_value
     .eq.return_value
     .limit.return_value
     .execute.return_value.data) = [{"id": 1}]
    assert fear_greed_has_today(mock_client) is True


def test_fear_greed_has_today_returns_false_when_empty():
    from etl.db import fear_greed_has_today
    mock_client = MagicMock()
    (mock_client.table.return_value
     .select.return_value
     .eq.return_value
     .limit.return_value
     .execute.return_value.data) = []
    assert fear_greed_has_today(mock_client) is False


def test_onchain_has_yesterday_returns_true_when_row_exists():
    from etl.db import onchain_has_yesterday
    mock_client = MagicMock()
    (mock_client.table.return_value
     .select.return_value
     .eq.return_value
     .limit.return_value
     .execute.return_value.data) = [{"id": 1}]
    assert onchain_has_yesterday(mock_client) is True


def test_onchain_has_yesterday_returns_false_when_empty():
    from etl.db import onchain_has_yesterday
    mock_client = MagicMock()
    (mock_client.table.return_value
     .select.return_value
     .eq.return_value
     .limit.return_value
     .execute.return_value.data) = []
    assert onchain_has_yesterday(mock_client) is False


def test_upsert_prices_calls_supabase_with_correct_table():
    from etl.db import upsert_prices
    mock_client = MagicMock()
    mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()
    rows = [{"coin_id": "bitcoin", "bucket_time": "2024-01-01T00:00:00+00:00", "price_usd": 65000.0}]
    upsert_prices(mock_client, rows)
    mock_client.table.assert_called_with("prices")
    mock_client.table.return_value.upsert.assert_called_once_with(rows, on_conflict="coin_id,bucket_time")


def test_upsert_fear_greed_calls_supabase_with_correct_table():
    from etl.db import upsert_fear_greed
    mock_client = MagicMock()
    mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()
    rows = [{"value": 72, "label": "Greed", "recorded_at": "2024-01-01"}]
    upsert_fear_greed(mock_client, rows)
    mock_client.table.assert_called_with("fear_greed")
    mock_client.table.return_value.upsert.assert_called_once_with(rows, on_conflict="recorded_at")


def test_upsert_onchain_calls_supabase_with_correct_table():
    from etl.db import upsert_onchain
    mock_client = MagicMock()
    mock_client.table.return_value.upsert.return_value.execute.return_value = MagicMock()
    rows = [{"metric": "n-unique-addresses", "value": 950000.0, "recorded_at": "2024-01-01"}]
    upsert_onchain(mock_client, rows)
    mock_client.table.assert_called_with("onchain")
    mock_client.table.return_value.upsert.assert_called_once_with(rows, on_conflict="metric,recorded_at")
