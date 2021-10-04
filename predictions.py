# Clases Pipeline para facilitar y automatizar 
# el testeo de diferentes estrategias para prediccion de assets
# o clasificacion

from datetime import date, timedelta, datetime
import pandas as pd
import parser
import time
import random
from scipy.sparse import data

from sklearn.metrics import mean_squared_error, mean_absolute_error

from .procesos import Setter
from .instrumento import Instrumento
from .func_aux import *


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

    def run(self, verbose = True, timing = True):
        
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
            


            

            

