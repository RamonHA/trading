from .base_optimizer import BaseOptimizer
import numpy as np
import warnings
import pandas as pd

import riskfolio 
from riskfolio.AuxFunctions import weights_discretizetion

def riskfolio_first_function(
            df, 
            valor_portafolio,
            exp_return = None, 
            metodo = "MV",
            optimizacion = "Sharpe",
            tiempo_testeo = None,
            **kwargs
    ):
    """  
        Risk measure used, this time will be variance
        The risk measure used to optimze the portfolio. The default is ‘MV’. Posible values are:

            ’MV’: Standard Deviation.
            ’MAD’: Mean Absolute Deviation.
            ’MSV’: Semi Standard Deviation.
            ’FLPM’: First Lower Partial Moment (Omega Ratio).
            ’SLPM’: Second Lower Partial Moment (Sortino Ratio).
            ’CVaR’: Conditional Value at Risk.
            ’EVaR’: Entropic Value at Risk.
            ’WR’: Worst Realization (Minimax)
            ’MDD’: Maximum Drawdown of uncompounded cumulative returns (Calmar Ratio).
            ’ADD’: Average Drawdown of uncompounded cumulative returns.
            ’CDaR’: Conditional Drawdown at Risk of uncompounded cumulative returns.
            ’EDaR’: Entropic Drawdown at Risk of uncompounded cumulative returns.
            ’UCI’: Ulcer Index of uncompounded cumulative returns.

        Objective function, could be MinRisk, MaxRet, Utility or Sharpe
        Objective function of the optimization model. The default is ‘Sharpe’. Posible values are:

            ’MinRisk’: Minimize the selected risk measure.
            ’Utility’: Maximize the Utility function μw−lϕi(w).
            ’Sharpe’: Maximize the risk adjusted return ratio based on the selected risk measure.
            ’MaxRet’: Maximize the expected return of the portfolio.

    """
    
    df = df.replace([np.inf, -np.inf], np.nan).dropna()

    if len(df) < 2:
        return None, None

    latest_price = df.iloc[-1]

    port = riskfolio.Portfolio(returns = df.pct_change(periods = 1).dropna())

    port.assets_stats()

    if exp_return is not None:
        port.mu = exp_return
    
    model = 'Classic' # Could be Classic (historical), BL (Black Litterman) or FM (Factor Model)
    rm = metodo        
    obj = optimizacion

    hist = True # Use historical scenarios for risk measures that depend on scenarios
    rf = 0 # Risk free rate

    l = 2 # Risk aversion factor, only useful when obj is 'Utility'
            # Es el factor de cuanto un inversionista es capaz de aceptar riesgo

    w = port.optimization(model=model, rm=rm, obj=obj, rf=rf, l=l, hist=hist)

    discrete = weights_discretizetion(w, latest_price, valor_portafolio)

    discrete = discrete[0].to_dict()

    total_money = 0
    for i in discrete:
        total_money += ( latest_price[i]*discrete[i] )

    discrete_weights = {}
    for i in discrete:
        discrete_weights[i] = (latest_price[i]*discrete[i]) / total_money

    return w.to_dict(), discrete_weights

class Riskfolio(BaseOptimizer):

    __RISK = [ "MV", "mad", "msv", "flpm", "slpm", "cvar", "evar", "wr", "mdd", "add", "cdar", "edar", "uci" ]
    __OBJECTIVES = [ "MinRisk", "Utility", "Sharpe", "MaxRet" ]
    __MODELS = [ "Classic", "BL", "FM" ]

    def __init__(
            self,
            df,
            value = 0,
            exp_returns = None,
            risk = "MV",
            objective = "Sharpe",
            time = 1,
            limits = (0, 1),
            target_return = 0,
            **kwargs
        ):
        """  
            risk: 
        """
        super().__init__(
            df = df,
            value = value,
            time = time,
            limits = limits,
            target_return = target_return,
            **kwargs
        )

        self.risk = risk
        self.objective = objective

        assert self.risk in self.__RISK, f"No risk with name '{self.risk}'."
        assert self.objective in self.__OBJECTIVES, f"No objective with name '{self.objective}'."

        if exp_returns is None:
            self.exp_returns = None # self.df.pct_change()
        else:
            self.exp_returns = exp_returns.replace([np.inf, -np.inf], np.nan).dropna()

        if len(self.exp_returns) < 2:
            raise ValueError( "Data with more that one sample needed." )
        
        self.model = kwargs.get("model", "Classic")

        assert self.model in self.__MODELS, f"No model with name '{self.model}'."

    @property
    def df(self):
        return self._df
    
    @df.setter
    def df(self, value):
        assert len(value) > 0, "DataFrame must not be empty"
        
        nans = value.isna().sum(axis = 1)
        nans = nans[ nans == len(value.columns) ].index.to_list()
        value.drop(value.loc[nans].index, inplace = True)

        nans = value.isna().sum()
        nans = nans[ nans > int( len(value) * 0.2 ) ].index.to_list()
        value.drop( columns = nans, inplace = True )

        assert len(value) > 0, "DataFrame must not be empty"

        self._df = value

    @property
    def exp_returns(self):
        return self._exp_returns
    
    def set_exp_returns(self, value):
        if isinstance(value, pd.Series):
            value = self.set_exp_returns( value.to_frame() )

        elif isinstance(value, pd.DataFrame):
            col = value.columns
            # assert len(col) == 1, "Exp returns is a pandas DataFrame with more than one column"
            warnings.warn("First column of Exp Return is considered as the exp returns")
            value = value[ [col[0]] ]
        elif value is None:
            value = value

        else:
            raise ValueError( "Exp returns is not pandas DataFrame. It is {} with values {}".format(type(value), value) )

        return value

    @exp_returns.setter
    def exp_returns(self, value):
        self._exp_returns = self.set_exp_returns(value)

    def optimize(self, **kwargs):

        latest_price = self.df.iloc[-1]

        port = riskfolio.Portfolio(returns = self.df.pct_change().dropna())

        port.assets_stats()

        if self.exp_returns is not None:
            port.mu = self.exp_returns
        
        hist = True # Use historical scenarios for risk measures that depend on scenarios
        rf = 0 # Risk free rate

        l = 2 # Risk aversion factor, only useful when obj is 'Utility'
                # Es el factor de cuanto un inversionista es capaz de aceptar riesgo

        w = port.optimization(model=self.model, rm=self.risk, obj=self.objective, rf=rf, l=l, hist=hist)

        if w is None:
            raise Exception( "The problem doesn't have a solution with actual input parameters" )

        allocation = weights_discretizetion(w, latest_price, self.value)

        allocation = allocation[0].to_dict()

        qty = { i:( v*latest_price[i] ) for i,v in allocation.items() }

        total_money = sum(qty.values())
        pct = { i:(v/total_money) for i,v in qty.items() }

        return allocation, qty, pct