from trading.func_brokers import get_assets
from trading import Asset
from trading.optimization.pyportfolio import PyPort

import matplotlib.pyplot as plt
import pandas as pd
from dateutil.relativedelta import relativedelta

class BatchSimulation():
    def __init__(self, broker, fiat, start, end, frequency, **kwargs ):
        self.broker = broker
        self.fiat = fiat
        self.start = start
        self.end = end
        self.frequency = frequency

        self.source = "db"

        for i,v in kwargs.items(): setattr( self, i, v )

        self.assets = get_assets()[ self.broker ]

        self.df = self.get_df()

    def get_df(self):
        df = pd.DataFrame()
        symbols_list = []
        self.assets_df = {}
        for symbol in self.assets:
            asset = Asset(
                symbol=symbol,
                broker = self.broker,
                fiat = self.fiat,
                start = self.start,
                end = self.end,
                frequency = self.frequency,
                source = self.source
            )

            if asset is None or asset.df is None or len(asset.df) == 0:
                continue

            asset.df.index = pd.to_datetime( asset.df.index )

            if self.frequency == "1m":
                asset.df = asset.df[ asset.df.index.map(lambda x : x.day == 1) ]
            
            asset.df.sort_index(ascending = True, inplace = True)

            df = pd.concat([ df, asset.df[["close"]] ], axis = 1)
            symbols_list.append(symbol)
            self.assets_df[ symbol ] = asset

        df.columns = symbols_list

        return df

    def analysis(self, func, simulations = None):

        self.analysis_df = pd.concat([ func(asset) for _, asset in self.assets_df.items() ], axis = 1)
        self.analysis_df.columns = [ symbol for symbol,_ in self.assets_df.items() ]

        self.simulations = simulations
        self.sim_start = self.start
        if simulations is not None:
            d = { 
                {
                    "1m":"months",
                    "1w":"weeks",
                    "1d":"days",
                    "1min":"minutes"
                }[self.frequency]:self.simulations 
            }
            self.sim_start = self.start if self.simulations is None else self.end - relativedelta( **d )

            self.analysis_df = self.analysis_df.iloc[ -simulations: ]
    
    def filter(self, filter, series, filter_qty = None):
        if filter == "positive": 
            series = series[ series > 0 ]
        
        else:
            filter_qty = filter_qty if filter_qty >= 1 else int( filter_qty * len(series) )
            if filter_qty == "highest":
                series = series.sort_values(ascending = False)[ : filter_qty]
            elif filter_qty == "lowest":
                series = series.sort_values(ascending = True)[ : filter_qty]
        
        return series

    def optimize(self, risk, objective = "", period = 10,  exp_returns = "mean", target_return = 0.01, verbose = 0, filter = None, filter_qty = None):
        
        allocation_dict, qty_dict, pct_dict = {}, {}, {}

        for date_ in self.analysis_df.index:

            if filter is not None:
                series = self.filter( filter,  self.analysis_df.loc[ date_ ], filter_qty)
                if len(series) == 0:
                    continue
                price_df = self.df[ series.index ]
                print(len(price_df.columns))

            else:
                series = self.analysis_df.loc[ date_ ]
                price_df = self.df

            if risk == "1/N":
                l = len(series)
                allocation = qty = pct = { symbol:(1/l) for symbol in price_df.columns }
            else:

                opt = PyPort(
                    value = 0,
                    df = price_df.loc[ :date_ ],
                    exp_returns= series if exp_returns else price_df.loc[ :date_ ],
                    risk = risk,
                    objective = objective,
                    time = period,
                    limits = (0,1),
                    target_return=target_return,
                    verbose = verbose,
                )

                allocation = None

                try:
                    allocation, qty, pct = opt.optimize(  )
                except Exception as e:
                    print("Couldnt generate portfolio. \nException: {}".format(e))
                    continue

            allocation_dict[ date_ ] = allocation
            qty_dict[ date_ ] = qty
            pct_dict[ date_ ] = pct
        
        print(allocation_dict)
        self.allocation = pd.DataFrame.from_dict(allocation_dict).T# .dropna(axis = 0)
        self.qty = pd.DataFrame.from_dict(qty_dict).T# .dropna(axis = 0)
        self.pct = pd.DataFrame.from_dict(pct_dict).T# .dropna(axis = 0)

    def validate(self):
        self.behavior = pd.DataFrame() 
        self.behavior["returns"] = (self.df.pct_change().shift(-1) * self.pct).sum(axis = 1)

        self.behavior = self.behavior.loc[ self.sim_start: ]

        self.behavior["acc"] = (self.behavior["returns"] + 1).cumprod()

        self.resume = {
            "mean":self.behavior["returns"].mean(),
            "std":self.behavior["returns"].std(),
            "max drawdown":self.behavior["returns"].min(),
            "sharpe":self.behavior["returns"].mean() / self.behavior["returns"].std(),
            # "sortino":(self.behavior[ self.behavior["returns"] > 0].mean() / self.behavior["returns"].std()  ),
            "acc":self.behavior["acc"].iloc[-1]
        }

        return self.resume

    def plot(self, column = "acc", **kwargs):
        self.behavior[ column ].plot(figsize = (10,4))
        plt.title( f"Simulation of {self.broker} from { self.sim_start } to {self.end} in {self.frequency} frequency." )
        plt.xlabel("Date")
        plt.ylabel("Returns")

