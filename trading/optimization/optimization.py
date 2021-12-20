import pandas as pd
from datetime import date

from trading.assets import Asset

class Optimization():
    def __init__(
            self,
            assets,
            start,
            end = date.today(),
            frequency = "1d",
            risk = "efficientfrontier",
            objective = "maxsharpe",
            broker = "yahoo_asset",
            fiat = "mx",
            from_ = "db",
            interpolate = True
        ):
        self.assets = assets
        self.start = start
        self.end = end
        self.frequency = frequency.lower()
        self.broker = broker.lower()
        self.fiat = fiat.lower()
        self.from_ = from_

        self.interpolate = interpolate

        self.risk = risk.lower()
        self.objective = objective.lower()
        self.optimizer = self.get_optimizer()

    def get_optimizer(self):
        if self.risk in ["efficientfrontier"]:
            from .pyportfolio import PyPort
            return PyPort
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

    def octetos(self, df):
        raise NotImplementedError
        for i in df.columns: df[i] /= pow(10, self.octetos.get(i, 1))
        return df
    
    def optimize(self, value = 0):

        self.optimizer(
            self.df,
            value,

        )