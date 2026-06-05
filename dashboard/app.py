import pandas as pd
import streamlit as st
from dashboard.queries import (
    get_latest_prices,
    get_price_history,
    get_fear_greed_history,
    get_onchain_history,
    get_last_updated,
)
from dashboard.charts import (
    price_history_chart,
    fear_greed_gauge,
    fear_greed_history_chart,
    onchain_chart,
)

st.set_page_config(
    page_title="加密貨幣市場儀表板",
    page_icon="📊",
    layout="wide",
)

st.title("📊 加密貨幣市場儀表板")


def format_delta(value) -> str | None:
    """Format a percentage change for st.metric, treating NaN/None as no delta.

    Seeded historical rows store change_24h as None, which pandas surfaces as NaN.
    `NaN is not None` is True, so a plain `is not None` check would render 'nan%'.
    """
    return f"{value:.2f}%" if pd.notna(value) else None

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("控制面板")
    last_updated = get_last_updated()
    st.caption(f"最後更新：{last_updated}")
    if st.button("🔄 重新整理資料"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.caption("資料來源：CoinGecko · Alternative.me · Blockchain.com")

# ── Load data ─────────────────────────────────────────────────────────────────
prices_df = get_latest_prices()
fg_df = get_fear_greed_history(30)

# ── Section 1: Market Overview Cards ─────────────────────────────────────────
if not prices_df.empty:
    coin_ids = prices_df["coin_id"].tolist()

    btc = prices_df[prices_df["coin_id"] == "bitcoin"].iloc[0] if "bitcoin" in coin_ids else None
    eth = prices_df[prices_df["coin_id"] == "ethereum"].iloc[0] if "ethereum" in coin_ids else None
    top10_mcap = prices_df["market_cap"].sum()
    fg_current = int(fg_df.iloc[-1]["value"]) if not fg_df.empty else None
    fg_label   = fg_df.iloc[-1]["label"]       if not fg_df.empty else "N/A"

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if btc is not None:
            st.metric("₿ 比特幣", f"${btc['price_usd']:,.0f}", format_delta(btc["change_24h"]))
    with col2:
        if eth is not None:
            st.metric("Ξ 以太幣", f"${eth['price_usd']:,.0f}", format_delta(eth["change_24h"]))
    with col3:
        st.metric("🌐 前十大市值", f"${top10_mcap / 1e12:.2f}T")
    with col4:
        if fg_current is not None:
            st.metric("🧭 恐懼貪婪指數", f"{fg_current} — {fg_label}")
else:
    st.warning("尚無價格資料 — 請先執行 seed 腳本。")

st.divider()

# ── Section 2: Price History + Volume ────────────────────────────────────────
coin_options = prices_df["coin_id"].tolist() if not prices_df.empty else ["bitcoin"]
col_a, col_b = st.columns([2, 1])
with col_a:
    selected_coin = st.selectbox(
        "選擇幣種",
        coin_options,
        format_func=lambda x: x.capitalize(),
    )
with col_b:
    days_map = {"7天": 7, "30天": 30, "90天": 90}
    selected_range = st.radio("時間範圍", list(days_map.keys()), horizontal=True)

history_df = get_price_history(selected_coin, days_map[selected_range])
if not history_df.empty:
    st.plotly_chart(price_history_chart(history_df, selected_coin), use_container_width=True)
else:
    st.info("尚無價格歷史資料 — 請先執行 seed 腳本，再等待 ETL 執行。")

st.divider()

# ── Section 3: Market Sentiment ───────────────────────────────────────────────
col_gauge, col_trend = st.columns(2)
with col_gauge:
    st.subheader("目前市場情緒")
    if not fg_df.empty:
        last_fg = fg_df.iloc[-1]
        st.plotly_chart(
            fear_greed_gauge(int(last_fg["value"]), last_fg["label"]),
            use_container_width=True,
        )
    else:
        st.info("尚無恐懼貪婪指數資料。")
with col_trend:
    st.subheader("近 30 天趨勢")
    if not fg_df.empty:
        st.plotly_chart(fear_greed_history_chart(fg_df), use_container_width=True)

st.divider()

# ── Section 4: On-Chain Metrics ───────────────────────────────────────────────
st.subheader("鏈上數據：比特幣活躍地址數（近 30 天）")
onchain_df = get_onchain_history("n-unique-addresses", 30)
if not onchain_df.empty:
    st.plotly_chart(
        onchain_chart(onchain_df, "比特幣活躍地址數"),
        use_container_width=True,
    )
else:
    st.info("尚無鏈上數據。")
