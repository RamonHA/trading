import numpy as np
import pandas as pd

from trading.func_aux import min_max, dropna
from pymoo.model.problem import Problem
from .metaheuristics import Metaheuristic

class TATunning(Metaheuristic):
    def __init__(
            self,
            asset,
            regr,
            n_var,
            xu,
            xl,
            places = 1,
            normalize = True,
            seasonality = False,
            error = "relative",
            verbose = 0,
            algorithm = "de", 
            algorithm_params ={},
            n_obj = 1,
            n_constr = 0,
            type_var = np.int,
        ):
        
        self.set_algorithm(algorithm, algorithm_params)

        self.problem = TATunningProblem(
            asset=asset,
            regr=regr,
            n_var=n_var,
            xu=xu,
            xl=xl,
            places = places,
            normalize = normalize,
            seasonality = seasonality,
            error = error,
            verbose = verbose,
            n_obj = n_obj,
            n_constr = n_constr,
            type_var = type_var
        )

class TATunningProblem(Problem):

    def __init__(
            self,
            asset,
            regr,
            n_var = 11,
            xu = 50,
            xl = 3,
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

        self.places = places
        self.normalize = normalize
        self.seasonality = seasonality
        self.verbose = verbose

        self.asset = asset
        self.regr = regr
        self.error_func = error

        super().__init__(
            n_var=n_var, 
            n_obj=n_obj,
            n_constr=n_constr, 
            xl=xl, 
            xu=xu, 
            type_var=type_var ,
            elementwise_evaluation=True
        )



    @property
    def error_func(self):
        return self._error_func
    
    @error_func.setter
    def error_func(self, value):
        if isinstance(value, str):
            self._error_func = {
                "relative":self.relative
            }[ value ]
        elif callable(value):
            self._error_func = value

    @property
    def asset(self):
        return self._asset
    
    @asset.setter
    def asset(self, value):
        from trading.assets import Asset
        assert issubclass( type(value), Asset ), "Asset must be an Assert type"

        if "target" not in value.df.columns:
            value.df["target"] = value.df[ "close" ].pct_change(periods = self.places).shift(-self.places)

        self._asset = value

    def _evaluate(self, x, out, *args, **kwargs):
        if self.verbose > 0: print( "- Evaluation" )
        x = x.astype(int)
        # out["F"] = [ self.objective_function(i) for i in x]    
        out["F"] = self.objective_function(x)

    def objective_function(self, vector):
        if self.verbose > 0: print("- Objective Function")
        self.update_ta(vector)

        predict = self.predict()
        if predict is None: 
            if self.verbose > 1: print("-- Predict is None")
            return np.inf

        error = self.error(predict) 

        if self.verbose > 1: print("-- Error is ", error)

        return error

    def update_ta(self, vector):
        """ Modified the asset object from the new vector parameters """

        if self.verbose > 0: print("- Update TA")

        try:
            self._update_ta(vector=vector)
        except Exception as e:
            if self.verbose > 1: print("Update ta exception: {} \n  Vector: {} \n {}".format( e, vector.shape, vector ))

    def _update_ta(self, vector):
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

        df = dropna(df)

        if 0 in df.shape: return None, None

        df = df.replace([np.inf, -np.inf], np.nan).dropna()
        
        if len(df) < ( 5 ): return None, None

        self.test_size = int( len(df)*0.2 )      # self.places
        self.train_size = len(df) - self.test_size   # self.places
    
        return df.iloc[:self.train_size], df.iloc[-self.test_size:]

    def train_predict(self,df ):
        aux = df.tail(1)

        if len( aux.drop(columns = ["target"]).replace([ np.inf, -np.inf ], np.nan).dropna() ) == 0: return None, None

        train, _ = self.train_test(df)
        return train, aux

    def predict(self, for_real = False):
        if self.verbose > 0: print("- Predict")

        if self.normalize:
            df = min_max( self.asset.df, exception=["target"] )

        if self.verbose > 1: print("-- Len of df.dropna in Predict: ", len(df.dropna()))

        self.train, self.test = self.train_test(df) if not for_real else self.train_predict(df)

        if self.train is None or len(self.train) == 0 or len(self.test) == 0: return None

        if self.verbose > 1: print("Len of train {} - Len of test {}".format( len(self.train), len(self.test) ))

        self.regr = self.regr.fit(self.train.drop(columns = "target"), self.train["target"])
        
        predict = self.regr.predict(self.test.drop(columns = "target"))

        return predict

    def rollback(self, predicted):

        real = pd.merge( self.test[["target"]], self.asset.df, left_index=True, right_index=True, how = "left" )[["close"]].reset_index(drop = True)

        predicted += 1
        
        predicted = pd.DataFrame(predicted)
        predicted.columns = ["close"]

        predicted = pd.concat([pd.DataFrame(real.head(1)), predicted], axis = 0)
        predicted = predicted.cumprod()
        predicted = predicted.iloc[1:]
        predicted.reset_index(drop = True, inplace = True)
        
        return  predicted

    def error(self, predicted):
        if self.verbose > 0: print("- Error")
        y_true = pd.merge( self.test[["target"]], self.asset.df, left_index=True, right_index=True, how = "left" )[["close"]].reset_index(drop = True)
        
        predicted = pd.DataFrame( self.rollback( predicted ) )
        predicted = predicted.iloc[ :-1 ]  
        predicted.reset_index(drop = True, inplace = True)

        y_true = y_true.iloc[1:]
        y_true.reset_index(drop = True, inplace = True)

        return self.error_func( y_true, predicted )

    def relative(self, y_true, y_pred):
        if self.verbose > 1: print( "--- Relative Error. \nThe y_true is: {}\nAnd y_predict: {} ".format( y_true, y_pred ) )
        aux = abs( y_true - y_pred ) / y_true
        aux = aux.sum() / len(aux)
        return aux[ 0 ]
