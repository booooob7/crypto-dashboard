from datetime import datetime, timezone, timedelta

import pandas as pd
import streamlit as st
from path_bootstrap import ensure_project_root_on_path

ensure_project_root_on_path(__file__)

from dashboard.queries import (
    get_latest_prices,
    get_price_history,
    get_fear_greed_history,
    get_onchain_history,
    get_price_matrix,
    get_price_period_changes,
    get_last_updated,
)
from dashboard.metrics import estimate_market_cap_change_pct
from dashboard.charts import (
    price_history_chart,
    fear_greed_gauge,
    fear_greed_history_chart,
    onchain_chart,
    correlation_heatmap,
    market_bubble_chart,
    fear_greed_label_zh,
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


def to_taipei(iso_utc: str) -> str:
    """Convert a UTC ISO timestamp to a readable Taipei-time string."""
    if not iso_utc or iso_utc == "N/A":
        return "N/A"
    try:
        dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
        local = dt.astimezone(timezone(timedelta(hours=8)))
        return local.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return iso_utc


ONCHAIN_METRIC_LABELS = {
    "n-unique-addresses": "活躍地址數",
    "n-transactions": "每日交易數",
    "estimated-transaction-volume-usd": "鏈上交易量 USD",
}

BUBBLE_RANGES = {
    "1H": {"hours": 6, "latest_pair": True},
    "1D": {"column": "change_24h"},
    "1W": {"column": "change_7d"},
    "1M": {"days": 30},
    "3M": {"days": 90},
}


def format_onchain_value(metric: str, value: float) -> str:
    if metric == "estimated-transaction-volume-usd":
        return f"${value / 1e9:.2f}B"
    return f"{value:,.0f}"


def onchain_delta(df: pd.DataFrame) -> str | None:
    if len(df) < 8:
        return None
    latest = df.iloc[-1]["value"]
    previous = df.iloc[-8]["value"]
    if not previous:
        return None
    return f"{((latest - previous) / previous) * 100:.2f}% vs 7 天前"

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("控制面板")
    last_updated = get_last_updated()
    st.caption(f"最後更新：{to_taipei(last_updated)}（台北時間）")
    if st.button("🔄 重新整理資料"):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.caption("資料來源：CoinGecko · Alternative.me · Blockchain.com")

# ── Load data ─────────────────────────────────────────────────────────────────
prices_df = get_latest_prices()
fg_df = get_fear_greed_history(30)

dashboard_tab, bubble_tab = st.tabs(["儀表板", "市場泡泡圖"])

with dashboard_tab:
    # ── Section 1: Market Overview Cards ─────────────────────────────────────────
    if not prices_df.empty:
        coin_ids = prices_df["coin_id"].tolist()

        btc = prices_df[prices_df["coin_id"] == "bitcoin"].iloc[0] if "bitcoin" in coin_ids else None
        eth = prices_df[prices_df["coin_id"] == "ethereum"].iloc[0] if "ethereum" in coin_ids else None
        top10_mcap = prices_df["market_cap"].sum()
        top10_mcap_delta = format_delta(
            estimate_market_cap_change_pct(prices_df, "change_24h")
        )
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
            st.metric("🌐 前十大市值", f"${top10_mcap / 1e12:.2f}T", top10_mcap_delta)
        with col4:
            if fg_current is not None:
                st.metric(
                    "🧭 恐懼貪婪指數",
                    f"{fg_current}",
                    fear_greed_label_zh(fg_label),
                    delta_color="off",
                )
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

    lower_panel_map = {"成交量": "volume", "RSI": "rsi"}
    selected_lower = st.radio("下方指標", list(lower_panel_map.keys()), horizontal=True, key="lower_panel")

    history_df = get_price_history(selected_coin, days_map[selected_range])
    if not history_df.empty:
        st.plotly_chart(
            price_history_chart(history_df, selected_coin, lower_panel_map[selected_lower]),
            use_container_width=True,
        )
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
    st.subheader("鏈上數據分析")
    selected_onchain_metric = st.selectbox(
        "選擇鏈上指標",
        list(ONCHAIN_METRIC_LABELS.keys()),
        format_func=lambda metric: ONCHAIN_METRIC_LABELS[metric],
    )
    onchain_df = get_onchain_history(selected_onchain_metric, 30)
    if not onchain_df.empty:
        latest_onchain = onchain_df.iloc[-1]["value"]
        st.metric(
            f"比特幣{ONCHAIN_METRIC_LABELS[selected_onchain_metric]}",
            format_onchain_value(selected_onchain_metric, latest_onchain),
            onchain_delta(onchain_df),
        )
        st.plotly_chart(
            onchain_chart(onchain_df, f"比特幣{ONCHAIN_METRIC_LABELS[selected_onchain_metric]}"),
            use_container_width=True,
        )
    else:
        st.info("尚無鏈上數據。")

    st.divider()

    # ── Section 5: Coin Correlation Heatmap ──────────────────────────────────────
    st.subheader("幣種相關性分析")
    st.caption("各幣種每日報酬的相關係數：+1 同向、0 無關、−1 反向（已排除穩定幣）")
    corr_days = st.radio("相關性區間", {"30天": 30, "90天": 90}, horizontal=True, key="corr_range")
    price_matrix = get_price_matrix({"30天": 30, "90天": 90}[corr_days])
    if not price_matrix.empty and price_matrix.shape[1] >= 2:
        st.plotly_chart(correlation_heatmap(price_matrix), use_container_width=True)
    else:
        st.info("相關性資料不足 — 需要至少兩個幣種的歷史價格。")

with bubble_tab:
    st.subheader("市場泡泡圖")
    st.caption("泡泡大小代表市值，顏色代表所選期間漲跌；滑鼠移到泡泡上可查看價格、市值、成交量與 7D 漲跌。")
    if not prices_df.empty:
        if "bubble_range" not in st.session_state:
            st.session_state.bubble_range = "1D"
        bubble_range = st.session_state.bubble_range
        bubble_df = prices_df.copy()
        range_config = BUBBLE_RANGES[bubble_range]
        if "column" in range_config:
            bubble_df["period_change"] = bubble_df[range_config["column"]]
        else:
            changes_df = get_price_period_changes(
                hours=range_config.get("hours"),
                days=range_config.get("days"),
                latest_pair=range_config.get("latest_pair", False),
            )
            bubble_df = bubble_df.merge(changes_df, on="coin_id", how="left")

        if bubble_df["period_change"].notna().any():
            st.plotly_chart(
                market_bubble_chart(bubble_df, change_label=bubble_range),
                use_container_width=True,
            )
        else:
            st.info("這個時間範圍的價格點不足，請改選其他範圍或等待 ETL 累積資料。")
        st.radio("時間範圍", list(BUBBLE_RANGES.keys()), horizontal=True, key="bubble_range")
    else:
        st.info("尚無市場資料 — 請先執行 ETL。")
