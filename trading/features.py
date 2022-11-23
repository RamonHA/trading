# Form a set of historical features

from trading import Asset
import pandas as pd

def checker(func):

    def wrapper(*args, **kwargs):

        obj = args[0]

        if isinstance(obj, Asset):
            obj = obj.df
        elif isinstance(obj, pd.DataFrame):
            pass
        else:
            raise ValueError( f"Object must be pd.DataFrame or Asset, but {type(obj)} was given." )

        return func(obj, **kwargs)
    
    return wrapper

@checker
def pct(obj, cols = "all", lags = 3, shift = False):
    
    if isinstance(cols, str) and cols == "all":
        cols = obj.columns
    
    assert isinstance(cols, list), f"Cols must be a list, but {type(cols)} was input."
    assert len( [c for c in cols if c in obj.columns ] ) > 0, "Columns are wrong"
    
    for c in cols:
        for i in range(1, lags + 1):
            if shift:
                obj[ f"{c}_pct_{i}" ] = obj[c].pct_change(1).shift(i)
            else:
                obj[ f"{c}_pct_{i}" ] = obj[c].pct_change(i)

    return obj