import warnings
import pandas as pd
import numpy as np

class BaseOptimizer():
    def __init__(
            self,
            df,
            value = 0,
            risk = None,
            objective = None,
            time = 1,
            limits = (0, 1),
            target_return = 0
        ):
        self.value = value
        self.df = df
        self.risk = risk.lower()
        self.objective = objective.lower()
        self.time = time
        self.limits = limits
        self.target_return = target_return

    @property
    def df(self):
        return self._df
    
    @df.setter
    def df(self, value):
        assert len(value) > 0, "DataFrame must not be empty"
        self._df = value

    @property
    def exp_returns(self):
        return self._exp_returns
    
    @exp_returns.setter
    def exp_returns(self, value):
        if isinstance(value, pd.DataFrame):
            col = value.columns
            assert len(col) == 1, "Exp returns is a pandas DataFrame with more than one column"
            warnings.warn("First column of Exp Return is considered as the exp returns")
            value = value[ col[0] ]

        assert type(value) in [ pd.Series, np.ndarray, list ], "Exp returns is not Series, list or array. It is {}".format(type(value))
        self._exp_returns = value

    def N(self):
        """ 1/N Optimizer """
        raise NotImplementedError

    def optimize(self):
        raise NotImplementedError