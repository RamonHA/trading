
import warnings
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from copy import copy
import multiprocess as mp
import math
import re
import json
import numpy as np
import pandas as pd

from trading.assets import Asset

COMMISSIONS = {

}

def strategy(
        asset,
        time,
        function,
        end,
        frequency,
        fiat,
        broker,
        from_ = "db",
        sentiment = False,
        verbose = False
    ):

    period_analysis, interval_analysis = re.findall(r'(\d+)(\w+)', frequency)[0]
    period_analysis = int(period_analysis)

    if interval_analysis == "m":
        start = end - relativedelta(months = time*period_analysis) 
        start = start.replace(day = 1)
    elif interval_analysis == "w":
        start = end - timedelta(days = 7*time*period_analysis)
    elif interval_analysis == "d":
        start = end - timedelta(days = time*period_analysis ) 
    elif interval_analysis == "h":
        start = end - timedelta(seconds = 3600*time*period_analysis )

    if verbose:
        print("Func Strategy", asset, start, end, frequency, fiat, broker)
    
    inst = Asset( 
        asset, 
        start, 
        end, 
        frequency = frequency, 
        fiat = fiat, 
        broker = broker, 
        from_ = from_, 
        sentiment = sentiment
    )

    if inst.df is None or len(inst.df) <= 3: 
        warnings.warn("Error in strategy. Df import issue")
        # print("Error in strategy. Df import issue")
        return None

    r = function(inst)

    if verbose:
        print( "{}: {}".format( asset, r ) )

    return r

class Setter():
    def __init__(
            self,
            broker = "yahoo_asset",
            fiat = None,
            commission = None,
            assets = None,
            **kwargs
        ):
        self.broker = broker
        self.commission = COMMISSIONS.get( commission, 0.0 )
        self.fiat = fiat if fiat is not None else self.set_fiat()
        self.assets = assets if assets is not None else self.get_assets()

        self.verbose = kwargs.get("verbose", 0)

    def print_func(self, value):
        print( "\n\n", "#"*20, value, "#"*20 )
    
    def print_for(self, value):
        print("--- ", value)

    @property
    def assets(self):
        if hasattr(self, "_assets"):
            return self._assets
        else:
            self.assets = self.get_assets()
            return self._assets
    
    @assets.setter
    def assets(self, value):
        if value is not None:
            assert type(value) in [list, dict], "Asset must be a list or dictionary"
            self._assets = value
        else:
            warnings.warn("Asset list is empty")
            self._assets = {}

    def get_assets(self):
        from trading.func_aux import get_assets
        return get_assets().get( self.broker, None )

    def set_fiat(self):
        # Defaults values
        return {
            "gbm":"mx",
            "bitso":"mx",
            "binance":"usdt"
        }.get(self.broker, None)

class BaseProcess(Setter):
    def __init__(
            self,
            broker,
            fiat = None,
            commission = None,
            assets = None,
            end = date.today(),
            subdivision = None,
            **kwargs
        ):
        super().__init__(
            broker = broker, 
            fiat = fiat, 
            commission = commission,
            assets=assets,
            **kwargs
        )
        self.analysis = {}
        self.end = end
        self.subdivision = subdivision

    def strategy(self, end, from_ = "db", parallel = False, **kwargs):

        if self.verbose > 0:
            self.print_func( "Strategy" )

        or_assets = copy( self.assets )
        for a, v in self.analysis.items():

            if self.verbose > 1:
                self.print_for("Analysis: {}".format( a ) )

            next_assets = {}

            if parallel:
                with mp.Pool( mp.cpu_count() // 2 ) as pool:
                    r = pool.starmap(
                        strategy,
                        [(
                            i, 
                            v["time"],
                            v["function"],
                            end,
                            v.get( "frequency", self.frequency_analysis ),
                            self.fiat,
                            self.broker,
                            from_,
                            kwargs.get("sentiment", False),
                            True if self.verbose > 2 else False
                        ) for i in or_assets ]
                    )
            else:
                r = [   strategy(
                            i, 
                            v["time"],
                            v["function"],
                            end,
                            v.get( "frequency", self.frequency_analysis ),
                            self.fiat,
                            self.broker,
                            from_,
                            kwargs.get("sentiment", False),
                            True if self.verbose > 2 else False
                        ) for i in or_assets ]

            if v.get("filter", "all") == "all":
                next_assets = { inst:value for inst, value in zip( or_assets, r ) if value }
            else:

                next_assets = { inst:value for inst, value in zip( or_assets, r ) if value }

                if self.subdivision is not None:
                    next_assets = self.asset_division(next_assets)

                next_assets = self.filter(
                    next_assets,
                    v.get("filter", "highest"),
                    filter_qty = v.get("filter_qty", 3),
                    **kwargs
                )

            or_assets = copy(next_assets)

        return next_assets # Al fin: or_instrumentos = next_instrumentos

    def asset_division(self, data):
        
        aux = {}
        
        for i, v in data.items():
            
            sd = self.assets[ i ][ self.subdivision ]

            if sd not in aux.keys(): aux[ sd ] = {}
            
            aux[ sd ][ i ] = v
                  
        return aux

    def filter(self, data, filter = "all", **kwargs):

        # types = [type(i) for i in data.values()]

        # if len(types) == 0: 
        #     if self.verbose > 2:
        #         print(data)

        #     raise ValueError("Types None")

        # if types.count(types[0]) != len(types):
        #     raise ValueError("List of data compossed by different data types. Types: {}".format(types))

        # types = list( set(types) )[ 0 ]

        # if types in [float, int, np.float64]:
        if self.subdivision is None:
            return {
                "all":data,
                "positive":{ i:v for i,v in data.items() if v > 0 },
                "highest":{k:v for k, v in sorted(data.items(), key = lambda item:item[1], reverse = True)[ 0: kwargs.get("filter_qty", 3)] if v > 0},
                "lowest":{k:v for k, v in sorted(data.items(), key = lambda item:item[1], reverse = False)[ 0: kwargs.get("filter_qty", 3)] if v > 0},
            }[filter]

        # elif types in [dict]:
        else:
            if filter == "positive":
                aux = { i:{ j:k for j,k in v.items() if k > 0 } for i, v in data.items() }
            elif filter in ["highest", "lowest"]:
                aux = { i:{ j:k for j, k in sorted(
                            v.items(),
                            key = lambda item:item[1], 
                            reverse = True if filter == "highest" else False
                    )[ 0: kwargs.get("filter_qty", 3)] if k > 0 
                } for i, v in data.items() }

            auxx = {}
            for i in aux: auxx.update( aux[i] )
            
            return auxx


    def preanalisis(self, data = None, pwd = None, filter = "positive", **kwargs ):
        
        if data is None:
            with open( pwd, "r" ) as fp:
                data = json.load(fp)
        
        if len(data) == 0: return None

        if isinstance(data, pd.DataFrame):
            col = data.columns
            assert len(col) == 1, "Exp returns data is a pandas DataFrame with more than one column"
            data = data[ col[0] ]

        data = self.filter(data, filter = filter, **kwargs)

        if len(data) == 0: return None

        return data
