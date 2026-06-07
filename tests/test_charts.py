import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timezone


def _price_df():
    return pd.DataFrame({
        "bucket_time": pd.to_datetime(["2024-01-01", "2024-01-02"], utc=True),
        "price_usd":   [65000.0, 66000.0],
        "volume_24h":  [25e9, 26e9],
    })


def _fg_df():
    return pd.DataFrame({
        "recorded_at": ["2024-01-01", "2024-01-02"],
        "value":       [45, 72],
        "label":       ["Fear", "Greed"],
    })


def _onchain_df():
    return pd.DataFrame({
        "recorded_at": ["2024-01-01", "2024-01-02"],
        "value":       [900000.0, 950000.0],
    })


def test_price_history_chart_returns_figure_with_two_traces():
    from dashboard.charts import price_history_chart
    fig = price_history_chart(_price_df(), "bitcoin")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2  # price line + volume bar


def test_price_history_chart_uses_unified_crosshair_hover():
    from dashboard.charts import price_history_chart
    fig = price_history_chart(_price_df(), "bitcoin")
    assert fig.layout.hovermode == "x unified"
    assert fig.layout.xaxis.showspikes is True
    assert fig.layout.xaxis2.showspikes is True


def test_fear_greed_gauge_returns_figure_with_correct_value():
    from dashboard.charts import fear_greed_gauge
    fig = fear_greed_gauge(72, "Greed")
    assert isinstance(fig, go.Figure)
    assert fig.data[0].value == 72


def test_fear_greed_gauge_localizes_label_and_draws_needle():
    from dashboard.charts import fear_greed_gauge
    fig = fear_greed_gauge(12, "Extreme Fear")
    assert fig.data[0].title.text == "極度恐懼"
    assert any(shape.type == "line" for shape in fig.layout.shapes)


def test_fear_greed_history_chart_returns_figure():
    from dashboard.charts import fear_greed_history_chart
    fig = fear_greed_history_chart(_fg_df())
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1


def test_onchain_chart_returns_figure():
    from dashboard.charts import onchain_chart
    fig = onchain_chart(_onchain_df(), "Active Addresses")
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 1
