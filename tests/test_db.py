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
