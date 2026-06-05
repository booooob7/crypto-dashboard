import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

_BG = "#0e1117"
_GRID = "#1e2130"
_GREEN = "#00d4aa"
_YELLOW = "#e9c46a"
_BLUE = "#4cc9f0"


def price_history_chart(df: pd.DataFrame, coin_id: str) -> go.Figure:
    """Dual-panel: price line (top 70%) + volume bars (bottom 30%), shared x-axis."""
    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.7, 0.3],
        shared_xaxes=True,
        vertical_spacing=0.05,
    )
    fig.add_trace(go.Scatter(
        x=df["bucket_time"], y=df["price_usd"],
        mode="lines", name="價格",
        line=dict(color=_GREEN, width=2),
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        x=df["bucket_time"], y=df["volume_24h"],
        name="交易量",
        marker_color="rgba(0,212,170,0.3)",
    ), row=2, col=1)
    fig.update_layout(
        title=f"{coin_id.capitalize()} 價格與交易量",
        paper_bgcolor=_BG, plot_bgcolor=_BG,
        font=dict(color="white"),
        legend=dict(orientation="h"),
        margin=dict(l=0, r=0, t=40, b=0),
        height=450,
    )
    fig.update_xaxes(gridcolor=_GRID)
    fig.update_yaxes(gridcolor=_GRID)
    return fig


def fear_greed_gauge(value: int, label: str) -> go.Figure:
    """Radial gauge for current Fear & Greed value (0-100)."""
    color = "#e63946" if value < 40 else "#f4a261" if value < 60 else "#2a9d8f"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title=dict(text=label, font=dict(size=18, color="white")),
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
    return fig
