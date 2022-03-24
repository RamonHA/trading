# Aplicacion de estrategias de Analisadores Tecnicos
# A diferencia del archivo procesos.py
# este no se encarga de como tal la formacion de un portafolio de inversiones
# solo basara sus decisiones de acuerdo a las señales de compra venta

# Se generara su clase de simulacion

# No habra clase Bot puesto que la clase Bot de procesos.py puede ser aplicda para este proposito
# donde se entregue como tal la correcta estrategia_filtro
# basado en los resultados que se puedan extraer con esta herramienta

from trading.assets import Asset
from trading.metaheuristics.metaheuristics import Metaheuristic

class Strategy():
    def __init__(
            self, 
            asset = None,
            df = None,
            buy = None,
            sell = None,
            target = None        
        ):

        if asset is not None: 
            self.asset = asset
        elif df is not None:
            self.asset = Asset()
            self.asset.df = df
        else:
            self.asset = None

        self.buy = buy
        self.sell = sell
        self.target = target

    @property
    def asset(self):
        return self._asset
    
    @asset.setter
    def asset(self, value):
        from .assets import Asset
        assert isinstance(value, Asset), "asset is not type Asset. It is {}".format( type(value) )
        self._asset = value

    def set_target(self, is_buy = True):
        
        if isinstance(self.target, str):
            assert (self.target in self.asset.df.columns), "Target {} not in DataFrame columns".format(self.target)
        elif type(self.target) in [int, float]:
            if is_buy:
                self.asset.df["target"] = self.asset.df["close"].pct_change(periods = self.target).shift(-self.target)
            else:
                self.asset.df["target"] = self.asset.df["close"].pct_change(periods = self.target)

            self.target = "target"
        
        else:
            raise ValueError("Wrong target value inputed")

    def run(self):
        assert self.asset is not None, "Introduce dataframe or asset to run"
        assert self.buy or self.sell, "Either introduce the values to enter or exit market"

        if self.buy and self.sell:
            df = self.asset.df.copy()
            df = df[ (df[self.buy] == 1) | (df[self.sell] == 1) ]
            df = df[ ( (df[self.buy] - df[self.buy].shift()) == 1) | (df[self.sell] == 1) ]
            df["target"] = df["close"].pct_change()
            self.target = "target"

        else:
            self.set_target( is_buy= bool(self.buy) )
            df = self.asset.df.copy()
            df = df[ df[ self.buy ] == 1 ]
        
        if len(df) == 0:
            print("No transactions done with this strategy")
            return None

        df["acc"] = (df[self.target] + 1).cumprod()
        self.df = df

        return self.resume(df)
        
    def resume(self, df):

        self.results = {
            "acc":df["acc"].iloc[-1],
            "mean":df[self.target].mean(),
            "std":df[self.target].std(),
            "max drawdown":df[self.target].min(),
            "max up":df[self.target].max(),
            "sharpe":df[self.target].mean() / df[self.target].std(),
            "sortino":df[self.target].mean() / df[df[self.target] > 0][self.target].std()
        }

        return self.results

