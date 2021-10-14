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

from .instrumentos import *
from .tokens import BROKERS

class Estrategia():

    def __init__(self, broker, frecuencia = None, asset = None):
        """  
            asset (str): Asset con el cual trabajar
                        Default = None, Se escoge uno random de la lista de instrumentos del correspondiente broker
        """


        assert broker in BROKERS, "broker no esta en lista brokers {}".format( BROKERS )
        self.broker = broker

        self.frecuencia

        self.asset = asset
    
    @property
    def asset(self):
        return self._asset
    
    @asset.setter
    def asset(self, value):
        if value is None:
            pass