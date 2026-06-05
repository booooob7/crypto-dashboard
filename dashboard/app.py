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
    page_title="Crypto Dashboard",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Crypto Market Dashboard")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Controls")
    last_updated = get_last_updated()
    st.caption(f"Last updated: {last_updated}")
    if st.button("🔄 Refresh data"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.caption("Sources: CoinGecko · Alternative.me · Blockchain.com")

# ── Load data ─────────────────────────────────────────────────────────────────
prices_df = get_latest_prices()
fg_df = get_fear_greed_history(30)

# ── Section 1: Market Overview Cards ─────────────────────────────────────────
if not prices_df.empty:
    coin_ids = prices_df["coin_id"].tolist()

    btc = prices_df[prices_df["coin_id"] == "bitcoin"].iloc[0] if "bitcoin" in coin_ids else None
    eth = prices_df[prices_df["coin_id"] == "ethereum"].iloc[0] if "ethereum" in coin_ids else None
    total_mcap = prices_df["market_cap"].sum()
    fg_current = int(fg_df.iloc[-1]["value"]) if not fg_df.empty else None
    fg_label   = fg_df.iloc[-1]["label"]       if not fg_df.empty else "N/A"

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if btc is not None:
            delta = f"{btc['change_24h']:.2f}%" if btc["change_24h"] is not None else None
            st.metric("₿ Bitcoin", f"${btc['price_usd']:,.0f}", delta)
    with col2:
        if eth is not None:
            delta = f"{eth['change_24h']:.2f}%" if eth["change_24h"] is not None else None
            st.metric("Ξ Ethereum", f"${eth['price_usd']:,.0f}", delta)
    with col3:
        st.metric("🌐 Total Market Cap", f"${total_mcap / 1e12:.2f}T")
    with col4:
        if fg_current is not None:
            st.metric("🧭 Fear & Greed", f"{fg_current} — {fg_label}")
else:
    st.warning("No price data yet — run the seed script first.")

st.divider()

# ── Section 2: Price History + Volume ────────────────────────────────────────
coin_options = prices_df["coin_id"].tolist() if not prices_df.empty else ["bitcoin"]
col_a, col_b = st.columns([2, 1])
with col_a:
    selected_coin = st.selectbox(
        "Select Coin",
        coin_options,
        format_func=lambda x: x.capitalize(),
    )
with col_b:
    days_map = {"7D": 7, "30D": 30, "90D": 90}
    selected_range = st.radio("Range", list(days_map.keys()), horizontal=True)

history_df = get_price_history(selected_coin, days_map[selected_range])
if not history_df.empty:
    st.plotly_chart(price_history_chart(history_df, selected_coin), use_container_width=True)
else:
    st.info("No price history yet — run the seed script, then wait for the ETL to run.")

st.divider()

# ── Section 3: Market Sentiment ───────────────────────────────────────────────
col_gauge, col_trend = st.columns(2)
with col_gauge:
    st.subheader("Current Sentiment")
    if not fg_df.empty:
        last_fg = fg_df.iloc[-1]
        st.plotly_chart(
            fear_greed_gauge(int(last_fg["value"]), last_fg["label"]),
            use_container_width=True,
        )
    else:
        st.info("Fear & Greed data not available yet.")
with col_trend:
    st.subheader("30-Day Trend")
    if not fg_df.empty:
        st.plotly_chart(fear_greed_history_chart(fg_df), use_container_width=True)

st.divider()

# ── Section 4: On-Chain Metrics ───────────────────────────────────────────────
st.subheader("On-Chain: Active Bitcoin Addresses (30D)")
onchain_df = get_onchain_history("n-unique-addresses", 30)
if not onchain_df.empty:
    st.plotly_chart(
        onchain_chart(onchain_df, "Active Bitcoin Addresses"),
        use_container_width=True,
    )
else:
    st.info("On-chain data not available yet.")
