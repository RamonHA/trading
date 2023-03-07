# TEST paper trading portfolio
import json

from trading.assets import Asset

class PaperTrading():
    
    def __init__(self, portfolio = {}, pwd = ""):

        if len(portfolio) > 0:
            self.portfolio = portfolio

        elif pwd != "":
            self.portfolio = self.get_portfolio(pwd)

        else:
            raise ValueError("There must be a portfolio or a path to it.")

    @property
    def portfolio(self):
        return self._portfolio
    
    @portfolio.setter
    def portfolio(self, value):
        if not isinstance(value, dict):
            raise ValueError("Portfolio must be a dictionary type. It was deliver {}".format(type(value)))
        
        # if keys not in dict

        self._portfolio = value

    def get_portfolio(self, pwd):
        with open( pwd, "r" ) as fp:
            data = json.load(fp)

        return data 

    def simulate(self):
        
        returns = []

        final_return = 0

        for a in self.portfolio["final_real_allocation"]:

            pct = self.portfolio["results"]["optimization"]["pct"][a]

            asset = Asset(
                symbol=a,
                start = self.start,
                end = self.end,
                frequency=self.frequency,
                broker = self.broker,
                fiat = self.fiat,
                source = "db"
            )

            if asset.df is None or len(asset.df) == 0: continue

            end_p = asset.df["close"].iloc[-1]
            start_p = asset.df["close"].iloc[0]

            r = ( end_p / start_p ) - 1

            final_return += (pct*r)

            returns.append([
                a,
                pct,
                r,
                pct*r,
                end_p,
                start_p    
            ])

        self.returns = returns

        return final_return
            
