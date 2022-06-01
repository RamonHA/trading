import pytest
from datetime import date

from trading.optimization import Optimization

@pytest.mark.parametrize( "assets", [
    (["aapl", "agua", "amzn", "bbajioo"]),
])
def test_1N(assets):
    
    op = Optimization(
        assets=assets,
        start = date(2018,1,1),
        end = date(2020,12,1),
        frequency="1m",
        risk = "1/N",
        broker = "gbm",
        fiat = "mx"
    )

    op.optimize()