from unittest.mock import patch, MagicMock

MOCK_ONCHAIN_RESPONSE = {
    "values": [
        {"x": 1704067200, "y": 950000.0},
        {"x": 1703980800, "y": 920000.0},
    ]
}


def _mock_get(data):
    mock_resp = MagicMock()
    mock_resp.json.return_value = data
    mock_resp.raise_for_status.return_value = None
    return mock_resp


def test_fetch_metric_returns_correct_shape():
    from etl.fetch_onchain import fetch_metric
    with patch("requests.get", return_value=_mock_get(MOCK_ONCHAIN_RESPONSE)):
        rows = fetch_metric("n-unique-addresses")

    assert len(rows) == 2
    row = rows[0]
    assert row["metric"] == "n-unique-addresses"
    assert row["value"] == 950000.0
    assert "recorded_at" in row
    assert "fetched_at" in row


def test_fetch_all_onchain_returns_list():
    from etl.fetch_onchain import ONCHAIN_METRICS, fetch_all_onchain
    with patch("requests.get", return_value=_mock_get(MOCK_ONCHAIN_RESPONSE)):
        rows = fetch_all_onchain()
    assert isinstance(rows, list)
    assert {r["metric"] for r in rows} == set(ONCHAIN_METRICS)
    assert len(rows) == len(ONCHAIN_METRICS) * 2
