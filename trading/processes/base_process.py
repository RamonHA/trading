
import warnings
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta
from copy import copy
import multiprocess as mp
import math
import re
import json
import numpy as np

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
        sentiment = False
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

    # print(asset, start, end, frequency, fiat, broker)
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

    return function(inst)

class Setter():
    def __init__(
            self,
            broker = "yahoo_asset",
            fiat = None,
            commission = None,
            assets = None
        ):
        self.broker = broker
        self.commission = COMMISSIONS.get( commission, 0.0 )
        self.fiat = fiat if fiat is not None else self.set_fiat()
        self.assets = assets if assets is not None else self.get_assets()

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
            end = date.today()
        ):
        super().__init__(
            broker = broker, 
            fiat = fiat, 
            commission = commission,
            assets=assets
        )
        self.analysis = {}
        self.end = end

    def strategy(self, end, from_ = "db", parallel = False, **kwargs):
        or_assets = copy( self.assets )
        for a, v in self.analysis.items():

            # print("Analysis: {}".format(a))

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
                            kwargs.get("sentiment", False)
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
                            kwargs.get("sentiment", False)
                        ) for i in or_assets ]

            if v.get("filter", "all") != "all":
                next_assets = { inst:value for inst, value in zip( or_assets, r ) if value }
            else:
                next_assets = self.filter(
                    { inst:value for inst, value in zip( or_assets, r ) if value },
                    v.get("filter", "highest"),
                    **kwargs
                )

            or_assets = copy(next_assets)

        return next_assets # Al fin: or_instrumentos = next_instrumentos

    def filter(self, data, filter = "all", **kwargs):
        
        types = [type(i) for i in data.values()]
        if types.count(types[0]) != len(types):
            raise ValueError("List of data compossed by different data types. Types: {}".format(types))

        types = list( set(types) )[ 0 ]

        if types in [float, int, np.float64]:
            return {
                "all":data,
                "positive":{ i:v for i,v in data.items() if v > 0 },
                "highest":{k:v for k, v in sorted(data.items(), key = lambda item:item[1], reverse = True)[ 0: kwargs.get("filter_qty", 3)] if v > 0},
                "lowest":{k:v for k, v in sorted(data.items(), key = lambda item:item[1], reverse = False)[ 0: kwargs.get("filter_qty", 3)] if v > 0},
            }[filter]

        elif types in [dict]:
            raise NotImplementedError
        else:
            raise NotImplementedError
        
    def preanalisis(self, data = None, pwd = None, filter = "positive", **kwargs ):
        
        if data is None:
            with open( pwd, "r" ) as fp:
                data = json.load(fp)
        
        if len(data) == 0: return None

        data = self.filter(data, filter = filter, **kwargs)

        if len(data) == 0: return None

        return data


