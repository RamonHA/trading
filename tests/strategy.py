import pytest
from datetime import date
from trading.assets import Asset
from trading.strategy import Strategy

def test_strategy():
    inst = Asset(
        "eth",
        start = date(2021,1,1),
        end = date(2022,1,1),
        frequency = "1d",
        fiat = "usdt",
        broker = "binance",
        from_ = "ext_api"
    )

    st = Strategy(
        asset=inst,
        rules= {
            "buy":["rsi_14 < 30"],
            "sell":["rsi_14 > 40"]
        }
    )

    st.evaluate()