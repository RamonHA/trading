
import pandas as pd
import numpy as np

from .instrumento import Instrumento

class Portfolio():

    def __init__(
            self,
            returns = None,
            risk = None,
            df = None,
        ):

        assert type(returns) == dict, "returns tiene que ser un diccionario"
        self.returns = returns

        assert type(risk) == dict, "returns tiene que ser un diccionario"
        self.risk = risk
        
        self.df = df

    @property
    def df(self):
        return self._df
    
    @df.setter
    def df(self, value):
    
        assert type(value) == pd.DataFrame, "Df tiene que ser una pd.DataFrame, pero se entrego {}".format(type(value))

        if self.returns is not None:
            assert set( value.columns ) - set( list( self.returns.keys() ) ) == 0, "Las columnsa del df no son iguales a los retornos ingresados"
        
        if self.risk is not None:
            assert set( value.columns ) - set( list( self.risk.keys() ) ) == 0, "Las columnsa del df no son iguales a los riesgos ingresados"
    
        self._df = value

