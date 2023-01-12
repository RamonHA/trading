import pandas as pd
import numpy as np

from sklearn.model_selection import ParameterGrid
from trading.variables.errors import ERRORS

class BruteGridSearch():

    def __init__(
            self, 
            df, 
            regr, 
            parameters, 
            train_test_split = 0.8, 
            target = "target", 
            error = "mae",
            error_ascending = True,
            verbose = 0,
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
        elif isinstance(value, str):
            from trading.variables import params_grid as pg
            # Not use mode .get() because we want exception if key not found
            self._parameters = pg.__dict__[ value ]
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

    def apply(self, params, train, test, pos_label):
        for j, v in params.items(): self.regr.__dict__[j] = v

        self.regr.fit( train.drop(columns = self.target), train[self.target] )

        predict = self.regr.predict( test.drop(columns = self.target) )

        if pos_label:
            error = self.error( test[ self.target ], predict , pos_label = pos_label)
        else:
            error = self.error( test[ self.target ], predict )
        
        return [params, error]

    def parallel(self, train, test, **kwargs):
        import multiprocess as mp

        with mp.Pool( kwargs.get("cpus", mp.cpu_count() // 2) ) as pool:
                cache = pool.starmap(
                    self.apply,
                    [(
                        i, 
                        train,
                        test,
                        kwargs.get("pos_label")
                    ) for i in self.parameters ]
                )
        
        return cache

    def series(self, train, test, **kwargs):
        cache = [ 
            self.apply( i, train, test, kwargs.get("pos_label") ) for i in self.parameters 
        ]
        
        return cache

    def test(self, parallel = False, debug = False, **kwargs):
        train, test = self.train_test(debug = debug )

        if debug:
            print("test Train: {}".format(train.shape))
            print("test Test: {}".format(train.shape))

        if len(train) == 0 or len(test) == 0:
            return None

        if isinstance(self.cache, pd.DataFrame): self.cache = []

        # pos_label = kwargs.get( "pos_label", None )

        self.cache = self.series( train, test ) if not parallel else self.parallel( train, test, **kwargs )
        
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

        test = test.replace( [np.inf, -np.inf], 0 )

        predict = self.regr.predict( test.drop(columns = self.target) )

        self.trainset = train
        self.testset = test

        if one: return predict[-1]
        else: return predict
    
    def run(self, **kwargs):
        self.test(**kwargs)
        return self.predict(**kwargs)


