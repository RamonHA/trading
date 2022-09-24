import pandas as pd
from datetime import date
import json

from trading.assets import Asset
from trading.func_aux import PWD
from trading.processes.base_process import Setter

class Optimization(Setter):
    def __init__(
            self,
            assets,
            start,
            end = date.today(),
            frequency = "1d",
            exp_returns = None,
            risk = "efficientfrontier",
            objective = "maxsharpe",
            broker = "yahoo_asset",
            fiat = "mx",
            from_ = "db",
            interpolate = True,
            verbose = 0 ,
            **kwargs
        ):

        super().__init__(
            broker = broker,
            commission=0,
            fiat = fiat,
            assets=assets
        )

        self.verbose = verbose
        
        if exp_returns is None or isinstance(exp_returns, str):
            self.exp_returns = exp_returns
        else:
            self.exp_returns = self.set_exp_returns(exp_returns)

        self.start = start
        self.end = end
        self.frequency = frequency.lower()
        self.from_ = from_

        self.interpolate = interpolate

        self.risk = risk.lower()
        self.objective = objective.lower()
        self.optimizer = self.get_optimizer()

        self.target_return = kwargs.get("target_return", 0)

    def set_exp_returns(self, exp_returns):
        if isinstance(exp_returns, pd.Series):
            return exp_returns
        elif isinstance(exp_returns, dict):
            exp_returns = pd.DataFrame.from_dict( exp_returns, orient="index" )
            return exp_returns[ exp_returns.columns[0] ]
        elif isinstance(exp_returns, pd.DataFrame):
            return exp_returns[ exp_returns.columns[0] ]

    def get_optimizer(self):
        if self.risk in ["efficientfrontier", "efficientsemivariance", "efficientcvar", "efficientcdar"]:
            from .pyportfolio import PyPort
            return PyPort
        elif self.risk in ["mv" , "mad", "msv", "flpm", "slpm", "cvar", "evar", "wr", "mdd", "add", "cdar", "edar", "uci"]:
            from .riskfolio import Riskfolio
            return Riskfolio
        elif self.risk == "1/n":
            from .base_optimizer import BaseOptimizer
            return BaseOptimizer
        else:
            raise ValueError("No optimizer for {}".format(self.risk))

    @property
    def df(self):
        if hasattr(self, "_df"):
            return self._df
        else:
            self._df = self.get_df()
            return self._df
        
    @df.setter
    def df(self, value):
        if isinstance(value, pd.DataFrame):
            self._df = value
        else:
            raise ValueError()
    
    def get_df(self):
        
        if self.verbose > 0: self.print_0("Optimization: Getting Df")

        df = pd.DataFrame()
        for i in self.assets:
            inst = Asset(
                i,
                start = self.start,
                end = self.end,
                frequency=self.frequency,
                broker = self.broker,
                fiat = self.fiat,
                from_ = self.from_
            )

            if inst.df is None or len(inst.df) == 0: continue

            df = pd.concat([ df, inst.df["close"] ], axis = 1)
            df.rename(columns = {"close":i}, inplace = True)

        if self.interpolate:
            if df.isnull().any().any():
                df.interpolate(method = "linear", inplace = True)

                if df.isnull().any().any():
                    df.drop(
                        columns = list( df.isnull().any()[df.isnull().any()].index ),
                        inplace = True
                    )

        return df

    @property
    def octetos(self):
        if hasattr(self, "_octetos"):
            return self._octetos
        elif self.broker == "binance":
            self._octetos =  self.octetos_binance()
        elif self.broker == "bitso":
            self._octetos =  self.octetos_bitso()
        else:
            raise ValueError("No octetos for {}.".format(self.broker))

        return self._octetos

    def octetos_binance(self):
        """  
            Return: octetos (dict)

            to_buy (list)
        """
        pwd = PWD( "binance/octetos.json" )

        with open(pwd, "r") as fp:
            data = json.load( fp )

        return data[self.fiat]

    def octetos_bitso(self):
        return {
            "BTC":8,
            "ETH":8,
            "XRP":6,
            "LTC":8,
            "BCH":8,
            "TUSD":2,
            "BAT":8,
            "DAI":2,
            "MANA":8
        }
    
    def one_asset(self, value = 0):
        asset = self.df.columns[0]
        if value == 0:
            allocation = pct = qty = { asset:1 }
        else:
            allocation = pct = { asset:1 }
            qty = self.df[asset].iloc[-1]
            qty = {asset: value // qty }
        
        return allocation, qty, pct

    def optimize(self, value = 0, time = 1, limits = (0,1), **kwargs):

        if self.broker in ["binance", "bitso"]:
            for i in self.df.columns: self.df[i] /= pow(10, self.octetos.get(i, 1))

        if len(self.df) == 0:
            return None, None, None
        
        if len( self.df.columns ) == 1:
            return self.one_asset(value = value)

        opt = self.optimizer(
            value = value,
            df = self.df,
            exp_returns=self.exp_returns,
            risk = self.risk,
            objective = self.objective,
            time = time,
            limits = limits,
            target_return=self.target_return,
            verbose = self.verbose,
            **kwargs
        )

        allocation = None

        try:
            allocation, qty, pct = opt.optimize( **kwargs )
        except Exception as e:
            print("Couldnt generate portfolio. \nException: {}".format(e))

        if allocation is None or len(allocation) == 0: return None, None, None

        if self.broker in ["binance", "bitso"]:
            qty = { i:(v*10**(self.octetos.get(i, 1))) for i, v in qty.items() }

        return allocation, qty, pct



        