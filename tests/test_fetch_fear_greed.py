from unittest.mock import patch, MagicMock

MOCK_FG_RESPONSE = {
    "data": [
        {"value": "72", "value_classification": "Greed", "timestamp": "1704067200"},
        {"value": "45", "value_classification": "Fear",  "timestamp": "1703980800"},
    ]
}


def _mock_get(data):
    mock_resp = MagicMock()
    mock_resp.json.return_value = data
    mock_resp.raise_for_status.return_value = None
    return mock_resp


def test_fetch_fear_greed_returns_correct_shape():
    from etl.fetch_fear_greed import fetch_fear_greed
    with patch("requests.get", return_value=_mock_get(MOCK_FG_RESPONSE)):
        rows = fetch_fear_greed(limit=2)

    assert len(rows) == 2
    row = rows[0]
    assert row["value"] == 72
    assert row["label"] == "Greed"
    assert "recorded_at" in row
    assert "fetched_at" in row


def test_fetch_fear_greed_value_is_int():
    from etl.fetch_fear_greed import fetch_fear_greed
    with patch("requests.get", return_value=_mock_get(MOCK_FG_RESPONSE)):
        rows = fetch_fear_greed(limit=2)
    assert isinstance(rows[0]["value"], int)
