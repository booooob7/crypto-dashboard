"""
LOCAL PREVIEW ONLY — not part of the deployed app.

Renders the real dashboard layout (mirrors dashboard/app.py) using the real
chart builders from dashboard/charts.py, but feeds them synthetic data so you
can see the UI without any Supabase / cloud setup.

Run:  streamlit run tools/preview_app.py
"""
import sys
import os
import numpy as np
import pandas as pd
import streamlit as st

# Make the project root importable so we can reuse the real chart builders
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dashboard.charts import (  # noqa: E402
    price_history_chart,
    fear_greed_gauge,
    fear_greed_history_chart,
    onchain_chart,
    correlation_heatmap,
)

rng = np.random.default_rng(42)

COINS = [
    ("bitcoin", "BTC", 1, 103200, 2.31),
    ("ethereum", "ETH", 2, 3850, -0.52),
    ("tether", "USDT", 3, 1.00, 0.01),
    ("binancecoin", "BNB", 4, 712, 1.04),
    ("solana", "SOL", 5, 168, 4.85),
    ("ripple", "XRP", 6, 2.34, -1.20),
    ("usd-coin", "USDC", 7, 1.00, 0.00),
    ("dogecoin", "DOGE", 8, 0.21, 3.40),
    ("cardano", "ADA", 9, 0.78, -2.10),
    ("toncoin", "TON", 10, 5.12, 0.95),
]


def make_price_history(base_price: float, days: int) -> pd.DataFrame:
    n = days
    times = pd.date_range(end=pd.Timestamp.utcnow(), periods=n, freq="D")
    walk = rng.normal(0, 0.02, n).cumsum()
    prices = base_price * (1 + walk)
    volumes = rng.uniform(0.6, 1.4, n) * base_price * 1e5
    return pd.DataFrame({"bucket_time": times, "price_usd": prices, "volume_24h": volumes})


def make_fg_history(days: int = 30) -> pd.DataFrame:
    dates = pd.date_range(end=pd.Timestamp.utcnow().normalize(), periods=days, freq="D")
    base = 50 + 20 * np.sin(np.linspace(0, 3, days)) + rng.normal(0, 5, days)
    values = np.clip(base, 5, 95).astype(int)

    def label(v):
        return ("Extreme Fear" if v < 25 else "Fear" if v < 45 else
                "Neutral" if v < 55 else "Greed" if v < 75 else "Extreme Greed")
    return pd.DataFrame({"recorded_at": dates.date.astype(str),
                         "value": values,
                         "label": [label(v) for v in values]})


def make_onchain(days: int = 30) -> pd.DataFrame:
    dates = pd.date_range(end=pd.Timestamp.utcnow().normalize(), periods=days, freq="D")
    values = 900_000 + rng.normal(0, 40_000, days).cumsum() / 5 + rng.uniform(-20000, 20000, days)
    return pd.DataFrame({"recorded_at": dates.date.astype(str), "value": np.clip(values, 700_000, 1_200_000)})


# ── Page ──────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="加密貨幣市場儀表板（預覽）", page_icon="📊", layout="wide")
st.title("📊 加密貨幣市場儀表板")
st.caption("⚠️ 本機預覽 — 合成假資料，未連接即時資料庫。")

prices_df = pd.DataFrame(
    [{"coin_id": c, "symbol": s, "rank": r, "price_usd": p,
      "market_cap": p * rng.uniform(1e7, 2e7), "change_24h": ch} for c, s, r, p, ch in COINS]
)
fg_df = make_fg_history(30)

with st.sidebar:
    st.header("控制面板")
    st.caption("最後更新：2026-06-05T12:00:00+00:00（預覽）")
    st.button("🔄 重新整理資料")
    st.divider()
    st.caption("資料來源：CoinGecko · Alternative.me · Blockchain.com")

# Section 1 — overview cards
btc = prices_df[prices_df.coin_id == "bitcoin"].iloc[0]
eth = prices_df[prices_df.coin_id == "ethereum"].iloc[0]
c1, c2, c3, c4 = st.columns(4)
c1.metric("₿ 比特幣", f"${btc.price_usd:,.0f}", f"{btc.change_24h:.2f}%")
c2.metric("Ξ 以太幣", f"${eth.price_usd:,.0f}", f"{eth.change_24h:.2f}%")
c3.metric("🌐 前十大市值", f"${prices_df.market_cap.sum() / 1e12:.2f}T")
last_fg = fg_df.iloc[-1]
c4.metric("🧭 恐懼貪婪指數", f"{int(last_fg.value)} — {last_fg.label}")
st.divider()

# Section 2 — price history + volume
col_a, col_b = st.columns([2, 1])
with col_a:
    sel = st.selectbox("選擇幣種", prices_df.coin_id.tolist(), format_func=str.capitalize)
with col_b:
    days_map = {"7天": 7, "30天": 30, "90天": 90}
    rng_label = st.radio("時間範圍", list(days_map), horizontal=True)
base = float(prices_df[prices_df.coin_id == sel].iloc[0].price_usd)
st.plotly_chart(price_history_chart(make_price_history(base, days_map[rng_label]), sel),
                use_container_width=True)
st.divider()

# Section 3 — sentiment
g, t = st.columns(2)
with g:
    st.subheader("目前市場情緒")
    st.plotly_chart(fear_greed_gauge(int(last_fg.value), last_fg.label), use_container_width=True)
with t:
    st.subheader("近 30 天趨勢")
    st.plotly_chart(fear_greed_history_chart(fg_df), use_container_width=True)
st.divider()

# Section 4 — on-chain
st.subheader("鏈上數據：比特幣活躍地址數（近 30 天）")
st.plotly_chart(onchain_chart(make_onchain(30), "比特幣活躍地址數"), use_container_width=True)
st.divider()

# Section 5 — correlation heatmap (synthetic price matrix)
st.subheader("幣種相關性分析")
st.caption("各幣種每日報酬的相關係數：+1 同向、0 無關、−1 反向（已排除穩定幣）")
_dates = pd.date_range(end=pd.Timestamp.utcnow(), periods=30, freq="D")
_btc = 65000 * (1 + rng.normal(0, 0.02, 30).cumsum())
_corr_coins = {
    "bitcoin":  _btc,
    "ethereum": _btc * 0.06 * (1 + rng.normal(0, 0.005, 30)),       # 高度同向
    "binancecoin": _btc * 0.011 * (1 + rng.normal(0, 0.01, 30)),    # 中度同向
    "solana":   150 * (1 + rng.normal(0, 0.03, 30).cumsum()),       # 部分相關
    "ripple":   2.5 - _btc / 65000 * 0.8 + rng.normal(0, 0.02, 30), # 偏反向
    "dogecoin": 0.2 * (1 + rng.normal(0, 0.04, 30).cumsum()),       # 較無關
}
_matrix = pd.DataFrame(_corr_coins, index=_dates)
st.plotly_chart(correlation_heatmap(_matrix), use_container_width=True)
