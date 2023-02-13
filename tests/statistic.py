import pytest
from datetime import date
from trading.assets import Asset

def test_asset_ur():
    inst = Asset(
        symbol = "AAPL",
        start = date(1990,1,1),
        end = date.today(),
        frequency="1m",
        broker = "gbm",
        fiat = "mx",
        source = "db"
    )

    r = inst.unit_roots()

    assert (r is not None or len(r.dropna()) > 0)

def test_asset_durbin_watson():
    inst = Asset(
        symbol = "AAPL",
        start = date(1990,1,1),
        end = date.today(),
        frequency="1m",
        broker = "gbm",
        fiat = "mx",
        source = "db"
    )

    r = inst.durbin_watson()

    assert (r is not None or len(r.dropna()) > 0)

@pytest.mark.parametrize("targets", [[], ["close"]])
def test_asset_causality(targets):
    inst = Asset(
        symbol = "AAPL",
        start = date(1990,1,1),
        end = date.today(),
        frequency="1m",
        broker = "gbm",
        fiat = "mx",
        source = "db"
    )

    r = inst.causality()

    assert (r is not None or len(r.dropna()) > 0)
