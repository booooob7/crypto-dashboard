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


def test_price_history_chart_hover_includes_volume():
    from dashboard.charts import price_history_chart
    fig = price_history_chart(_price_df(), "bitcoin")
    assert "交易量" in fig.data[0].hovertemplate
    assert fig.data[0].customdata[0][0] == 25e9


def test_price_history_chart_volume_bars_coloured_by_direction():
    from dashboard.charts import price_history_chart, _VOL_UP, _VOL_DOWN
    # rising then falling price → second bar up (green), third bar down (red)
    df = pd.DataFrame({
        "bucket_time": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"], utc=True),
        "price_usd":   [65000.0, 66000.0, 64000.0],
        "volume_24h":  [25e9, 26e9, 24e9],
    })
    fig = price_history_chart(df, "bitcoin")
    colors = list(fig.data[1].marker.color)
    assert colors == [_VOL_UP, _VOL_UP, _VOL_DOWN]


def test_price_history_chart_uses_datetime_axis():
    from dashboard.charts import price_history_chart
    fig = price_history_chart(_price_df(), "bitcoin")
    assert fig.layout.xaxis2.type == "date"
    assert fig.layout.yaxis.side == "right"


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


def test_compute_rsi_all_gains_approaches_100():
    from dashboard.charts import compute_rsi
    prices = pd.Series([float(i) for i in range(1, 30)])  # strictly rising
    rsi = compute_rsi(prices)
    assert round(rsi.iloc[-1], 1) == 100.0


def test_compute_rsi_all_losses_approaches_0():
    from dashboard.charts import compute_rsi
    prices = pd.Series([float(i) for i in range(30, 1, -1)])  # strictly falling
    rsi = compute_rsi(prices)
    assert round(rsi.iloc[-1], 1) == 0.0


def test_price_history_chart_rsi_panel_has_reference_lines():
    from dashboard.charts import price_history_chart
    dates = pd.date_range("2026-01-01", periods=20, freq="D", tz="UTC")
    df = pd.DataFrame({
        "bucket_time": dates,
        "price_usd": [100 + i for i in range(20)],
        "volume_24h": [1e9] * 20,
    })
    fig = price_history_chart(df, "bitcoin", lower_panel="rsi")
    # RSI line present and 70/30 reference lines drawn as shapes
    assert any(t.name == "RSI" for t in fig.data)
    ys = [s.y0 for s in fig.layout.shapes]
    assert 70 in ys and 30 in ys


def test_correlation_heatmap_returns_square_matrix():
    from dashboard.charts import correlation_heatmap
    dates = pd.date_range("2026-01-01", periods=10, freq="D")
    matrix = pd.DataFrame({
        "bitcoin":  [100, 102, 101, 104, 106, 105, 108, 110, 109, 112],
        "ethereum": [50, 51, 50, 52, 53, 52, 54, 55, 54, 56],   # moves with BTC
        "xrp":      [2.0, 1.9, 2.0, 1.8, 1.7, 1.8, 1.6, 1.5, 1.6, 1.4],  # moves opposite
    }, index=dates)
    fig = correlation_heatmap(matrix)
    assert isinstance(fig, go.Figure)
    z = fig.data[0].z
    # 3 coins -> 3x3 correlation matrix
    assert len(z) == 3 and len(z[0]) == 3
    # diagonal is 1.0 (self-correlation)
    assert round(z[0][0], 4) == 1.0
