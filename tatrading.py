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
import random
import copy

from instrumento import Instrumento

from .procesos import Setter
from .instrumentos import *
from .tokens import BROKERS

class Estrategia():
    def __init__(
            self, 
            inst,
            reglas = [],
            **kwargs
        ):
        """  
            asset (str): Asset con el cual trabajar
                        Default = None, Se escoge uno random de la lista de instrumentos del correspondiente broker
        """

        self.reglas = reglas
        self.inst = inst

        self.broker = inst.broker
        self.fiat = inst.fiat
        self.comision = inst.comision


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
        regla = regla.split(" ")
        return regla[0], regla[1], regla[2]

    def backtest(self):
        df = copy( self.inst.df )

        for r in self.reglas:
            # Column, Operator, Value
            c, o, v = self.separar_reglas( r )

            