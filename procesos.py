
from multiprocessing import Value
import numpy as np
import pandas as pd
import re
import os
import time
import math
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from copy import copy
import json
import matplotlib.pyplot as plt

import multiprocess as mp

# Balanceo
from pypfopt import EfficientFrontier, EfficientSemivariance, EfficientCVaR, EfficientCDaR
from pypfopt import risk_models
from pypfopt import expected_returns
from pypfopt.discrete_allocation import DiscreteAllocation, get_latest_prices
from pypfopt import objective_functions
from pypfopt import plotting

# Riskfolio
import riskfolio.Portfolio as pf
from riskfolio.AuxFunctions import weights_discretizetion

# Binance
from binance.client import Client
from binance.enums import *

from .instrumento import Instrumento, PWD
from .tokens import *
from .instrumentos  import *
from .func_aux import *
from .func_brokers import cantidad_por_sector


def estrategia( i, tiempo, funcion, fin, frecuencia, fiat, broker, desde_api = False, sentimiento = False ):
    """  
        Este tipo de estrategias se encargara de la prediccion de retornos
        del instrumento indicado.

        Se tendra que ingresar una Funcion que tome como parametro un objeto Instrumento
        Este generara el modelo de ML correspondiente, y hara la prediccion a como este lo vea
        conveniente.
            La razon por la que ingresar el Instrumento, es que el tiempo, la ventana de tiempo
            se ira moviendo de acuerdo a la simulacion.
            Haciendolo asi, la funcion a programar no tendra que preocuparse por esto.
    """

    periodo_analisis, intervalo_analisis = re.findall(r'(\d+)(\w+)', frecuencia)[0]
    periodo_analisis = int(periodo_analisis)

    if intervalo_analisis == "m":
        inicio = fin - relativedelta(months = tiempo*periodo_analisis) 
        inicio = inicio.replace(day = 1)
    elif intervalo_analisis == "w":
        inicio = fin - timedelta(days = 7*tiempo*periodo_analisis)
    elif intervalo_analisis == "d":
        inicio = fin - timedelta(days = tiempo*periodo_analisis ) 
    elif intervalo_analisis == "h":
        inicio = fin - timedelta(seconds = 3600*tiempo*periodo_analisis )

    # print(i, inicio, fin, frecuencia, fiat, broker)
    inst = Instrumento( i, inicio, fin, frecuencia = frecuencia, fiat = fiat, broker = broker, desde_api = desde_api, sentimiento = sentimiento)

    if inst.df is None or len(inst.df) <= 3:
        return None

    return funcion(inst)

def optimizacion_portafolio( 
            df, 
            optimizacion, 
            valor_portafolio,
            tiempo_balanceo,
            exp_return = None, 
            return_comp = "mean", 
            risk_comp = "exp", 
            target_return = 0.01, 
            limites = (0,1.0), 
            span = None
    ):
    """  
        exp_return (Series): Serie con los retornos esperados por cada uno de 
                            de los instrumentos en las columnas de df
    """
    if exp_return is not None:
        mu = exp_return

    else:
        mu = {
            "mean":expected_returns.mean_historical_return,
            "ema":expected_returns.ema_historical_return
        }[return_comp](df, 
                    compounding=True, 
                    frequency = tiempo_balanceo)

    s = {
        "exp":risk_models.exp_cov,
        "simple":risk_models.sample_cov
    }[risk_comp](df, frequency = tiempo_balanceo)

    ef = EfficientFrontier(mu, s, weight_bounds=limites)

    try:
        raw_weights = {
            "MaxSharpe":ef.max_sharpe(),
            "MinVol":ef.min_volatility(),
            "EfficientReturn":ef.efficient_return( target_return = target_return )
        }[optimizacion]

        cleaned_weights = ef.clean_weights()
        latest_prices = get_latest_prices(df)

        da = DiscreteAllocation(cleaned_weights, latest_prices, total_portfolio_value=valor_portafolio)
        allocation, leftover = da.lp_portfolio()

    except:
        print("1er Error en el proceso de optimizacion")
        
        # Aqui anteriormente se habia intentado un Greedy Portfolio
        # sin embargo, lanzaba demasiados Tracebacks

        try:

            min_w, max_w = limites

            raw_weights = ef.nonconvex_objective(
                    objective_functions.sharpe_ratio,
                    objective_args=(ef.expected_returns, ef.cov_matrix),
                    constraints=[
                        {"type": "eq", "fun": lambda w: np.sum(w) - 1},  # sum to 1
                        {"type": "ineq", "fun": lambda w: w - min_w},  # greater than min_weight
                        {"type": "ineq", "fun": lambda w: max_w - w},  # less than max_weight
                    ],
                )

            cleaned_weights = ef.clean_weights()
            latest_prices = get_latest_prices(df)

            da = DiscreteAllocation(cleaned_weights, latest_prices, total_portfolio_value=valor_portafolio)
            allocation, leftover = da.lp_portfolio()

        except:
            print("2do Error en el proceso de optimizacion")
            print("Este periodo no tendra un portafolio")
            return None, None

    total_money = 0
    for i in allocation:
        total_money += ( latest_prices[i]*allocation[i] )

    discrete_weights = {}
    for i in allocation:
        discrete_weights[i] = (latest_prices[i]*allocation[i]) / total_money

    return allocation, discrete_weights


class Setter():
    def __init__(self,
        broker,
        fiat = None,
        comision = None,
        instrumentos = None,
        ):
        
        self.broker = broker
        self.comision = COMISION[broker] if comision is None else comision

        # Con property
        self.fiat = fiat
        self.instrumentos = None

    @property
    def instrumentos(self):
        return self._instrumentos
    
    @instrumentos.setter
    def instrumentos(self, value):
        if value is not None:
            assert type(value) in [dict, list], "Instrumetos tiene que ser tipo dict o list, no {}.".format(type(dict))
            self._instrumentos = value
        elif self.broker == "Bitso":
            self._instrumentos = Bitso
        elif self.broker == "Binance":
            self._instrumentos = Binance
        elif self.broker == "GBM":
            self._instrumentos = GBM
        elif self.broker == "Tesis":
            self._instrumentos = Tesis
        else:
            raise ValueError("No hay lista de instrumentos por el nombre {}.".format(value))

    @property
    def fiat(self):
        return self._fiat
    
    @fiat.setter
    def fiat(self, value):
        if value is None:
            if self.broker in ["Tesis", "GBM", "Bitso"]:
                self._fiat = "MXN"
            elif self.broker in ["Binance"]:
                self._fiat = "USDT"

        else:
            self._fiat = value


class Proceso(Setter):
    def __init__(self,
        broker,
        fiat = None,
        comision = None,
        instrumentos = None,
        fin = date.today()
        ):
        super().__init__(broker = broker, 
                        fiat = fiat, 
                        comision = comision,
                        instrumentos=instrumentos
                        )
        
        self.analisis = []

        # Properties
        self.fin = fin

    # Funcion de analisis

    def estrategia(self, fin, desde_api = False, **kwargs):

        # Instrumentos iniciales
        or_instrumentos = copy(self.instrumentos)

        # Diccionario que sera Regresado de la funcion
        # Contendra el nombre del instrumento y su correspondiente valor
        
        for a in self.analisis:
            next_instrumentos = {}
            frecuecia_de_analisis = self.analisis[a].get("frecuencia", self.frecuencia_analisis)

            pool = mp.Pool(mp.cpu_count() // 2)
            r = pool.starmap( 
                    estrategia, 
                    [( 
                        i, 
                        self.analisis[a]["tiempo"], 
                        self.analisis[a]["funcion"], 
                        fin, 
                        frecuecia_de_analisis, 
                        self.fiat, 
                        self.broker, 
                        desde_api, 
                        kwargs.get("sentimiento", False) 
                    ) for i in or_instrumentos ]            
                )
            pool.close()

            next_instrumentos = { inst:valor for inst, valor in zip(or_instrumentos, r) if valor }

            if self.analisis[a]["tipo"] == "analisis":

                # False: Menor a Mayor 
                # True: Mayor a Menor
                n = len(or_instrumentos)
                n = n if "qty" not in self.analisis[a] else math.ceil( n*self.analisis[a]["qty"] )

                next_instrumentos = { k:v for k,v in sorted( 
                                            next_instrumentos.items(), 
                                            key = lambda item: item[1] , 
                                            reverse = True if self.analisis[a]["mejor"] == "mayor" else False 
                                        )[ 0: n ] 
                                    }

            or_instrumentos = copy(next_instrumentos)

        return next_instrumentos # Al fin: or_instrumentos = next_instrumentos

    def preanalisis(
            self, 
            valor_portafolio, 
            pwd = None, 
            min_qty = 0, 
            data = None, 
            **kwargs
        ):
        """  
            Preanalisis se encarga de la lectura de los archivos analisis.
                - Posteriormente se filtran de acuerdo a All, Positivos y Greatest.
                - De los archivos resultantes, se obtienen unicamente aquellos
                    que si se pueden comprar de acuerdo al valor del portafolio
                    y la cantidad minima.
            
            Return data (dict), min_position(float): Acciones resultantes a considerar
                        para el balanceo del portafolio despues de todos los filtros necesarios.
                        Tambien se regresa en porcentaje la posicion minima a tomar, misma que se
                        ocupa para la optimizacion del portafolio.

            
        """

        # Abrimos analisis
        if data is None:
            with open( pwd , "r" ) as fp:
                data = json.load(fp)

        if len(data) ==0: return None, None

        data = self.filtro( data, kwargs.get("filtro_tipo", "All"), **kwargs)

        if len(data) == 0: return None, None

        # Definimos la posicion minima (lower constraint para la optimizacion)

        min_position = min_qty / valor_portafolio

        if min_position > 0:

            n = int(1 // min_position)  - 1 

            if len(data) > n:
                data = sorted( data.items(), 
                                key = lambda item: item[1] , 
                                reverse = True 
                        )[ 0: n ]
                data = { k:v for k,v in data }

        return data, min_position

    def filtro(self, analisis, filtro = "All", **kwargs):
        """  
            filtro_qty = Cantidad a considerar para el filtro de Greatest.
                        En caso de que analisis sea un diccionario con tipos diccionario
                        filtro_qty tambien tiene que ser un diccionario con los diferentes sectores (keys)
                        de analisis.
        """

        tipos = [type(i) for i in analisis.values()]

        if tipos.count(tipos[0]) != len(tipos):
            raise ValueError("La lista de analisis esta compuesta por diferetes tipos de datos: {}".format(tipos))

        tipos = list( set( tipos ) )[0]

        if tipos in [float, int]: 
            return {
                "All":analisis,
                "Positivos":{ i:v for i,v in analisis.items() if v > 0 },
                "Greatest":{k:v for k, v in sorted(analisis.items(), key = lambda item:item[1], reverse = True)[ 0: kwargs.get("filtro_qty", 3)] if v > 0}
            }[filtro]

        elif tipos in [dict]:
            if filtro == "All": aux = analisis
            
            elif filtro == "Positivos":
                aux = {}
                for i, v in analisis.items():
                    aux[i] = { j:k for j, k in v.items() if k > 0}
                
            elif filtro == "Greatest":
                aux = pd.DataFrame()
                for i in analisis:
                    auxx = pd.DataFrame.from_dict( analisis[i], orient="index" ).iloc[ -kwargs["filtro_qty"][i]: ]
                    aux = pd.concat([aux, auxx[ auxx[0] > 0 ]], axis = 0)
                
                aux = aux.to_dict(orient = "index")

                # aux = {}
                # for i, v in analisis.items():
                #     aux[i] = { j:k for j, k in sorted(
                #                                     v.items(), 
                #                                     key = lambda item:item[1], 
                #                                     reverse = True
                #                                 )[ 0: kwargs["cps"][i] ] if k > 0 
                #             }   
                return aux

            auxx = {}
            for i in aux: auxx.update( aux[i] )

            return auxx

        else:
            raise ValueError("No se puede hacer un filtro con tipo {}".format(tipos))

    def _balanceo(
            self, 
            data,
            inicio, 
            fin,
            valor_portafolio,
            metodo = "EfficientFrontier",
            optimizacion = "MaxSharpe",
            exp_return = True,
            dynamic_target = False,
            min_position = 0,
            **kwargs
        ):

        df = pd.DataFrame()

        for i in data:
            inst = Instrumento(i, inicio, fin, frecuencia=self.frecuencia_balanceo, fiat = self.fiat, broker = self.broker, desde_api=False)

            if inst.df is None or len(inst.df) == 0: continue

            df = pd.concat([ df, inst.df["Close"] ], axis = 1)

            df.rename(columns = {"Close":i}, inplace = True)

        if df.isnull().any().any():
            df.interpolate(method = "linear", inplace = True)

            if df.isnull().any().any():
                df.drop(
                    columns = list( df.isnull().any().any()[df.isnull().any().any()].index ),
                    inplace = True
                )
        
        if self.broker in ["Binance", "Bitso"]:
            for i in df.columns: df[i] /= pow(10, self.octetos.get(i, 1))

        if exp_return:
            assert isinstance(data, dict), "Data tiene que ser un tipo diccionario, pero se entrego {}".format(type(data))
            data = pd.DataFrame.from_dict(data, orient = "index")

            try:
                data = data.loc[ df.columns ][0]
            except:
                print(type(data))
                print(data)
                
            if dynamic_target:
                pos = data[ data > 0  ].sort_values( ascending = False ).head( int(1 // min_position) ) 
                kwargs[ "target_return" ] = round( pos.median(), 3 )

        allocation, qty = {}, {}

        try:
            allocation, qty = self.optimizacion_portafolio(
                                                df, 
                                                valor_portafolio = valor_portafolio,
                                                exp_return = data if exp_return else None,  
                                                metodo = metodo,
                                                optimizacion = optimizacion, 
                                                limites = (min_position, 1),
                                                tiempo_testeo = self.tiempo_testeo_balanceo,
                                                **kwargs
                                            )

        except Exception as e:
            print("No se pudo generar un portafolio.\nException: {}".format(e))
            return None, None
        
        if allocation is None or qty is None or len(allocation) == 0 or len(qty) == 0: return None, None

        if self.broker in ["Binance", "Bitso"]:
            qty = { i:(v*10**(self.octetos.get(i, 1))) for i, v in qty.items() }

        return allocation, qty
        
    def optimizacion_portafolio(self,
                df, 
                valor_portafolio,
                exp_return = None, 
                metodo = "EfficientFrontier",
                optimizacion = "MaxSharpe",
                tiempo_testeo = None,
                **kwargs
        ):
        if metodo in ["EfficientFrontier", "EfficientSemivariance", "EfficientCVaR", "EfficientCDaR"]:
            func = self._pyportfolioopt
        else:
            func = self._riskfolio
        
        return func(
                        df,  
                        valor_portafolio,
                        exp_return,  
                        metodo,
                        optimizacion,
                        tiempo_testeo,
                        **kwargs
                    )

    # Funciones de balanceo

    def optimizacion_portafolio(self,
                df, 
                valor_portafolio,
                exp_return = None, 
                metodo = "EfficientFrontier",
                optimizacion = "MaxSharpe",
                tiempo_testeo = None,
                **kwargs
        ):
        if metodo in ["EfficientFrontier", "EfficientSemivariance", "EfficientCVaR", "EfficientCDaR"]:
            func = self.pyportfolioopt
        else:
            func = self.riskfolio
        
        return func(
                        df,  
                        valor_portafolio,
                        exp_return,  
                        metodo,
                        optimizacion,
                        tiempo_testeo,
                        **kwargs
                    )

    def riskfolio(self, 
                df, 
                valor_portafolio,
                exp_return = None, 
                metodo = "MV",
                optimizacion = "Sharpe",
                tiempo_testeo = None,
                **kwargs
        ):
        """  
            Risk measure used, this time will be variance
            The risk measure used to optimze the portfolio. The default is ‘MV’. Posible values are:

                ’MV’: Standard Deviation.
                ’MAD’: Mean Absolute Deviation.
                ’MSV’: Semi Standard Deviation.
                ’FLPM’: First Lower Partial Moment (Omega Ratio).
                ’SLPM’: Second Lower Partial Moment (Sortino Ratio).
                ’CVaR’: Conditional Value at Risk.
                ’EVaR’: Entropic Value at Risk.
                ’WR’: Worst Realization (Minimax)
                ’MDD’: Maximum Drawdown of uncompounded cumulative returns (Calmar Ratio).
                ’ADD’: Average Drawdown of uncompounded cumulative returns.
                ’CDaR’: Conditional Drawdown at Risk of uncompounded cumulative returns.
                ’EDaR’: Entropic Drawdown at Risk of uncompounded cumulative returns.
                ’UCI’: Ulcer Index of uncompounded cumulative returns.

            Objective function, could be MinRisk, MaxRet, Utility or Sharpe
            Objective function of the optimization model. The default is ‘Sharpe’. Posible values are:

                ’MinRisk’: Minimize the selected risk measure.
                ’Utility’: Maximize the Utility function μw−lϕi(w).
                ’Sharpe’: Maximize the risk adjusted return ratio based on the selected risk measure.
                ’MaxRet’: Maximize the expected return of the portfolio.

        """
        
        df = df.replace([np.inf, -np.inf], np.nan).dropna()

        if len(df) < 2:
            return None, None

        latest_price = df.iloc[-1]

        port = pf.Portfolio(returns = df.pct_change(periods = 1).dropna())

        port.assets_stats()

        if exp_return is not None:
            port.mu = exp_return
        
        model = 'Classic' # Could be Classic (historical), BL (Black Litterman) or FM (Factor Model)
        rm = metodo        
        obj = optimizacion

        hist = True # Use historical scenarios for risk measures that depend on scenarios
        rf = 0 # Risk free rate

        l = 2 # Risk aversion factor, only useful when obj is 'Utility'
                # Es el factor de cuanto un inversionista es capaz de aceptar riesgo

        w = port.optimization(model=model, rm=rm, obj=obj, rf=rf, l=l, hist=hist)

        discrete = weights_discretizetion(w, latest_price, valor_portafolio)

        discrete = discrete[0].to_dict()

        total_money = 0
        for i in discrete:
            total_money += ( latest_price[i]*discrete[i] )

        discrete_weights = {}
        for i in discrete:
            discrete_weights[i] = (latest_price[i]*discrete[i]) / total_money

        return w.to_dict(), discrete_weights

    def pyportfolioopt(self, 
                df, 
                valor_portafolio,
                exp_return = None, 
                metodo = "EfficientFrontier",
                optimizacion = "MaxSharpe",
                tiempo_testeo = None,
                **kwargs
        ):
        """  
            exp_return (Series): Serie con los retornos esperados por cada uno de 
                                de los instrumentos en las columnas de df
        """

        if exp_return is not None:
            mu = exp_return

        else:
            mu = {
                "mean":expected_returns.mean_historical_return,
                "ema":expected_returns.ema_historical_return
            }[ kwargs.get("return_comp", "mean") ](  df, 
                                                    compounding=True, 
                                                    frequency = 1 if tiempo_testeo is not None else tiempo_testeo
                                                )
        ef = {
            "EfficientFrontier":self.efficient_frontier,
            "EfficientSemivariance":self.efficient_semivariance,
            "EfficientCVaR":self.efficient_cvar,
            "EfficientCDaR":self.efficient_cdar
        }[ metodo ]( df, mu, optimizacion = optimizacion, tiempo_testeo = tiempo_testeo, **kwargs )

        if ef is None:
            return None, None

        return self.discretizacion( ef, df, valor_portafolio )

    def efficient_frontier(self, df, mu, optimizacion = "MaxSharpe", tiempo_testeo = None, **kwargs):    
        s = {
            "exp":risk_models.exp_cov,
            "simple":risk_models.sample_cov
        }[ kwargs.get("risk_comp", "exp") ](df, frequency = 1 if tiempo_testeo is not None else tiempo_testeo)

        ef = EfficientFrontier(mu, s, weight_bounds = kwargs["limites"], solver = kwargs.get("solver", None) )
        
        try:
            if optimizacion == "MaxSharpe":
                raw_weights = ef.max_sharpe()
            elif optimizacion == "MinVol":
                raw_weights = ef.min_volatility()
            elif optimizacion == "EfficientReturn":
                raw_weights = ef.efficient_return( target_return = kwargs.get("target_return", 0.01) )

        except Exception as e:
            # Meter esto en otro if
            # print("1/N portafolio es probado")
            
            # try:
            #     min_weight, max_weight = kwargs["limites"] if "limites" in kwargs else (0,1)
            #     raw_weights = ef.nonconvex_objective(
            #         objective_functions.sharpe_ratio,
            #         objective_args=(ef.expected_returns, ef.cov_matrix),
            #         constraints=[
            #             {"type": "eq", "fun": lambda w: np.sum(w) - 1},  # sum to 1
            #             {"type": "ineq", "fun": lambda w: w - min_weight},  # greater than min_weight
            #             {"type": "ineq", "fun": lambda w: max_weight - w},  # less than max_weight
            #         ],
            #     )
            # except:


            print("Error con Raw Weights en EfficientFrontier. Exception: {}".format(e))
            return None
        
        if kwargs.get("plotting", False): self.portfolio_plotting(ef = ef, optimizacion = optimizacion, mu = mu, s = s, target_return = kwargs.get("target_return", 0.01))
        
        return ef

    def portfolio_plotting(self, ef, optimizacion, mu, s, target_return = None):

        ef = EfficientFrontier(mu, s, weight_bounds = (0, 1))

        fig, ax = plt.subplots()

        plotting.plot_efficient_frontier(ef, ax=ax, show_assets=True)

        try:
            if optimizacion == "MaxSharpe":
                ef.max_sharpe()
            elif optimizacion == "MinVol":
                ef.min_volatility()
            elif optimizacion == "EfficientReturn":
                ef.efficient_return( target_return = target_return )
        except Exception as e:
            print("Problemas con el objetivo durante el plotting. {}".format(e))
            return 

        ret_tangent, std_tangent, _ = ef.portfolio_performance()
        ax.scatter(std_tangent, ret_tangent, marker="*", s=100, c="r", label=optimizacion)
      
        # Generate random portfolios
        n_samples = 10000
        w = np.random.dirichlet(np.ones(len(mu)), n_samples)
        rets = w.dot(mu)
        stds = np.sqrt(np.diag(w @ s @ w.T))
        sharpes = rets / stds
        ax.scatter(stds, rets, marker=".", c=sharpes, cmap="viridis_r")

        # Output
        ax.set_title("Efficient Frontier with 10,000 random portfolios")
        ax.legend()
        plt.tight_layout()
        plt.savefig( self.pwd_balanceo.format("ef_scatter.png") , dpi=200)
        plt.show()

    def efficient_semivariance(self, df, mu , optimizacion, tiempo_testeo = None, **kwargs):
        h = expected_returns.returns_from_prices(df)

        ef = EfficientSemivariance( mu, h, weight_bounds = kwargs["limites"], solver = kwargs.get("solver", None) )

        try:
            if optimizacion == "MinSemivariance":
                raw_weights = ef.min_semivariance()
            elif optimizacion == "EfficientReturn":
                raw_weights = ef.efficient_return( target_return = kwargs["target_return"] if "target_return" in kwargs else 0.01 )
        except Exception as e:
            print("Error con RawWeights en Efficient Semivariance. Exception: {}".format(e))
            return None

        return ef

    def efficient_cvar(self, df, mu, optimizacion = "MinCVaR", tiempo_testeo = None, **kwargs):

        try:
            h = expected_returns.returns_from_prices(df)
        except Exception as e:
            print("Error con returns_from_prices. Exception: {}".format(e) )

        ef = EfficientCVaR( 
                    mu, 
                    h,
                    beta = kwargs["beta"] if "beta" in kwargs else 0.95,
                    weight_bounds = kwargs["limites"], 
                    solver = kwargs.get("solver", None) 
                    )
        
        try:
            if optimizacion == "MinCVaR":
                raw_weights = ef.min_cvar()
            elif optimizacion == "EfficientReturn":
                raw_weights = ef.efficient_return( target_return = kwargs["target_return"] if "target_return" in kwargs else 0.01 )
        except Exception as e:
            print("Error con RawWeights en Efficient CVaR. Exception: {}".format(e))
            return None

        return ef

    def efficient_cdar(self, df, mu, optimizacion = "MinCDaR", tiempo_testeo = None, **kwargs):

        h = expected_returns.returns_from_prices(df)

        ef = EfficientCDaR( 
                    mu, 
                    h,
                    beta = kwargs["beta"] if "beta" in kwargs else 0.95,
                    weight_bounds = kwargs["limites"], 
                    solver = kwargs.get("solver", None) 
                    )
        
        try:
            if optimizacion == "MinCDaR":
                raw_weights = ef.min_cvar()
            elif optimizacion == "EfficientReturn":
                raw_weights = ef.efficient_return( target_return = kwargs["target_return"] if "target_return" in kwargs else 0.01 )
        except Exception as e:
            print("Error con RawWeights en Efficient CDaR. Exception: {}".format(e))
            return None

        return ef

    def discretizacion(self, ef, df, valor_portafolio):
        """  
            Objeto de frontera eficiente
        """

        latest_prices = get_latest_prices(df)
        cleaned_weights = ef.clean_weights()

        if valor_portafolio > 0:
            try: 
                da = DiscreteAllocation(cleaned_weights, latest_prices, total_portfolio_value=valor_portafolio)
                allocation, leftover = da.lp_portfolio()
            except:
                print("Error discretizacion, se probara un greedy portafolio")

                try:
                    da = DiscreteAllocation(cleaned_weights, latest_prices, total_portfolio_value=valor_portafolio)
                    allocation, leftover = da.greedy_portfolio()
                
                except:
                    print("Error con el greedy portafolio")
                    return None, None
        else:
            allocation = cleaned_weights
            
        total_money = 0
        for i in allocation:
            total_money += ( latest_prices[i]*allocation[i] )

        qty = { i:( v*latest_prices[i] ) for i,v in allocation.items() }

        return allocation, qty

    # Funciones aux
    @property
    def octetos(self):
        if self.broker == "Binance":
            return self.octetos_binance()
        elif self.broker == "Bitso":
            return self.octetos_bitso()
        else:
            raise ValueError("No hay octetos para {}.".format(self.broker))

    def octetos_binance(self):
        """  
            Return: octetos (dict)

            to_buy (list)
        """

        with open(PWD("/Binance/octetos_{}.json".format(self.fiat)), "r") as fp:
            octetos = json.load(fp)

        return octetos

    def octetos_bitso(self):
        return {
            "BTC":8,
            "ETH":8,
            "XRP":6,
            "LTC":8,
            "BCH":8,
            "TUSD":2,
            "BAT":8,
            "DAI":2,
            "MANA":8
        }


class Simulacion(Proceso):
    def __init__(self,
        broker,
        fiat = None,
        fin = date.today(),
        cant_simulaciones = 0,
        instrumentos = None,
        comision = None,
        **kwargs
        ):
        """  

            valor_portafolio (float): Valor en FIAT que vale el portafolio al inicio del periodo
                                        Inversion inicial
            instrumentos (list): Se tienen listas Default en instrumentos.py
                                Si se desean usar otras, integrarlas como lista
            
        """

        # Inicializacion del objecto Proceso
        super().__init__(broker = broker, 
                        fiat = fiat, 
                        comision = comision,
                        instrumentos=instrumentos,
                        fin = fin
                )

        self.cant_simulaciones = cant_simulaciones

        self.pwd = PWD("/{}/Resultados/{}/{}".format( self.broker, self.fiat, "{}" ))

        self.resumen = None

    def analizar(self, frecuencia, tiempo_testeo, analisis, if_save = True, correr_analisis = True, carpeta = None, **kwargs):
        """  
        analisis (dict): Un diccionario con el nombre de la estrategia en cuestion, con sus correspondientes parametros
                            y si es analisis o filtro 
                            Ej para tipos analisis. 
                                { "RSI":{ "tipo":"analisis", "parametros":[14], "mejor":"mayor", "qty":0.2} }
                            
                            tipo: analisis, filtro
                            mejor (solo si tipo = analisis): mayor, menor
                            qty (solo si tipo = analisis) (float): Porcentaje de instrumentos a considerar para la siguiente vuelta
                                                                    Defualt = 1 (100%)
                            
                            Ej para tipos prediccion:
                                { "RF":{"tipo":"prediccion", 
                                        "tiempo":int,
                                        "funcion":Funcion,
                                        "filtro":positivos (all)
                                        } 
                                }

        """
        self.tiempo_analisis = tiempo_testeo
        self.analisis = analisis
        self.frecuencia_analisis = frecuencia
        self.periodo_analisis, self.intervalo_analisis = re.findall(r'(\d+)(\w+)', frecuencia)[0]
        self.periodo_analisis = int( self.periodo_analisis )

        aux_analisis = "_".join( list( analisis.keys() ) )

        # integrar linea de codigo para identificar el tiempo de prediccion
        # en estrategias de prediccion
        aux = []
        for k, v in analisis.items():
            if v["tipo"] == "prediccion" and "tiempo" in v:
                aux.append( [v["tiempo"]] )

            if "parametros" in v:
                if isinstance(v["parametros"], list):
                    aux.append( v["parametros"] )
                if isinstance(v["parametros"], dict):
                    aux.append(  list(v["parametros"].values()) )

            if "frecuencia" in v:
                aux.append([ v["frecuencia"] ])

        # aux = [ v["parametros"] for k, v in analisis.items() if "parametros" in v ]        
        aux_param = "_".join( [ str(item) for s in aux for item in s ] )

        aux = [ v["mejor"] for k, v in analisis.items() if "mejor" in v]
        aux_mejor = "_".join( aux )

        if carpeta is None:
            self.pwd_analisis = self.pwd.format( "{}_{}/{}/{}_{}".format( frecuencia, tiempo_testeo, aux_analisis, aux_param, aux_mejor ) )
        else:
            self.pwd_analisis = self.pwd.format( "{}_{}/{}/{}_{}/{}".format( frecuencia, tiempo_testeo, aux_analisis, aux_param, aux_mejor, carpeta ) )

        creacion_carpeta(self.pwd_analisis)
        
        self.pwd_analisis += "/{}"

        if self.intervalo_analisis == "m":
            self.inicio = self.fin - relativedelta(months = self.cant_simulaciones - 1)
            self.inicio = self.inicio.replace(day = 1)
        elif self.intervalo_analisis == "w":
            self.inicio = self.fin - timedelta(days = 7*self.cant_simulaciones*self.periodo_analisis*tiempo_testeo)
        elif self.intervalo_analisis == "d":
            self.inicio = self.fin - timedelta(days = self.cant_simulaciones*self.periodo_analisis*tiempo_testeo)
        elif self.intervalo_analisis == "h":
            self.fin = datetime.combine( self.fin, datetime.min.time() )
            self.inicio = self.fin - timedelta(seconds = 3600*self.cant_simulaciones*self.periodo_analisis*tiempo_testeo)            

        if correr_analisis:
            self._analizar_(tiempo_testeo = tiempo_testeo, if_save = if_save, **kwargs)

    def _analizar_(self, tiempo_testeo, if_save = True, **kwargs):
        
        for simulacion in range(self.cant_simulaciones):

            if self.intervalo_analisis == "m":
                inicio = self.inicio + relativedelta(months = simulacion*self.periodo_analisis*tiempo_testeo)
                inicio = inicio.replace(day = 1)

                fin = self.inicio + relativedelta(months = (simulacion+1)*self.periodo_analisis*tiempo_testeo)
                fin -= timedelta(days = 1)

                fin_analisis = inicio - timedelta(days = 1)
                # inicio_analisis = fin_analisis - relativedelta( months = tiempo_testeo*self.periodo_analisis )
            
            elif self.intervalo_analisis == "w":
                inicio = self.inicio + timedelta(days = 7*simulacion*tiempo_testeo*self.periodo_analisis)
                fin = inicio + timedelta(days = 7*tiempo_testeo*self.periodo_analisis)
                fin_analisis = inicio

            elif self.intervalo_analisis == "d":
                inicio = self.inicio + timedelta( days = simulacion*tiempo_testeo*self.periodo_analisis )
                fin = inicio + timedelta(days = tiempo_testeo*self.periodo_analisis)
                fin_analisis = inicio

            elif self.intervalo_analisis == "h":
                inicio = self.inicio + timedelta( seconds = simulacion*tiempo_testeo*self.periodo_analisis*3600 )
                fin = inicio + timedelta( seconds = tiempo_testeo*self.periodo_analisis*3600 ) 
                fin_analisis = inicio

            print(inicio, fin)

            resultados = self.estrategia( fin_analisis , **kwargs)

            if if_save:
                with open( self.pwd_analisis.format( "{}_{}_analisis.json".format(  inicio  ,   fin   ) ), "w" ) as fp:
                    json.dump( resultados, fp )

    def balanceo(self,  
                tiempo_balanceo,
                valor_portafolio = 0,
                min_qty = 0,
                metodo = "EfficientFrontier",
                optimizacion = "MaxSharpe",
                if_save = True,
                correr_analisis = True,
                exp_return = False,
                preanalisis = True,
                dropdown = None,
                dynamic_target = False,
                sobreescribir = True,
                **kwargs
        ):
        """  
            factor_reduccion (float): Del valor del portafolio, cuanto realmente considerar para las posiciones minimas
                                    Default = 0.95
        """

        assert not( exp_return != dynamic_target ), "Si dynamic_target entonces debe ser exp_return."

        self.tiempo_testeo_balanceo = kwargs.get("tiempo_testeo", self.tiempo_analisis)
        self.frecuencia_balanceo = kwargs.get("frecuencia", self.frecuencia_analisis)

        aux = "{}_{}/{}_{}_{}".format(kwargs.get("filtro_tipo", "All"), metodo, optimizacion, self.frecuencia_balanceo, tiempo_balanceo )

        if optimizacion == "EfficientReturn":
            aux += ( "_" + str(  kwargs["target_return"] if not dynamic_target else "dynamictarget"  ) )
        
        if dropdown is not None: 
            aux += ( "_dropdown{}".format(dropdown)  )

        self.pwd_balanceo = self.pwd_analisis.format( aux )

        creacion_carpeta( self.pwd_balanceo )

        self.pwd_balanceo += "/{}"

        if correr_analisis:
            if sobreescribir or not os.path.isfile( self.pwd_balanceo.format("resumen.csv") ):
                self._balanceo_(
                    tiempo_balanceo = tiempo_balanceo,
                    valor_portafolio = valor_portafolio,
                    min_qty = min_qty,
                    metodo = metodo,
                    optimizacion = optimizacion,
                    if_save = if_save,
                    exp_return = exp_return,
                    preanalisis = preanalisis,
                    dropdown = dropdown,
                    dynamic_target = dynamic_target,
                    **kwargs
                )
    
    def _balanceo_(
            self, 
            tiempo_balanceo,
            valor_portafolio = 0,
            min_qty = 0,
            metodo = "EfficientFrontier",
            optimizacion = "MaxSharpe",
            if_save = True,
            exp_return = False,
            preanalisis = True,
            dropdown = None,
            dynamic_target = False,
            **kwargs
        ):

        # Variables finales para el testeo
        acumulado = 1
        self.df = []

        periodo_balanceo, intervalo_balanceo = re.findall(r'(\d+)(\w+)', self.frecuencia_balanceo)[0]
        periodo_balanceo = int( periodo_balanceo )

        if self.broker in ["Tesis", "GBM"] and kwargs.get("filtro_tipo", "All") == "Greatest": 
            cps = cantidad_por_sector(self.instrumentos, porcentaje=True)
        else:
            cps = {}
        
        # Esto es solo para intervalo weekly
        mas = 1 if self.broker == "Tesis" else 0

        for simulacion in range(self.cant_simulaciones):

            if intervalo_balanceo == "m":
                inicio = self.inicio + relativedelta(months = simulacion*periodo_balanceo*self.tiempo_testeo_balanceo)
                inicio = inicio.replace(day = 1)

                fin = self.inicio + relativedelta(months = (simulacion+1)*periodo_balanceo*self.tiempo_testeo_balanceo)
                fin -= timedelta(days = 1)

                fin_analisis = inicio - timedelta(days = 1)
                inicio_analisis = fin_analisis - relativedelta( months = tiempo_balanceo*periodo_balanceo )

            # Se puede crear otra funcion para que este if entre solo con Tesis
            elif intervalo_balanceo == "w":
                inicio = self.inicio + timedelta(days = 7*simulacion*self.tiempo_testeo_balanceo*periodo_balanceo )
                fin = inicio + timedelta(days = 7*self.tiempo_testeo_balanceo*periodo_balanceo - mas)
                fin_analisis = inicio
                inicio_analisis = fin_analisis - timedelta(days = 7*tiempo_balanceo*periodo_balanceo)

            elif intervalo_balanceo == "d":
                inicio = self.inicio + timedelta( days = simulacion*self.tiempo_testeo_balanceo*periodo_balanceo )
                fin = inicio + timedelta(days = self.tiempo_testeo_balanceo*periodo_balanceo)
                fin_analisis = inicio
                inicio_analisis = fin_analisis - timedelta(days = tiempo_balanceo*periodo_balanceo)

            elif intervalo_balanceo == "h":
                inicio = self.inicio + timedelta( seconds = simulacion*self.tiempo_testeo_balanceo*periodo_balanceo*3600 )
                fin = inicio + timedelta( seconds = self.tiempo_testeo_balanceo*periodo_balanceo*3600 ) 
                fin_analisis = inicio
                inicio_analisis = fin_analisis - timedelta(seconds = tiempo_balanceo*periodo_balanceo*3600)

            print(inicio, fin)

            # If leer algun input como Pre-Analisis
            # Mandar en esta funcion toda la correspondiente manipuacion de data
            if preanalisis:
                data, min_position = self.preanalisis(
                                            pwd = self.pwd_analisis.format( "{}_{}_analisis.json".format(inicio, fin)),
                                            valor_portafolio = valor_portafolio, 
                                            min_qty = min_qty, 
                                            cps = cps, 
                                            **kwargs
                                    )
            else:
                data = self.instrumentos
                min_position = 0

            if data is None: continue 

            allocation, qty = self._balanceo(
                data = data,
                inicio = inicio_analisis,
                fin = fin_analisis,
                valor_portafolio = valor_portafolio,
                metodo = metodo,
                optimizacion = optimizacion,
                exp_return = exp_return,
                dynamic_target = dynamic_target,
                min_position = min_position,
                **kwargs
            )            

            if allocation is None or qty is None or len(allocation) == 0 or len(qty) == 0: continue

            if if_save:
                with open( self.pwd_balanceo.format( str(inicio) + "_" + str(fin) + "_allocation.json" ), "w" ) as fp:
                    json.dump( 
                        {"allocation":allocation, "qty":qty}, 
                        fp 
                    )

            # Testeo
            total_return = self.test( allocation, 
                                        inicio, 
                                        fin, 
                                        kwargs.get("frecuencia_testeo", "1d"),
                                        verbose = kwargs.get("testeo_print", False),
                                        dropdown = dropdown,
                                        **kwargs
                            )

            acumulado *= ( total_return + 1 )

            valor_portafolio *= ( total_return + 1 )
            self.df.append([
                inicio, fin, total_return, acumulado, valor_portafolio
            ])

    
        self.df = pd.DataFrame(
                data = self.df,
                columns = ["inicio", "fin", "net", "acc", "valor_portafolio"]
            )

        self.df["fin"] = pd.to_datetime( self.df["fin"] )
        self.df.set_index("fin", inplace = True)

        self.df.to_csv( self.pwd_balanceo.format( "resumen.csv" ) )

    def test(self, allocation, inicio, fin, frecuencia, verbose = False, dropdown = None,**kwargs):
        """  
            dropdown (float): Procentaje limite de caida para vender antes de tiempo
        """

        total_return = 0

        if self.broker == "Tesis" and self.intervalo_analisis == "w":
            dia = "Open"
        else: 
            dia = "Close"

        for i, v in allocation.items():
            inst = Instrumento(i, inicio, fin, frecuencia=frecuencia, fiat = self.fiat, broker = self.broker, desde_api=False)

            if inst.df is None or len(inst.df) == 0: continue

            if dropdown is not None:
                first = inst.df.iloc[0][dia]
                inst.df["dropdown"] = inst.df["Close"].apply(lambda x: x/first - 1)

                if len( inst.df[ inst.df["dropdown"] < -dropdown ] ) > 0:
                    first = inst.df[ inst.df["dropdown"] < -dropdown ].index[0]

                    aux = ( (inst.df["Close"].loc[first]*(1 - self.comision)) / (inst.df[dia].iloc[0]*(1 + self.comision))  ) - 1
                else: 
                    aux = ( (inst.df["Close"].iloc[-1]*(1 - self.comision)) / (inst.df[dia].iloc[0]*(1 + self.comision))  ) - 1
                
            else:
                aux = ( (inst.df["Close"].iloc[-1]*(1 - self.comision)) / (inst.df[dia].iloc[0]*(1 + self.comision))  ) - 1

            if verbose: print( "Retorno para {} de {}%, dando un peso al portafolio de {}".format( i, aux*100, aux*100*v ) )

            total_return += (aux * v)
        
        return total_return

    @property
    def resumen(self):
        if not hasattr(self, "_resumen"):
            if not hasattr(self, "_df"):
                try:
                    self.df = pd.read_csv( self.pwd_balanceo.format("resumen.csv") )
                    # self.df.drop(columns = ["Unnamed: 0"], inplace = True)
                    self.df.set_index("fin", inplace = True)
                    self.df.index = pd.to_datetime( self.df.index )
                except:
                    raise ValueError("Todavia no hay una analisis con dichos parametros.")
                
            self._resumen = {
                "Neto Promedio":self.df["net"].mean(),
                "Neto Std": self.df["net"].std(),
                "Sharpe":self.df["net"].mean()/self.df["net"].std(),
                "Sortino":self.df["net"].mean()/ self.df[self.df["net"] <= 0 ]["net"].std() ,
                "Max Drawdonw":self.df["net"].min(),
                "Acc":self.df["acc"].iloc[-1],
                "Valor portafolio":self.df["valor_portafolio"].iloc[-1],
                "Al punto max":(self.df["valor_portafolio"].iloc[-1] / self.df["acc"].max()) - 1
            }
            
            return self._resumen

        else:
            return self._resumen

    @resumen.setter
    def resumen(self, value):
        self._resumen = value
    
    def recopilador_resultados(self, path = None):
        path = path if path is not None else PWD( "/{}/Resultados/{}/{}_{}".format( self.broker, self.fiat, self.frecuencia_analisis, self.tiempo_analisis ) )

        dicc = pd.DataFrame.from_dict( bring_results(path) , orient="index").reset_index().rename(columns = {"index":"route"})

        return dicc.sort_values(by = "acc", ascending=False).reset_index(drop = True)

    def comportamiento(self, route):
        assert route, "Se necesita una ruta de donde obtener el comportamiento atraves de tiempo de la estrategia de interes."

        route = route if "resumen.csv" in route else ( route + "/resumen.csv" )

        try:
            df = pd.read_csv( route )
        except:
            print("No hay un archivo resumen en la ruta {}".format(route))
            return None
        
        if "Unnamed: 0" in df.columns:
            df.drop(columns = ["Unnamed: 0"], inplace = True)
        
        df.set_index("fin", inplace = True)
        df.index = pd.to_datetime( df.index ) 

        return df


class Bot(Proceso):
    def __init__(self, 
        broker, 
        fiat = None,
        instrumentos = None,
        comision = None,
        fin = date.today()
        ):

        # Inicializacion del objecto Proceso
        super().__init__(broker = broker, 
                        fiat = fiat, 
                        comision = comision,
                        instrumentos=instrumentos,
                        fin = fin
                )

        self.pwd = PWD("/{}/Transacciones".format( self.broker ))

    def api(self):
        
        if self.broker == "Binance":
            try:
                api = Client(BINANCE_API_KEY, BINANCE_API_SECRETE)
            except:
                raise Exception("Problemas Cliente Binance")
    
        return api
    
    def analizar(self, frecuencia, analisis, desde_api = True):
        self.analisis = analisis
        self.frecuencia_analisis = frecuencia
        self.periodo_analisis, self.intervalo_analisis = re.findall(r'(\d+)(\w+)', frecuencia)[0]
        self.periodo_analisis = int( self.periodo_analisis )
        
        aux_analisis = "_".join( list( analisis.keys() ) )
        aux = [ v["parametros"] for k, v in analisis.items() if "parametros" in v ]
        aux_param = "_".join( [ str(item) for s in aux for item in s ] )

        aux = [ v["mejor"] for k, v in analisis.items() if "mejor" in v]
        aux_mejor = "_".join( aux )


        self.pwd_bot = self.pwd +  "/{}_{}_{}_{}_{}.json".format(self.fin, frecuencia, aux_analisis, aux_param, aux_mejor  ) 

        return self._estrategia( self.fin , desde_api = desde_api)
    
    def balanceo(self, 
            tiempo_balanceo,
            valor_portafolio,
            min_qty = 0,
            data = None,
            metodo = "EfficientFrontier",
            optimizacion = "MaxSharpe",
            exp_return = False,
            dynamic_return = False,
            **kwargs
        ):

        self.min_qty = min_qty
        self.tiempo_testeo_balanceo = kwargs.get("tiempo_testeo", self.tiempo_analisis)
        self.frecuencia_balanceo = kwargs.get("frecuencia", self.frecuencia_analisis)

        periodo_balanceo, intervalo_balanceo = re.findall(r'(\d+)(\w+)', self.frecuencia_balanceo)[0]
        periodo_balanceo = int( periodo_balanceo )

        if intervalo_balanceo == "d":
            inicio_analisis = self.fin - timedelta(days = tiempo_balanceo*periodo_balanceo)
        elif intervalo_balanceo == "h":
            inicio_analisis = self.fin - timedelta(days = tiempo_balanceo*periodo_balanceo*3600)
        elif intervalo_balanceo == "m":
            inicio_analisis = self.fin - relativedelta(months = tiempo_balanceo*periodo_balanceo)

        if data is not None:
            data, min_position = self.preanalisis(
                                            data = data,
                                            valor_portafolio = valor_portafolio, 
                                            min_qty = min_qty, 
                                            **kwargs
                                    )
        else:
            # De esta manera si no hay informacion de la que partir
            # Usara todos los instrumentos de este broker, para posteriormente buscar descargarlos
            assert min_qty == 0, "Si no se introduce informacion de los instrumentos (predicciones/analisis), el balanceo requiere min_qty = 0."
            min_position = 0
            data = self.instrumentos

        return self._balanceo(
            data = data,
            inicio = inicio_analisis,
            fin = self.fin,
            valor_portafolio = valor_portafolio,
            metodo = metodo,
            optimizacion = optimizacion,
            exp_return = exp_return,
            dynamic_return = dynamic_return,
            min_position = min_position
        )

    def posiciones_abiertas(self, verbose = True):
        """ 
            Lectura de archivos Json para ver que instrumentos ya se han comprado 
            El funcionamiento de esta, no debe depender de las estrategias usadas
            si no del tiempo en que fueron realizadas (fecha en el nombre del archivo)

            Tambien indicara, deacuerdo al analisis, quien debera venderse.
        """

        # Buscamos por archivos JSON
        json_files = [j for j in os.listdir( self.pwd ) if j.endswith('.json')]

        if len(json_files) == 0:
            return {
                "discrete":{},
                "percentage":{},
                "qty":{}
            }

        # Ordenamos de acuerdo a la fecha
        # Del menor al mayor, por lo que el ultimo es el que nos interesa
        json_files_order = [i.split("_")[0] for i in json_files]
        json_files_order.sort(key = lambda date: datetime.strptime(date, '%Y-%m-%d')) 

        # Obtenemos nombre del archivo que nos interesa
        json_files = [i for i in json_files if json_files_order[-1] in i]

        if verbose:
            print("El archivo a revisar es:", json_files[0])
        
        with open( self.pwd + "/" + json_files[0], 'r') as fp:
            json_files = json.load(fp)

        if verbose:
            print("Con cryptos:", list(json_files["discrete"].keys()))

        return json_files

    def posiciones_por_cerrar(self, analisis, posiciones_abiertas, if_print = True):
        """  
            Return: to_sell (dict), no_sell (dict)

            analisis (dict): Diccionario con los intrumentos a considerar
            posiciones_abiertas (dict): Diccionario con las posiciones que se abrieron el periodo anterior


        """
        if posiciones_abiertas is None:
            return set()

        if analisis is None:
            return set(analisis.keys())

        to_sell = set(posiciones_abiertas['discrete'].keys()) - set(analisis.keys())

        if if_print:
            print("Solo se venderan:", to_sell)

        return { i: v for i, v in posiciones_abiertas if i in to_sell }
        
    def vender(self, to_sell):
        if self.broker == "Binance":
            no_sell =  self.vender_binance(to_sell)
        elif self.broker == "Bitso":
            no_sell =  self.vender_bitso(to_sell)
        
        return no_sell

    def vender_binance(self, to_sell):
        """  
            Return: no_vendidas (list)

            De acuerdo al analisis y a lo que se tiene, se mandaran las ordenes de venta.

            (4/6/21) Que pasara si se complen N cantida de ciclos while y la orden no se cierra?
                    Se ciclara?
                    Se debera de cancelar dicha orden?

        """
        
        # Estas lineas de codigo deberan de mandarse llamar cada que se quiera interactuar 
        # con la API, pues despues la sesion se puede terminar
        api = self.api()

        ordenes = {}
        no_vendidas = []

        for k in list(to_sell):
            cr = k + self.fiat
            print("Orden de Venta:", cr, "Cantidad:", to_sell['discrete'][k])

            # Nos aseguramos de tener en nuestra cuenta dicha crypto
            asset_balance = float(api.get_asset_balance(asset=k)['free'])

            if asset_balance == 0:
                print("No hay", k, "en la cuenta")
                no_vendidas.append(cr)
                continue
            elif asset_balance < (to_sell['discrete'][k]*0.9):
                print("La cuenta cuenta con una cantidad de ",cr,"considerablemente inferior a la supuesta")
                no_vendidas.append(cr)
                continue

            # A este punto se sabe que la cuenta tiene la informacion necesario
            # Se asegura primero que lo que haya en la cuenta X precio > 0.0001
            aux = {
                "BTC":0.0001,
                "USDT":1,                   # Este valor falta configurarlos correctamente (4/06/21)
            }
            if asset_balance*float(api.get_symbol_ticker(symbol = cr)['price']) < aux[self.fiat]:
                print("El valor de la cuenta con {} es menor a {} {} por lo que no puede ser vendida".format( cr, aux[self.fiat], self.fiat ))
                no_vendidas.append(cr)
                continue

            # Ahora hay que redondear el numero a los decimales especificados
            # por la cryptomoneda
            asset_info = api.get_symbol_info(symbol=cr)['filters']
            asset_info = [i for i in asset_info if i['filterType'] == 'LOT_SIZE'][0]
            decimals = float( asset_info['stepSize'] )

            if int(decimals) == 0:
                decimals = str(decimals)
                decimals = decimals[::-1].find('.')
                asset_balance = math.floor( asset_balance * pow(10, int(decimals)) ) / pow(10, int(decimals))
            elif int(decimals) != 0:
                asset_balance = math.floor(asset_balance)

            if asset_balance*float(api.get_symbol_ticker( symbol = cr )['price']) <= aux[self.fiat]:
                print("{} no podra ser vendido debido a que es menor que {} {}".format( cr, aux[self.fiat], self.fiat ))
                no_vendidas.append(cr)
                continue

            # Guardar la orden
            ordenes[cr] = api.order_market_sell(
                symbol = cr,
                quantity = asset_balance
            )

            print("Real cantidad vendida:", asset_balance)

            # Esperamos un segundo para evitar que el sistema se sobrecargue
            # de ordenes
            time.sleep(1)

        # Generamos otro ciclo para ver que las ordenes ya se hayan completado
        for c in ordenes:
            oo = api.get_open_orders(symbol = c)

            # Tenemos que hacer un ciclo hasta 
            # que la venta haya sido completada
            while True:
                # Se asume que para el siguiente ciclo ya se cerro
                close = True

                # Ordenes en las ordenes abiertas
                for o in oo:
                    if ordenes[c]['orderId'] == o['orderId']:
                        close = False
                        break

                if close:
                    print("La orden de venta para", c, "ya se lleno")
                    break
                else:
                    print("La orden de venta para", c, "no se ha llenado")
                    # Esperamos 5 segundos para volver a checar si la orden ya se lleno
                    time.sleep(5)

            # Esperamos 1 segundos antes de checar la siguiente moneda y 
            # y evitar que el sistema se sobrecargue
            time.sleep(1)

        return no_vendidas

    def vender_bitso(self, to_sell):
        pass

    @property
    def dinero(self):
        if hasattr(self, "_dinero"):
            return self._dinero
        
        elif self.broker == "Binance":
            self._dinero =  self.dinero_binance()

        elif self.broker == "Bitso":
            self._dinero =  self.dinero_bitso()
        
        return self._dinero
    
    @dinero.setter
    def dinero(self, value):
        try:
            value = float(value)
        except:
            raise ValueError("Dinero tiene que ser un tipo int, float o str(int, float). Se entrego tipo: {}".format( type(value)) )
    
        self._dinero = value

    def dinero_binance(self):
        api = self.api()

        return float(api.get_asset_balance(asset = self.fiat)['free'])

    def dinero_bitso(self):
        pass

    @property
    def valor_portafolio(self):
        if hasattr(self, "_valor_portafolio"):
            return self._valor_portafolio
        elif self.broker == "Binance":
            self._valor_portafolio = self.valor_portafolio_binance()
        elif self.broker == "Bitso":
            self._valor_portafolio = self.valor_portafolio_bitso()
        
        return self._valor_portafolio
    
    @valor_portafolio.setter
    def valor_portafolio(self, value):
        try:
            value = float(value)
        except:
            raise ValueError("Valor portafolio tiene que ser un tipo int, float o str(int, float). Se entrego tipo: {}".format( type(value)) )
    
        self._valor_portafolio = value
    
    def valor_portafolio_binance(self):
        api = self.api()

        aux = api.get_account()["balances"]

        monedas = { i["asset"]:i["free"] for i in aux if float( i["free"] ) > 0 }
        # for i in aux:
        #     if float(i['free']) > 0:
        #         monedas[i['asset']] = i['free']

        valor_portafolio = 0
        for k, v in monedas.items():
            if k == self.fiat:
                valor_portafolio += float(v)
            else:
                try:
                    aux = float(v)*float(api.get_symbol_ticker( symbol = k + self.fiat )['price'])
                    valor_portafolio += aux
                except:
                    continue

            time.sleep(0.5)
        
        return valor_portafolio

    def valor_portafolio_bitso(self):
        pass

    def posiciones_por_abrir(self, analisis, posiciones_abiertas):
        return set(analisis.keys()) - set(posiciones_abiertas['discrete'].keys())

    def comprar(self, allocation):
        """  
            Antes de comprar, verificara que tanto es la diferencia de la nueva allocation
            con la anterior, para asi evitar cambios pequeños con grandes problemas debido a las
            comisiones y ventas/compras minimas

            La diferencia con el allocation que debe ser ingresado en esta funcion
            es que debe ser el discrete_weights * Money, con el objetivo de saber cuanto dinero en verdad
            se dedicara a cada una de ellas
        """
        allocation = { i:round( v, self.octetos[i] ) for i, v in allocation.items() }

        if self.broker == "Binance":
            return self.comprar_binance(allocation)
        elif self.broker == "Bitso":
            return self.comprar_bitso(allocation)

    def comprar_binance(self, allocation):
        not_to_consider = []

        # for i, v in allocation.items():

        #     if v < self.min_qty:
        #         print("{} con una asignacion de {} es menor que el {} requerido para generar la transaccion, por lo que no se procedera".format( i, v, self.min_qty ))
        #         not_to_consider.append( i )
        #         continue

        for i in not_to_consider: del allocation[i]
        
        if len(allocation) == 0: return None

        api = self.api()

        aux = {}
        real_end_allocation = {}

        for k,v in allocation.items():
            cr = k + self.fiat
            try:
                aux[cr] = api.order_market_buy(
                    symbol = cr,
                    quantity = v
                )
                real_end_allocation[cr] = v
            except:
                aux[cr] = api.order_market_buy(
                    symbol = cr,
                    quantity = v-1
                )

                real_end_allocation[cr] = v-1
                
            time.sleep(1)

        # Generamos otro ciclo para ver que las ordenes ya se hayan completado
        for c in aux:
            oo = api.get_open_orders(symbol = c)

            # Tenemos que hacer un ciclo hasta 
            # que la venta haya sido completada
            while True:
                # Se asume que para el siguiente ciclo ya se cerro
                close = True

                # Ordenes en las ordenes abiertas
                for o in oo:
                    if aux[c]['orderId'] == o['orderId']:
                        close = False
                        break

                if close:
                    print("La orden de compra para", c, "ya se lleno")
                    break
                else:
                    print("La orden de compra para", c, "no se ha llenado")
                    # Esperamos 5 segundos para volver a checar si la orden ya se lleno
                    time.sleep(5)

            # Esperamos 1 segundos antes de checar la siguiente moneda y 
            # y evitar que el sistema se sobrecargue
            time.sleep(1)

        return real_end_allocation

    def comprar_bitso(self):
        pass

    def resumen(self):

        pass

    def run(self, frecuencia, analisis):
        """  
            Funcion que correra con ciertos parametros Default todos
            los pasos correspondientes
        """
        
        analisis = self.analizar(
            frecuencia=frecuencia,
            analisis=analisis
        )   

        pa = self.posiciones_abiertas()

        ppc = self.posiciones_por_cerrar(analisis, pa)

        no_sell = self.vender(ppc)

        no_sell += ( list( set( pa ) ) - list( set( ppc ) ) )
        no_sell = { i:v for i,v in pa if i in no_sell }

        

