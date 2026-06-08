import math
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

_BG = "#0e1117"
_GRID = "#1e2130"
_GREEN = "#00d4aa"
_YELLOW = "#e9c46a"
_BLUE = "#4cc9f0"


def fear_greed_label_zh(label: str) -> str:
    labels = {
        "Extreme Fear": "極度恐懼",
        "Fear": "恐懼",
        "Neutral": "中性",
        "Greed": "貪婪",
        "Extreme Greed": "極度貪婪",
    }
    return labels.get(label, label)


def _apply_crosshair_hover(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        hovermode="x unified",
        hoverlabel=dict(bgcolor="#151926", font_size=13),
    )
    fig.update_xaxes(
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
        spikethickness=1,
        spikecolor="rgba(255,255,255,0.55)",
        spikedash="solid",
    )
    return fig


_VOL_UP = "rgba(0,212,170,0.55)"     # 漲：綠
_VOL_DOWN = "rgba(239,83,80,0.55)"   # 跌：紅
_RSI_PERIOD = 14


def compute_rsi(prices: pd.Series, period: int = _RSI_PERIOD) -> pd.Series:
    """Relative Strength Index (RSI), 0–100.

    delta -> separate gains/losses -> rolling averages over `period` ->
    RS = avg_gain / avg_loss -> RSI = 100 - 100/(1+RS).
    >70 overbought, <30 oversold.
    """
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - 100 / (1 + rs)
    return rsi


def price_history_chart(df: pd.DataFrame, coin_id: str, lower_panel: str = "volume") -> go.Figure:
    """TradingView-style dual panel: price line (top) + direction-coloured volume bars (bottom).

    Uses a real datetime x-axis so Plotly auto-spaces sparse, horizontal tick labels
    (no more cramped/rotated daily labels). Volume bars are coloured green/red by daily
    price direction so price and volume are visually distinct. Price y-axis sits on the
    right (TradingView convention) and is range-padded to the data so it does not start
    at zero.
    """
    df = df.copy()
    df["bucket_time"] = pd.to_datetime(df["bucket_time"], utc=True).dt.tz_convert("Asia/Taipei")

    # Volume bar colours by daily price direction (first bar treated as "up")
    prices = df["price_usd"].tolist()
    vol_colors = [_VOL_UP] + [
        _VOL_UP if prices[i] >= prices[i - 1] else _VOL_DOWN
        for i in range(1, len(prices))
    ]

    # Tight, padded price range so the line fills the panel (not squashed toward zero)
    p_min, p_max = min(prices), max(prices)
    pad = (p_max - p_min) * 0.08 or p_max * 0.02
    price_range = [p_min - pad, p_max + pad]

    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.78, 0.22],
        shared_xaxes=True,
        vertical_spacing=0.04,
    )
    fig.add_trace(go.Scatter(
        x=df["bucket_time"], y=df["price_usd"],
        mode="lines", name="價格",
        line=dict(color=_GREEN, width=2),
        fill="tozeroy", fillcolor="rgba(0,212,170,0.08)",
        customdata=df[["volume_24h"]],
        hovertemplate=(
            "價格：$%{y:,.2f}<br>"
            "交易量：$%{customdata[0]:,.0f}"
            "<extra></extra>"
        ),
    ), row=1, col=1)
    show_rsi = lower_panel == "rsi"
    if show_rsi:
        rsi = compute_rsi(df["price_usd"])
        fig.add_trace(go.Scatter(
            x=df["bucket_time"], y=rsi,
            name="RSI", mode="lines",
            line=dict(color="#c792ea", width=1.8),
            hovertemplate="RSI：%{y:.1f}<extra></extra>",
        ), row=2, col=1)
        # 70 / 30 reference lines (overbought / oversold)
        fig.add_hline(y=70, line=dict(color="#e63946", width=1, dash="dot"), row=2, col=1)
        fig.add_hline(y=30, line=dict(color="#00d4aa", width=1, dash="dot"), row=2, col=1)
    else:
        fig.add_trace(go.Bar(
            x=df["bucket_time"], y=df["volume_24h"],
            name="交易量",
            marker_color=vol_colors,
            marker_line_width=0,
            hovertemplate="交易量：$%{y:,.0f}<extra></extra>",
        ), row=2, col=1)
    fig.update_layout(
        title=f"{coin_id.capitalize()} 價格與{'RSI' if show_rsi else '交易量'}",
        paper_bgcolor=_BG, plot_bgcolor=_BG,
        font=dict(color="#d1d4dc"),
        showlegend=False,
        margin=dict(l=0, r=0, t=40, b=0),
        height=480,
        bargap=0.25,
    )
    # Price panel: y-axis on the right, padded range
    fig.update_yaxes(gridcolor=_GRID, side="right", range=price_range, row=1, col=1)
    # Lower panel: y-axis on the right. RSI is fixed 0–100; volume has no gridlines.
    if show_rsi:
        fig.update_yaxes(gridcolor=_GRID, side="right", range=[0, 100],
                         tickvals=[30, 70], row=2, col=1)
    else:
        fig.update_yaxes(gridcolor=_GRID, side="right", showgrid=False, row=2, col=1)
    # Clean horizontal datetime axis. No forced tickformat — Plotly auto-picks
    # time labels for intraday spans and date labels for multi-day spans.
    fig.update_xaxes(showgrid=False)
    fig.update_xaxes(type="date", tickangle=0, row=2, col=1)
    return _apply_crosshair_hover(fig)


def fear_greed_gauge(value: int, label: str) -> go.Figure:
    """Radial gauge for current Fear & Greed value (0-100)."""
    color = "#e63946" if value < 40 else "#f4a261" if value < 60 else "#2a9d8f"
    needle_angle = math.radians(180 - (max(0, min(value, 100)) / 100 * 180))
    needle_center = (0.5, 0.08)
    needle_length = 0.37
    needle_tip = (
        needle_center[0] + needle_length * math.cos(needle_angle),
        needle_center[1] + needle_length * math.sin(needle_angle),
    )
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title=dict(text=fear_greed_label_zh(label), font=dict(size=18, color="white")),
        gauge=dict(
            axis=dict(range=[0, 100], tickcolor="white"),
            bar=dict(color=color),
            steps=[
                dict(range=[0,  25], color="#e63946"),
                dict(range=[25, 45], color="#f4a261"),
                dict(range=[45, 55], color="#e9c46a"),
                dict(range=[55, 75], color="#a8dadc"),
                dict(range=[75, 100], color="#2a9d8f"),
            ],
        ),
    ))
    fig.update_layout(
        paper_bgcolor=_BG,
        font=dict(color="white"),
        height=250,
        margin=dict(l=20, r=20, t=40, b=20),
        shapes=[
            dict(
                type="line",
                xref="paper",
                yref="paper",
                x0=needle_center[0],
                y0=needle_center[1],
                x1=needle_tip[0],
                y1=needle_tip[1],
                line=dict(color="white", width=4),
            ),
            dict(
                type="circle",
                xref="paper",
                yref="paper",
                x0=needle_center[0] - 0.018,
                y0=needle_center[1] - 0.018,
                x1=needle_center[0] + 0.018,
                y1=needle_center[1] + 0.018,
                fillcolor="white",
                line=dict(color="white"),
            ),
        ],
    )
    return fig


def fear_greed_history_chart(df: pd.DataFrame) -> go.Figure:
    """Line chart of Fear & Greed over time with area fill."""
    fig = go.Figure(go.Scatter(
        x=pd.to_datetime(df["recorded_at"]),
        y=df["value"],
        mode="lines+markers",
        name="恐懼貪婪指數",
        line=dict(color=_YELLOW, width=2),
        fill="tozeroy",
        fillcolor="rgba(233,196,106,0.1)",
    ))
    fig.update_layout(
        title="恐懼貪婪指數 — 近 30 天",
        paper_bgcolor=_BG, plot_bgcolor=_BG,
        font=dict(color="white"),
        yaxis=dict(range=[0, 100]),
        margin=dict(l=0, r=0, t=40, b=0),
        height=250,
    )
    fig.update_xaxes(gridcolor=_GRID)
    fig.update_yaxes(gridcolor=_GRID)
    return _apply_crosshair_hover(fig)


def correlation_heatmap(price_matrix: pd.DataFrame) -> go.Figure:
    """Heatmap of pairwise price-return correlations across coins.

    Takes a date x coin price matrix, converts to daily returns, computes the
    Pearson correlation matrix, and renders it. +1 (green) = move together,
    0 (grey) = unrelated, -1 (red) = move oppositely.
    """
    returns = price_matrix.pct_change().dropna(how="all")
    corr = returns.corr()
    labels = [c.capitalize() for c in corr.columns]

    fig = go.Figure(go.Heatmap(
        z=corr.values,
        x=labels,
        y=labels,
        zmin=-1, zmax=1,
        colorscale=[
            [0.0, "#e63946"],   # -1 紅：反向
            [0.5, "#2b2f3a"],   #  0 灰：無關
            [1.0, "#00d4aa"],   # +1 綠：同向
        ],
        colorbar=dict(title="相關係數", tickvals=[-1, 0, 1]),
        text=corr.round(2).values,
        texttemplate="%{text}",
        textfont=dict(size=10, color="white"),
        hovertemplate="%{y} × %{x}<br>相關係數：%{z:.2f}<extra></extra>",
    ))
    fig.update_layout(
        title="幣種價格相關性（近期每日報酬）",
        paper_bgcolor=_BG, plot_bgcolor=_BG,
        font=dict(color="white"),
        margin=dict(l=0, r=0, t=40, b=0),
        height=480,
        yaxis=dict(autorange="reversed"),
    )
    return fig


def onchain_chart(df: pd.DataFrame, metric_label: str) -> go.Figure:
    """Line chart for a single on-chain metric."""
    fig = go.Figure(go.Scatter(
        x=pd.to_datetime(df["recorded_at"]),
        y=df["value"],
        mode="lines",
        name=metric_label,
        line=dict(color=_BLUE, width=2),
    ))
    fig.update_layout(
        title=metric_label,
        paper_bgcolor=_BG, plot_bgcolor=_BG,
        font=dict(color="white"),
        margin=dict(l=0, r=0, t=40, b=0),
        height=280,
    )
    fig.update_xaxes(gridcolor=_GRID)
    fig.update_yaxes(gridcolor=_GRID)
    return _apply_crosshair_hover(fig)
