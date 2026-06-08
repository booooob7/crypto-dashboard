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


def _latest_prices_df():
    return pd.DataFrame({
        "coin_id": ["bitcoin", "ethereum", "solana"],
        "symbol": ["BTC", "ETH", "SOL"],
        "rank": [1, 2, 5],
        "price_usd": [65000.0, 3200.0, 150.0],
        "market_cap": [1.2e12, 3.8e11, 7.2e10],
        "volume_24h": [45e9, 22e9, 4e9],
        "change_24h": [2.5, -1.2, 0.4],
        "change_7d": [6.1, -3.4, 1.8],
        "period_change": [3.4, -0.8, 1.2],
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


def test_fear_greed_gauge_needle_stays_inside_the_ring():
    from dashboard.charts import fear_greed_gauge
    fig = fear_greed_gauge(50, "Neutral")
    needle = next(shape for shape in fig.layout.shapes if shape.type == "line")
    assert fig.data[0].gauge.threshold.value is None
    assert needle.x0 == needle.x1 == 0.5
    assert needle.y0 > 0.35
    assert needle.y1 < 0.46
    assert needle.y1 > needle.y0


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
    reference_lines = {shape.y0: shape.line.color for shape in fig.layout.shapes}
    assert reference_lines[70] == "#00d4aa"
    assert reference_lines[30] == "#e63946"


def test_price_history_chart_rsi_fill_is_threshold_clipped():
    from dashboard.charts import price_history_chart
    dates = pd.date_range("2026-01-01", periods=30, freq="D", tz="UTC")
    df = pd.DataFrame({
        "bucket_time": dates,
        "price_usd": [float(i) for i in range(1, 31)],
        "volume_24h": [1e9] * 30,
    })

    fig = price_history_chart(df, "bitcoin", lower_panel="rsi")
    green_fill = next(t for t in fig.data if t.fillcolor == "rgba(0,212,170,0.45)")
    red_fill = next(t for t in fig.data if t.fillcolor == "rgba(230,57,70,0.45)")

    assert green_fill.fill == "tonexty"
    assert red_fill.fill == "tonexty"
    assert min(green_fill.y) >= 70
    assert list(red_fill.y) == [30] * len(df)


def test_price_history_chart_rsi_does_not_use_full_zone_rectangles():
    from dashboard.charts import price_history_chart
    dates = pd.date_range("2026-01-01", periods=30, freq="D", tz="UTC")
    df = pd.DataFrame({
        "bucket_time": dates,
        "price_usd": [100 + ((-1) ** i) * i for i in range(30)],
        "volume_24h": [1e9] * 30,
    })

    fig = price_history_chart(df, "bitcoin", lower_panel="rsi")
    assert not any(
        shape.type == "rect" and {shape.y0, shape.y1} in ({0, 30}, {70, 100})
        for shape in fig.layout.shapes
    )


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


def test_market_bubble_chart_uses_packed_layout_and_compact_hover():
    from dashboard.charts import market_bubble_chart

    fig = market_bubble_chart(_latest_prices_df(), change_label="1H")

    assert isinstance(fig, go.Figure)
    trace = fig.data[0]
    assert trace.mode == "markers+text"
    assert list(trace.text) == ["BTC<br>+3.4%", "ETH<br>-0.8%", "SOL<br>+1.2%"]
    assert trace.marker.size[0] > trace.marker.size[2] > trace.marker.size[1]
    assert min(trace.marker.size) >= 52
    assert max(trace.marker.size) <= 154
    assert fig.layout.xaxis.visible is False
    assert fig.layout.yaxis.visible is False
    assert trace.customdata[0][1] == "$1.2T"
    assert trace.customdata[0][2] == "$45.0B"
    assert "1H" in trace.hovertemplate
    assert "%{text}<br>" not in trace.hovertemplate
    assert trace.customdata[0][4] == "BTC"
    assert trace.customdata[0][5] == "+3.4%"
    assert "1H：%{customdata[5]}" in trace.hovertemplate
