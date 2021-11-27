# Aplicacion de estrategias de Analisadores Tecnicos
# A diferencia del archivo procesos.py
# este no se encarga de como tal la formacion de un portafolio de inversiones
# solo basara sus decisiones de acuerdo a las señales de compra venta

# Se generara su clase de simulacion

# No habra clase Bot puesto que la clase Bot de procesos.py puede ser aplicda para este proposito
# donde se entregue como tal la correcta estrategia_filtro
# basado en los resultados que se puedan extraer con esta herramienta


import numpy as np
import pandas as pd

from .instrumento import Instrumento
from .procesos import Setter
from .instrumentos import *

class Estrategia():
    def __init__(
            self, 
            inst,
            reglas = [],
            **kwargs
        ):
        """  
            reglas (list str):
                Ejemplo: "rsi_14 <= 30"
        """

        assert isinstance(reglas, dict), "reglas"
        self.reglas = reglas
        self.inst = inst

        self.broker = inst.broker
        self.fiat = inst.fiat
        # self.comision = inst.comision

        self.col = { "buy":[], "sell":[] }

    @property
    def reglas(self):
        return self._reglas
    
    @reglas.setter
    def reglas(self, value):
        assert isinstance(value, dict), "reglas no es tipo diccionario, se entrego {}".format(type(value))
        assert ( "buy" in value and "sell" in value ), "Diccionario tiene que indicar si son señales de compra o venta"
        self._reglas = value

    @property
    def inst(self):
        if hasattr(self, "_inst"):
            return self._inst
        else:
            return None
    
    @inst.setter
    def inst(self, value):
        if isinstance(value, Instrumento):
            self._inst = value
        else:
            raise ValueError("Se tiene que entregar un objeto Instrumento, pero se entrego {}".format( type(value) ))

    def separar_reglas(self, regla):
        by_ands = regla.split(" AND ")
        
        regla = []
        for i in by_ands:
            r = i.split(" ")
            
            regla.append( ( r[0], r[1], r[2] ) )
        
        return regla

    def aplicar(self, t, c, o, v):
        # Column and parameters
        c_aux = c.split("_")
        ta = c_aux[0]
        param = tuple( c_aux[1:] ) 
        col = "{} {} {}".format( c, o, v )

        # Calcular analyzador tecnico
        exec(
            "self.inst.df[ c ] = self.inst.{}{}".format( ta, param )
        )

        based_on = False
        try: 
            v = float(v)
        except: 
            based_on = True

        # Calcular si la regla se cumple en col
        if not based_on:
            exec(
                "self.inst.df[ col ] = self.inst.df[ c ].apply( lambda x : 1 if x {} {} else 0)".format(o, v)
            )
        else:
            exec(
                "self.inst.df[ col ] = (self.inst.df[ c ] - self.inst.df[ v ] ).apply( lambda x : 1 if x {} 0 else 0)".format(o)
            )

        if t == "sell": self.inst.df[col] *= (-1)

        self.col[t].append( col )

    def backtest(self, type = "buy"):

        for t, r in self.reglas.items():
            # Column, Operator, Value
            reglas = self.separar_reglas( r )

            for c, o, v in reglas: self.aplicar( t, c, o, v )

            self.evaluacion()

    def evaluacion(self, period = 1):
        self.inst.df["net"] = self.inst.df[ self.col ].prod(axis = 1).apply(lambda x : 1 if x > 0 else 0) * self.inst.df["Close"].pct_change(periods = period)
        self.inst.df["acc"] = ( self.inst.df["net"] + 1 ).cumprod()

    def optimize(self):
        raise NotImplementedError