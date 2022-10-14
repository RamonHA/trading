import pandas as pd
import numpy as np

from sklearn.model_selection import ParameterGrid
from trading.variables.errors import ERRORS

class BruteGridSearch():

    def __init__(
            self, 
            df = pd.DataFrame(), 
            regr = None, 
            parameters = {}, 
            train_test_split = 0.8, 
            target = "target", 
            error = "mae",
            error_ascending = True,
            verbose = 0
        ):
        """  
        
            error_ascending (bool): True if lowest error means better. False if highest error means better.
        """
        
        self.verbose = verbose

        assert type(df) == pd.DataFrame, "Df is not type Pandas DataFrame. It is  {}.".format( type(df) )

        self.df = df
        self.regr = regr
        self.parameters = parameters
        self.best = None
        self.train_test_split = train_test_split
        self.cache = []
        self.target = target
        self.error_ascending = error_ascending

        self.error = error

    @property
    def error(self):
        return self._error
    
    @error.setter
    def error(self, value):
        if value in ERRORS:
            self._error = ERRORS[ value ]
        elif callable( value ):
            self._error = value
        else:
            raise ValueError("Error is not callable nor is not the list of errors available.")
            
    @property
    def regr(self):
        return self._regr
    
    @regr.setter
    def regr(self, value):
        # if regr type sklearn
        self._regr = value

    @property
    def parameters(self):
            return self._parameters
       
    @parameters.setter
    def parameters(self, value):
        if isinstance(value, dict):
            self._parameters = list( ParameterGrid(value) )
        else:
            raise NotImplementedError

    def train_test(self, debug = False):
        df = self.df.replace( [np.inf, -np.inf], np.nan ).dropna()

        if len(df) == 0: 
            print("Al remover nan e inf, no hay informacion con la cual trabajar")
            return [], []

        train_size = int(  len(df)*self.train_test_split  )

        train = df.iloc[ :train_size ]
        test = df.iloc[ train_size: ]

        if debug:
            print("train_test Train: {}".format(train.shape))
            print("train_test Test: {}".format(train.shape))

        train = train.replace( [np.inf, -np.inf], np.nan ).dropna()
        test = test.replace( [np.inf, -np.inf], np.nan ).dropna()
    
        return train, test

    def test(self, debug = False):
        train, test = self.train_test(debug = debug )

        if debug:
            print("test Train: {}".format(train.shape))
            print("test Test: {}".format(train.shape))

        if len(train) == 0 or len(test) == 0:
            return None

        if isinstance(self.cache, pd.DataFrame): self.cache = []

        for i in self.parameters:
            for j, v in i.items(): self.regr.__dict__[j] = v

            self.regr.fit( train.drop(columns = self.target), train[self.target] )

            predict = self.regr.predict( test.drop(columns = self.target) )

            error = self.error( test[ self.target ], predict )

            self.cache.append([
                i, error
            ])
        
        self.cache = pd.DataFrame( self.cache )
        self.cache.columns = ["param", "error"]
        self.cache = self.cache.sort_values(by = "error", ascending = self.error_ascending).reset_index(drop = True)
        self.best = self.cache.iloc[0]

        if debug: print( self.best )
    
    def predict(self, one = True):
        assert self.best is not None, "Test has not been run"

        for j, v in self.best["param"].items(): self.regr.__dict__[j] = v

        if one: train, test = self.df.iloc[ :-1 ], self.df.iloc[ -1: ]
        else: train, test = self.train_test()

        train = train.replace( [np.inf, -np.inf], np.nan ).dropna()

        self.regr.fit( train.drop(columns = self.target), train[self.target] )

        predict = self.regr.predict( test.drop(columns = self.target) )

        if one: return predict[-1]
        else: return predict
    
    def run(self, **kwargs):
        self.test(**kwargs)
        return self.predict(**kwargs)


