import pandas as pd


def estimate_market_cap_change_pct(df: pd.DataFrame, change_column: str) -> float | None:
    """Estimate aggregate market-cap percentage change for the selected window."""
    if df.empty:
        return None

    data = df.copy()
    data["market_cap"] = pd.to_numeric(data["market_cap"], errors="coerce")
    data[change_column] = pd.to_numeric(data[change_column], errors="coerce")
    data = data.dropna(subset=["market_cap", change_column])
    data = data[(data["market_cap"] > 0) & (data[change_column] > -100)]
    if data.empty:
        return None

    current_market_cap = data["market_cap"].sum()
    previous_market_cap = (data["market_cap"] / (1 + data[change_column] / 100)).sum()
    if previous_market_cap == 0:
        return None
    return float(((current_market_cap - previous_market_cap) / previous_market_cap) * 100)
