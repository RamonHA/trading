# Clases Pipeline para facilitar y automatizar 
# el testeo de diferentes estrategias para prediccion de assets
# o clasificacion

from datetime import date, datetime
import pandas as pd
from dateutil import parser
import time
import random

from trading.func_aux import *
from trading.variables.errors import ERRORS
from trading import Asset

class Prediction():

    def __init__(
            self,
            model,
            asset = None,
            conf = {},
            num_assets = 0,
            
            data_manipulation = None,
            error = None,
            multiple_errors = False,

            train_size = None,
            cv = False,

            **kwargs,

        ):
        """  
            Input:

                train_size (int, float): If lower than '1', then it is set considered as a percentaje,
                    but if '1' or bigger, it is considered as the quantity of instances to take for the train set.

                cv (bool): Cross-Validation
                    If true, set cvf (Cross-Validation folds) variable to the desired folds.
                
                kwargs:
                    If desired to change model params of a already set model, you can set 'model_params'
                    with a dictionary of the desired params to set.

            regr: 
                Output: y_true, y_pred ( list/pd.Series tupple ) 
                    o   error (float)
        """

        self.model = model

        assert asset or conf, "Asset or conf must be filled."

        # Autogenerate assets
        self.auto = False

        if asset:
            self.asset = asset
        else:
            self.auto = True
            self.conf = conf
            self.num_assets = num_assets

        self.data_manipulation = data_manipulation
        self.error = error
        self.multiple_errors = multiple_errors

        # self.instrumentos = random.choices( list( self.instrumentos ), k = num_assets )

        self.exec_time = 0
        self.cache = {
            "data_manipulation" : [],
            "regr" : [],
            "error" : []
        }
    
    @property
    def model(self):
        return self.__model
    
    @model.setter
    def model(self, value):
        if value is None:
            raise ValueError("model must be input")

        if not (callable(value.fit) and callable(value.predict) ):
            raise ValueError( f"model obj must have declared a 'fit' and 'predict' function." )

        self.__model = value

    @property
    def data_manipulation(self):
        return self.__data_manipulation
    
    @data_manipulation.setter
    def data_manipulation(self, value):
        if value is None:
            self.__data_manipulation = value
        # elif isinstance(value, str): # When datamanipulation (features) functions exists
        #     self.__data_manipulation = ERRORS[ value ]
        elif callable(value):
            self.__data_manipulation = value
        else:
            raise ValueError(f"data_manipulation must be a known function or a function, but {type(value)} was given.")

    @property
    def error(self):
        return self.__error
    
    @error.setter
    def error(self, value):
        if value is None:
            self.__error = value
        elif isinstance(value, str):
            self.__error = ERRORS[ value ]
        elif callable(value):
            self.__error = value
        else:
            raise ValueError(f"error must be a known function or a function, but {type(value)} was given.")

    def single_run(self, asset):
        asset = self.data_manipulation(asset)

        


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
            


            

            

