import pytest
from datetime import date

from trading.assets import Asset

def test_binance():
    inst = Asset(
        symbol = "ADA",
        start = date(2021,1,1),
        end = date(2021,11,1), 
        frequency = "1d", 
        broker = "Binance",
        source="ext_api"
    )

    df = inst.df

    assert (df is not None and len(df) > 0) , "Wrong Data importation"

def test_yahoo_asset():
    inst = Asset(
        symbol = "AAPL.MX",
        start = date(2021,1,1),
        end = date(2021,11,1), 
        frequency = "1d", 
        fiat = "mx"
    )

    df = inst.df

    assert ( df is not None and len(df) > 0 ), "Wrong Data importation"