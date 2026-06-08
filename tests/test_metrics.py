import pandas as pd
import pytest


def test_estimate_market_cap_change_pct_uses_24h_change_to_reconstruct_previous_value():
    from dashboard.metrics import estimate_market_cap_change_pct

    df = pd.DataFrame({
        "market_cap": [110e9, 220e9],
        "change_24h": [10.0, 10.0],
    })

    assert estimate_market_cap_change_pct(df, "change_24h") == pytest.approx(10.0)


def test_estimate_market_cap_change_pct_is_market_cap_weighted():
    from dashboard.metrics import estimate_market_cap_change_pct

    df = pd.DataFrame({
        "market_cap": [110e9, 180e9],
        "change_24h": [10.0, -10.0],
    })

    assert estimate_market_cap_change_pct(df, "change_24h") == pytest.approx(-3.3333333333)
