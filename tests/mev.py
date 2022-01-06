import pytest

from trading.mev import MEV

@pytest.mark.parametrize( "data, source", [
    ("6200093973", "inegi"),
    ("SF4831", "sie")
])
def test_general(data, source):
    m = MEV(
        data = data,
        source = source,
        from_ = "api"
    )

    df = m.df

    assert ( df is not None and len(df) > 0 )