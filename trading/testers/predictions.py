# Clases Pipeline para facilitar y automatizar 
# el testeo de diferentes estrategias para prediccion de assets
# o clasificacion

from datetime import date, datetime
import pandas as pd
from dateutil import parser
import time
import random

from trading.processes.base_process import Setter
from trading.func_aux import *
from trading.variables.errors import ERRORS
from trading import Asset

class Prediction(Setter):

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
        self.error = error
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
    def error(self):
        return self._error
    
    @error.setter
    def error(self, value):
        if value is None:
            self._error = value
        elif isinstance(value, str):
            self._error = ERRORS[ value ]
        elif callable(value):
            self._error = value
        else:
            raise ValueError("Error tiene que ser un str del diccionario de posibles o una funcion callable, pero se entrego {}".format(type(value)))

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
            inst = Asset( 
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
                
                if y_true is None and y_pred is None: continue

                if self.multiple_errors:    aux += [ j( y_true, y_pred ) for j in self.error ]
                else:                       aux.append( self.error( y_true, y_pred ) )
            
            print(aux)

            self.results.append( aux )
        
        self.results = pd.DataFrame( self.results )

        if timing: self.exec_time = time.time() - start_time

        if verbose: print("Done!")
            


            

            

