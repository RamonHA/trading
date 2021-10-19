# Clases Pipeline para facilitar y automatizar 
# el testeo de diferentes estrategias para prediccion de assets
# o clasificacion

from datetime import date, timedelta, datetime
import pandas as pd
import numpy as np
import parser
import time
import random
from scipy.sparse import data

from sklearn.metrics import mean_squared_error, mean_absolute_error, precision_score
from sklearn.model_selection import ParameterGrid

from .procesos import Setter
from .instrumento import Instrumento
from .func_aux import *


class MyGridSearch():

    _ERRORS = {
        "rmse":mean_absolute_error,
        "mae":mean_absolute_error,
        "precision":precision_score
    }

    def __init__(self, df, regr, parameters, train_test_split = 0.8, target = "target", error = "mae"):
        
        assert type(df) == pd.DataFrame, "Df no es tipo Pandas DataFrame. Se entrego {}.".format( type(df) )

        self.df = df
        self.regr = regr
        self.parameters = parameters
        self.best = None
        self.train_test_split = train_test_split
        self.cache = []
        self.target = target

        self.error = error

    @property
    def error(self):
        return self._error
    
    @error.setter
    def error(self, value):
        if value in self._ERRORS:
            self._error = self._ERRORS[ value ]
        elif callable( value ):
            self._error = value
        else:
            raise ValueError("Error no es callable ni esta en la lista de funciones.")
            
    @property
    def regr(self):
        return self._regr
    
    @regr.setter
    def regr(self, value):
        # if regr tipo sklearn
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
        self.cache.sort_values(by = "error", ascending = True).reset_index(drop = True)
        self.best = self.cache.iloc[0]

        if debug: print( self.best )
    
    def predict(self):
        assert self.best is not None, "No se ha corrido la prueba test"

        for j, v in self.best["param"].items(): self.regr.__dict__[j] = v

        train = self.df.iloc[ :-1 ]
        test = self.df.iloc[ -1: ]

        train = train.replace( [np.inf, -np.inf], np.nan ).dropna()

        self.regr.fit( train.drop(columns = self.target), train[self.target] )

        predict = self.regr.predict( test.drop(columns = self.target) )

        return predict[-1]


class Prediction(Setter):
    _ERRORS = {
        "rmse":mean_absolute_error,
        "mae":mean_absolute_error,
    }

    def __init__(
            self,
            broker,
            fiat = None,
            instrumentos = None,
            comision = None,

            inicio = None,
            fin = None,
            frecuencia = None,

            num_assets = 5,
            
            data_manipulation = None,
            regr = None,
            error = None,

            multiple_errors = False

        ):
        """  

            regr: 
                Output: y_true, y_pred ( list/pd.Series tupple ) 
                    o   error (float)
        """

        super().__init__(
            broker = broker, 
            fiat = fiat, 
            comision = comision,
            instrumentos=instrumentos
        )
        
        self.data_manipulation = data_manipulation
        self.regr = regr
        self.error = self._ERRORS.get( error, None )
        self.multiple_errors = multiple_errors

        self.instrumentos = random.choices( list( self.instrumentos ), k = num_assets )

        self.inicio = inicio
        self.fin = fin
        self.frecuencia = frecuencia

        self.exec_time = 0
        self.cache = {
            "data_manipulation" : [],
            "regr" : [],
            "error" : []
        }
           
    @property
    def frecuencia(self):
        return self._frecuencia
    
    @frecuencia.setter
    def frecuencia(self, value):
        assert isinstance(value, str), "Frecuencia tiene que ser tipo str, se recibio {}.".format(type(value))
        self._frecuencia = value

    @property
    def inicio(self):
        return self._inicio

    @inicio.setter
    def inicio(self, value):
        if type(value) == datetime:
            self._inicio = value
        elif type(value) == date:
            self._inicio = datetime.combine(value, datetime.min.time())
        elif type(value) == str:
            self._inicio = parser.parse(value)
        else:
            raise ValueError("Inicio debe ser tipo date, datetime o str con formato valido, sin embargo se entrego {}.".format(type(value)))

    @property
    def fin(self):
        return self._fin

    @fin.setter
    def fin(self, value):
        if type(value) == datetime:
            self._fin = value
        elif type(value) == date:
            self._fin = datetime.combine(value, datetime.min.time())
        elif type(value) == str:
            self._fin = parser.parse(value)
        else:
            raise ValueError("Inicio debe ser tipo date, datetime o str con formato valido, sin embargo se entrego {}.".format(type(value)))

    def assertions(self):
        pass

    def run(self, verbose = False, timing = True):
        
        if self.multiple_errors:
            assert ( self.error is None or isinstance(self.error, list) ), "Se ha indicado de multiples errores, pero error no es una lista, o "

        if timing: start_time = time.time()

        self.results = []

        for i in self.instrumentos:
            if verbose: print(i)

            aux = [i]
            inst = Instrumento( 
                i, 
                self.inicio, 
                self.fin, 
                frecuencia = self.frecuencia, 
                broker = self.broker, 
                fiat = self.fiat,
                desde_api=False
            )

            if inst.df is None or len(inst.df) < 5: continue

            data_man = self.data_manipulation( inst )
            if isinstance(data_man, Instrumento):
                inst = data_man
            else:
                inst, auxx = data_man
                self.cache["data_manipulation"].append( [i, auxx] )
            

            regr = self.regr( inst )

            if self.error is None:
                if isinstance(regr, float) or isinstance(regr, int):
                    error = regr
                else:
                    error, auxx = regr
                    self.cache["regr"].append([i, auxx])

                if self.multiple_errors:    aux += error
                else:                       aux.append(error)
            
            else:
                if len(regr) > 2:       
                    y_true, y_pred, auxx = regr
                    self.cache["regr"].append([i, auxx])
                else:
                    y_true, y_pred = regr
                
                if self.multiple_errors:    aux += [ j( y_true, y_pred ) for j in self.error ]
                else:                       aux.append( self.error( y_true, y_pred ) )
            
            print(aux)

            self.results.append( aux )
        
        self.results = pd.DataFrame( self.results )

        if timing: self.exec_time = time.time() - start_time

        if verbose: print("Done!")
            


            

            

