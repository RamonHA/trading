import numpy as np
import pandas as pd

from trading.func_aux import min_max

from pymoo.core.problem import Problem
from pymoo.core.algorithm import Algorithm
from pymoo.optimize import minimize

class TATunning(Problem):

    def __ini__(
            self,
            asset,
            n_var,
            regr,
            xu,
            xl = 0,
            places = 1,
            normalize = True,
            seasonality = False,
            error = "relative",
            verbose = 0,
            n_obj = 1,
            n_constr = 0,
            type_var = np.int,
            **kwargs
        ):
        """  
            func (callable): function to minimize 
        """
        super().__init__(
            n_var=n_var, 
            n_obj=n_obj,
            n_constr=n_constr, 
            xl=xl, 
            xu=xu, 
            type_var=type_var, 
            elementwise_evaluation=True
        )

        self.asset = asset
        self.regr = regr
        self.error_func = error
        
        self.places = places
        self.normalize = normalize
        self.seasonality = seasonality
        self.verbose = verbose

    @property
    def error_func(self):
        return self._error_func
    
    @error_func.setter
    def error_func(self, value):
        if isinstance(value, str):
            self._error_func = {
                "relative":self.relative
            }
        elif callable(value):
            self._error_func = value

    @property
    def asset(self):
        return self._asset
    
    @asset.setter
    def asset(self, value):
        from trading.assets import Asset
        assert issubclass( value, Asset ), "Asset must be an Assert type"

        if "target" not in value.df.column:
            value.df = value.df[ "close" ].pct_change(periods = self.places).shift(-self.places)

        self._asset = value

    def _evaluate(self, x, out, *args, **kwargs):
        x = x.astype(int)

        out["F"] = self.objective_function(x)
    
    def objective_function(self, vector):
        self.update_ta(vector)

        predict = self.predict()
        if predict is None: return np.inf

        return self.error(predict)

    def update_ta(self, vector):
        self.asset.df['rsi'] = self.asset.rsi(vector[0])
        self.asset.df['cci'] = self.asset.cci(vector[1])
        self.asset.df['roc'] = self.asset.roc(vector[2])
        self.asset.df['trix'] = self.asset.trix(vector[3])
        self.asset.df['vi'], _ = self.asset.vortex_indicator(vector[4])
        self.asset.df['stoch'], _ = self.asset.stoch(vector[5], 3)
        self.asset.df['mass_index'] = self.asset.mass_index( vector[6] )
        
        try:
            self.asset.df['adx'], *_ = self.asset.adx( vector[7] )
        except:
            self.asset.df['adx'] = 0

        self.asset.df['macd'], *_ = self.asset.macd(vector[8], vector[9], vector[10])
    
    def train_test(self,df ):
        df = df.replace([np.inf, -np.inf], np.nan).dropna()
        if len(df) < ( 5 ): return None, None

        self.test_size = int( len(df)*0.2 )      # self.places
        self.train_size = len(df) - self.test_size   # self.places
    
        return df.iloc[:self.train_size], df.iloc[-self.test_size:]

    def train_predict(self,df ):
        aux = df.tail(1)
        train, _ = self.train_test(df)
        return train, aux

    def predict(self, for_real = False):
        
        if self.normalize:
            df = min_max( self.asset.df, exception=["target"] )

        self.train, self.test = self.train_test(df) if not for_real else self.train_predict(df)

        if self.train is None or len(self.train) == 0 or len(self.test) == 0: return None

        self.regr = self.regr.fit(self.train.drop(columns = "target"), self.train["target"])
        
        predict = self.regr.predict(self.test.drop(columns = "target"))

        return predict

    def error(self, predicted):
        y_true = pd.merge( self.test[["target"]], self.inst.df, left_index=True, right_index=True, how = "left" )[["close"]].reset_index(drop = True)
        
        predicted = pd.DataFrame(predicted)
        predicted = predicted.iloc[ :-1 ]  
        predicted.reset_index(drop = True, inplace = True)

        y_true = y_true.iloc[1:]
        y_true.reset_index(drop = True, inplace = True)

        return self.error_func( y_true, predicted )

    def relative(self, y_true, y_pred):
        aux = abs( y_true - y_pred ) / y_true
        aux = aux.sum() / len(aux)
        return aux[ 0 ]


