# Aplicacion de estrategias de Analisadores Tecnicos
# A diferencia del archivo procesos.py
# este no se encarga de como tal la formacion de un portafolio de inversiones
# solo basara sus decisiones de acuerdo a las señales de compra venta

# Se generara su clase de simulacion

# No habra clase Bot puesto que la clase Bot de procesos.py puede ser aplicda para este proposito
# donde se entregue como tal la correcta estrategia_filtro
# basado en los resultados que se puedan extraer con esta herramienta

import numpy as np
from numpy.lib.arraysetops import isin
import pandas as pd

class Strategy():
    def __init__(
            self,
            asset,
            rules = {}
        ):
        """  
            Technical Analysi / Sentiment Analysis strategy tester on individual assets
        """

        self.rules = rules
        self.asset = asset

        self.col = { "buy":[], "sell":[] }

    @property
    def rules(self):
        return self._rules
    
    @rules.setter
    def rules(self, value):
        assert isinstance(value, dict), "Rules is nor a dictionary, a {} was delivered".format(type(value))
        assert ( "buy" in value and "sell" in value ), "Dictionary must tell the buy and sell rules"
        self._rules = value
    
    @property
    def asset(self):
        return self._asset
    
    @asset.setter
    def asset(self, value):
        from .assets import Asset
        assert isinstance(value, Asset), "asset is not type Asset. It is {}".format( type(value) )
        self._asset = value

    def rule_sep(self, rule):
        by_ands = rule.split(" AND ")
        
        rule = []
        for i in by_ands:
            r = i.split(" ")
            
            rule.append( ( r[0], r[1], r[2] ) )
        
        return rule
    
    def rule_app(self, t, c, o, v):
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

    def rule_eval(self, period = 1):
        self.inst.df["net"] = self.inst.df[ self.col ].prod(axis = 1).apply(lambda x : 1 if x > 0 else 0) * self.inst.df["Close"].pct_change(periods = period)
        self.inst.df["acc"] = ( self.inst.df["net"] + 1 ).cumprod()

    def apply(self, rule, type):
        rules = self.rule_sep( rule )

        for c, o, v in rules: self.rule_app( type, c, o, v ) 

        self.rule_eval()

    def evaluate(self):
        for t in [ "buy", "sell"]:
            for r in self.rules[ t ]:
                self.apply( r, t )
    
    def optimize(self):
        raise NotImplementedError


