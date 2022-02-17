# Aplicacion de estrategias de Analisadores Tecnicos
# A diferencia del archivo procesos.py
# este no se encarga de como tal la formacion de un portafolio de inversiones
# solo basara sus decisiones de acuerdo a las señales de compra venta

# Se generara su clase de simulacion

# No habra clase Bot puesto que la clase Bot de procesos.py puede ser aplicda para este proposito
# donde se entregue como tal la correcta estrategia_filtro
# basado en los resultados que se puedan extraer con esta herramienta


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
        param = tuple( list(map(int, c_aux[1:])) ) 
        col = "{} {} {}".format( c, o, v )

        # Cal(cular analyzador tecnico
        try:
            exec(
                "self.asset.df[ c ] = self.asset.{}{}".format( ta, param )
            )
        except Exception as e:
            raise ValueError( 
                "Execution of : {} , with exception:\n{}".format(
                    "self.asset.df[ c ] = self.asset.{}{}".format( ta, param ),
                    e
                ) 
            )

        based_on = False
        try: 
            v = float(v)
        except: 
            based_on = True

        # Calcular si la regla se cumple en col
        if not based_on:
            exec(
                "self.asset.df[ col ] = self.asset.df[ c ].apply( lambda x : 1 if x {} {} else 0)".format(o, v)
            )
        else:
            exec(
                "self.asset.df[ col ] = (self.asset.df[ c ] - self.asset.df[ v ] ).apply( lambda x : 1 if x {} 0 else 0)".format(o)
            )

        # if t == "sell": self.asset.df[col] *= (-1)

        self.col[t].append( col )


    def apply(self, rule, type):
        rules = self.rule_sep( rule )

        for c, o, v in rules: self.rule_app( type, c, o, v ) 

    def rule_eval(self, periods = None):
        if len( self.rules["buy"]) > 0 and len( self.rules["sell"]) > 0:
            eval = self.rule_eval_all()
        
        else:
            assert periods is not None, "If about to analze buy/sell order, input periods after/before to compute return."

            if len( self.rules["buy"]) > 0:
                eval = self.rule_eval_buy(periods=periods)
            elif len( self.rules["sell"]) > 0:
                eval = self.rule_eval_sell(periods=periods)
            else:
                raise ValueError("No buy or sell orders")
        
        self.asset.df["net"] = self.asset.df[ self.col ].prod(axis = 1).apply(lambda x : 1 if x > 0 else 0) * self.asset.df["close"].pct_change(periods = period)
        self.asset.df["acc"] = ( self.asset.df["net"] + 1 ).cumprod()

        return eval

    def rule_eval_all(self):
        pass

    def rule_eval_buy(self, periods):
        pass

    def rule_eval_sell(self, periods):
        pass

    def evaluate(self, periods  = None):
        for t, rules in self.rules.items():
            for rule in rules:
                self.apply( rule, t )
        
            self.asset.df[t] = self.asset.df[ self.col[t] ].prod(axis = 1)
        
        self.rule_eval(periods=periods)
        
    
    def optimize(self):
        raise NotImplementedError


