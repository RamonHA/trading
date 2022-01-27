# -*- coding: utf-8 -*-

# Librerias generales
from copy import copy
import pandas as pd
import numpy as np
from datetime import datetime
import time
import yfinance as yf

# Asset
import ta

# Google Trends
from pytrends import dailydata
from pytrends.request import TrendReq
from trading.func_aux import *

# Timeseries + statsmodels
from statsmodels.tsa.stattools import kpss, adfuller
from statsmodels.stats.stattools import durbin_watson
from statsmodels.tsa.api import VAR
from statsmodels.tsa.stattools import grangercausalitytests
import statsmodels.api as sm

class TimeSeries():
    """ Clase Time Series 
        Esta clase permite definir aquellas variables que sean TimeSeries, y las dota
        de caracteristicas estadisticas, etc.
    """
    def __init__(self, df = None):
        
        if df is not None:
            self.df = df

    # def __repr__(self):
    #     return '{}: {}'.format(type(self).__name__,  self.symbol_aux )

    @property
    def df(self):
        return self._df
    
    @df.setter
    def df(self, value):
        # Here there will be a preprocessing
        assert (value is not None and isinstance( value, pd.DataFrame )), "Values is either None or is not pandas DataFrame"
        self._df = value

    def ensure_df(self, df):
        assert ( 
            df, hasattr(self, "_df") or hasattr(self, "_asset") 
        ), "Requiered a df"
        
        if df is not None: self.df = df

        # All statistic procedures requiered no inf or nan values
        # here assertions will come out
        self.df = self.df.replace([np.inf, -np.inf], np.nan).dropna()

    # Propiedades de yahoo finanzas
    @property
    def yf(self):
        if hasattr( self, "_yf" ):
            return self._yf
        else:
            self.yf = yf.Ticker( self.symbol )
            return self._yf
    
    @yf.setter
    def yf(self, value):
        self._yf = value
    
    # Statistics
    def _ur_adf(self, df, regression = "c"):
        return [
            adfuller(  
                df[i], regression = regression
            ) for i in df.columns 
        ]

    def _ur_kpss(self, df, regression = "c"):
        return [
            kpss(
                df[i], regression = regression
            ) for i in df.columns
        ]

    def _unit_roots(self, 
            df,
            method = "adf",
            **kwargs
        ):

        r = {
            "adf":self._ur_adf,
            "kpss":self._ur_kpss
        }[method]( df, kwargs.get("regression", "c") )

        tt = []
        for rr in r:
            t = []
            for i in list(rr):
                if isinstance(i, dict):
                    for j in list(i.values()):
                        t.append(j)
                else:
                    t.append(i)
            tt.append(t)

        return pd.DataFrame(
                    tt, 
                    columns = [ "t_stat", "p_value", "lags", "len", "1%", "5%", "10%", "resstore" ],
                    index = df.columns
                    )

    def log_diff(self, df):
        return np.log( df ).diff()
    
    def diff(self, df):
        return df.diff()

    def unit_roots(
            self, 
            df = None, 
            method = "adf",
            p_value = 0.05,
            reject = True,
            diff = 2, 
            log = False,
            ensure_no_ut = False
        ):
        """  


            reject (bool): Whether we want to reject or accept null hypothesis.
                Requiered if method is not adf or kpss.
                Defualt=True
            ensure_no_ut (bool): Ensure no unit roots in data.
                Process will iterate making a data difference or log difference
                expecting to reach no unit roots.
                Default=Falses
        """
        
        self.ensure_df(df)

        for i in range(diff):

            r = self._unit_roots(
                self.df,
                method = method
            )

            # Do something with r results

            if not ensure_no_ut: break

            if method == "kpss" or not reject:
                if (r[ "p_value" ] <= p_value).all():
                    break
            
            else:
                # We assume rejecting null hypothesis
                if (r["p_value"] >= p_value).all():
                    break

            self.df = self.log_diff(self.df) if log else self.diff(self.df)

        return r

    def durbin_watson(
            self, 
            df = None, 
            mode = "var", 
            target = None, 
            lim_sup = 2.5,
            lim_inf = 1.5,
            **kwargs
        ):
        """  
            mode (str): 
                linear with Ordinary Least Square Regression
                var (Lag 3)
            target (str): Exogenous Variable
                If VAR, target can be None for autoregression
                if != None, a regression is made based on the target set.
        """

        self.ensure_df(df)
        mode = mode.lower()

        if target is not None:
            X = self.df.drop(columns = [target])
            y = pd.DataFrame(self.df[target])

        if mode == 'var':
            mod = VAR(X, exog = y) if target is not None else VAR(self.df)
        
        elif mode == 'linear':
            mod = sm.OLS(X, y)

        res = mod.fit( kwargs.get("lag", 3) )

        dbt = durbin_watson(res.resid)
        dbt = pd.DataFrame(dbt)

        if target is not None:
            dbt.index = X.columns
            col_name = target
        else:
            dbt.index = self.df.columns
            col_name = 'durbin_watson'
        
        dbt.columns = [col_name]

        dbt['autocorrelation'] = dbt[(dbt[col_name]>= lim_inf) & (dbt[col_name]<=lim_sup)]
        dbt['autocorrelation'] = ~dbt['autocorrelation'].isnull()

        return dbt

    def _causality(self, df, target, tester, lag, verbose = 0):

        gc = grangercausalitytests(df[[target, tester]], maxlag=lag, verbose= False if verbose == 0 else True )
        keys = list( gc.keys() )

        r_df, *_ = gc[keys[0]]
        col_keys = list(r_df.keys())

        gc_df = pd.DataFrame(index = keys, columns=col_keys)

        for i in keys:
            r_df, *_ = gc[i]
            for j in col_keys:  
                test_statistic, p_value, *_ = r_df[j]
                gc_df.loc[i, j] = p_value

        return gc_df

    def causality(
            self,
            df = None,
            method = "granger",
            targets = [],
            p_value = 0.05,
            lag = 1,
            verbose = 0
        ):

        self.ensure_df(df)
        method = method.lower()

        if len(targets) == 0:
            targets = self.df.columns
            testetors = targets
        else:
            testetors = list( set(self.df.columns) - set(targets) )

        r = pd.DataFrame( index = testetors, columns = targets )

        for target in targets:
            for tester in testetors:
                r_aux = self._causality( self.df, target, tester, lag, verbose = verbose  )

                r.loc[ tester, target ] = 1 if r_aux.values.any() <= p_value else 0

        return r

    def corr(self, df = None, targets = [], method = "pearson"):
        self.ensure_df(df)
        
        if len(targets) == 0:
            targets = self.df.columns
            testetors = targets
        else:
            testetors = list( set(self.df.columns) - set(targets) )
        
        corr = self.df.corr()

        return corr.loc[ testetors, targets ]

    # Some other aux
    def ensure_date_col(self, df):
        if "date" in df.columns:
            return df

        df.reset_index(inplace = True)
        
        if "date" in df.columns:
            return df
        else:
            raise ValueError("No date column in DataFame")

    def get_frequency(self, df):
        
        df.sort_values(by = "date" , ascending=True, inplace = True)
        df["date"] = pd.to_datetime(df["date"])

        t = 360 / df["date"].diff().mean().days

        times = [1, 2, 3, 4, 6, 12, 52, 360]

        dist = lambda x: abs( x - t )

        closes = min( times, key = dist )

        return {
            1:"1a",
            2:"1b",
            3:"1t",
            4:"1q",
            6:"1sem",
            12:"1m",
            52:"1w",
            360:"1d"
        }[closes]

    def quarterly_to_monthly(self, df):

        df.set_index("date", inplace = True)

        df = df.reindex( 
            pd.date_range(
                start = df.index[0],
                end = df.index[-1],
                freq = "1MS" # Month start
            ),
            fill_value = "NaN"
        )

        df[ df.columns[0] ] = pd.to_numeric( df.columns[0], errors="coerce" )
        return df.interpolate(method = "linear")

    def _to_monthly(self, df):
        return df.resample( "1MS", on = "date" ).agg( {self.data:"last"} )

    def transform(self, df, frequency):
        
        df = self.ensure_date_col(df)

        freq = self.get_frequency( df )

        if freq == frequency: return df

        return {
            "1q":{
                "1m":self.quarterly_to_monthly
            },
            "1w":{
                "1m":self._to_monthly
            },
            "1d":{
                "1m":self._to_monthly
            }
        }[freq][frequency](df)

    # Trend TA

    def dema(self, length, target = "close"):
        """ Regresa un SERIE de una Doble EMA 

            Se genera una EMA con una largo LENGTH sobre TARGET
            Luego otra ema con el mismo LENGTH, pero sobre la primera EMA.
            La primera multiplicada por 2 (un valor aparentemente aleatorio)
            menos la segunda ema.

            Go long: Target > DEMA
            Go short: Target < DEMA
        """
        self.df['dema1'] = self.ema(length=length, target=target)
        self.df['dema2'] = self.ema(length=length, target='dema1')
        return 2*self.df['dema1'] - self.df['dema2']

    def ema(self, length, target = "close"):
        """ Regresa una SERIe de Exponential Moving Average """
        return self.df[target].ewm(span = length).mean()
   
    def sma(self, length, target = 'close'):
        """ Regresa una SERIE de Moving Average """
        return self.df[target].rolling(length).mean()

    def wma(self, length, target = "close"):
        """ Regresa una SERIE de Weighted Moving Average """
        weights = np.arange(1, length+1)
        return self.df[target].rolling(length).apply(lambda prices: np.dot(prices, weights)/weights.sum(), raw=True)



class Asset(TimeSeries):
    """ """

    def __init__(self, 
            symbol = None, 
            start = None, 
            end = datetime.today(), 
            frequency = None,
            broker = "yahoo_asset",
            fiat = None,
            from_ = "yahoo",
            sentiment = False,
            social_media = None,
            **kwargs
            ):
        """  
        """

        super().__init__()

        self.broker = broker.lower() 

        self.asset = self.get_asset()(
            symbol = symbol, 
            start = start, 
            end = end, 
            frequency = frequency,
            broker = broker,
            fiat = fiat,
            from_ = from_,
            sentiment = sentiment,
            social_media = social_media,
        )

    @property
    def symbol(self):
        return self.asset.symbol

    def get_asset(self):
        if self.broker == "binance":
            from .binance import Binance
            asset = Binance
        elif self.broker == "bitso":
            from .bitso import Bitso
            asset = Bitso
        else:
            from .base_asset import BaseAsset
            asset = BaseAsset
        
        return asset

    @property
    def asset(self):        
        return self._asset

    @asset.setter
    def asset(self, value):
        from .base_asset import BaseAsset
        if issubclass( type(value), BaseAsset ):
            self._asset = value
        else:
            raise ValueError( "It is not BaseAsset. Type {}".format(type(value)) )

    @property
    def df(self):
        return self.asset.df
    
    @df.setter
    def df(self, value):
        # Asset already contains all the filters for df
        self.asset.df = value

    def update(self, value = "df", pwd = None):
        self.asset.update( value = value, pwd = pwd )
    
    def refresh(self):
        self.asset.refresh()

    # Sentiment
    
    def sentimiento(self, social_media = ["Twitter", "Reddit", "Google"], desde_api = False, update = True, keywords = [], dropna = True):
        """  
            social_media (list): Lista de las redes sociales usadas para la descarga de informacion.
                                Default: ["Twitter", "Reddit", "Google"]
            desde_api (bool): Si la informacion sera obtenida de las carpetas ya destinadas a guardar esta informacin
                            o directamente de los API requests.
                            Default: False
            update (bool): Si despues de la carga con desde_api = True se actualizaran las carpetas con la informacion
                            actualizada.
                            Default: True
            keywords (list): Palabras claves a usar cuando se hagan los API Requests
                            Principalmente se dara uso para las descargas de Google Trends.
                            Default: Uso de listas en carpeta ...
            dropna (bool): Debido a la granularidad de la data, y los busquedas realizadas, NaN son freucentes.
                            Defualt: True

        """
        if desde_api:
            pass
        else:
            df = pd.DataFrame()
            for i in social_media:
                try:
                    aux = pd.read_csv(PWD("/{}/Sentimiento/{}/{}.csv".format( self.broker, i, self.symbol ) ))
                except:
                    continue

                if "Unnamed: 0" in aux.columns: aux.rename(columns ={"Unnamed: 0":"date"}, inplace = True)

                # if "date" in aux.columns:
                aux.set_index("date", inplace = True)
                
                aux.index = pd.to_datetime(aux.index)

                aux.columns += "_{}".format(i)

                df = pd.concat([ df, aux ], axis = 1)

        if dropna:
            df.dropna(inplace = True)

        df.sort_index(inplace = True)

        return df

    def google_trends(self, actualizar = False):
        df = self.google_trends_api if self.desde_api else self.google_trends_archivo
        
        if actualizar: df.to_csv( PWD( "{}/Sentimientos/GoogleTrends/{}/{}.csv".format( self.broker, self.frecuencia, self.simblo ) ) )

        return df
    
    def google_trends_api(self):
        assert Bitso[ self.symbol ].get("google_trends", False), "No hay ´keywords´ en Assets.py de Bitso para la busqueda en Google Trends"

        if self.frecuencia != "1m":
            df = pd.DataFrame()
            for i in Bitso[ self.symbol ][ "google_trends" ]:
                data = dailydata.get_daily_data(i, 
                                            self.inicio.year, 
                                            self.inicio.month, 
                                            self.fin.year, 
                                            self.fin.month, 
                                            geo = "",
                                            verbose = False,
                                            wait_time = 20
                                )
                
                df = pd.concat([df, data[i]], axis = 1)

                time.sleep(2)
        else:
            
            df = pd.DataFrame()
            for i in Bitso[ self.symbol ][ "google_trends" ]:
                pytrends = TrendReq(hl = 'en-US', tz = 360)
                pytrends.build_payload(
                    i,
                    cat = 0, # 0 -> All categories, 7 -> Finance 
                    timeframe = "all"
                )

                data = pytrends.interest_over_time()

                if "isPartial" in data.columns: data.drop(columns = ["isPartial"], inplace = True)

                df = pd.concat([df, data[i]], axis = 1)

                time.sleep(1)

        return df

    def google_trends_archivo(self):
        df = pd.read_csv( PWD( "{}/Sentimientos/GoogleTrends/{}/{}.csv".format( self.broker, self.frecuencia, self.simblo ) ) )

        return df

    # # Fundamental Analyzers

    # def _beta(self):
    #     pwd = PWD("/{}/Mercado/Informacion Fundamental/{}.json")

    #     with open( pwd.format(self.broker, self.symbol) , "r") as fp:
    #         data = json.load(fp)

    #     return float(data["Beta (5Y Monthly)"])

    # def _price_earnings(self):
    #     """ Regresa el Price/Earnings ratio 
        
    #         NOTA: Una compañia que tiene ganancias negativas 
    #         no tiene P/E ratio, por ende, al ejectuar esta funcion
    #         y encontrar ganancias negativas, levantara un error.
    #     """
    #     return (self.df.iloc[-1]['close'] / self._earnings_per_share()) if self._earnings_per_share() > 0 else 0

    # def _earnings_per_share(self):
    #     """ Regresa el trailing EPS ratio 
        
    #         Earnings per share ratio que es la cantidad 
    #         de ganancias por accion.
    #         La porcion de las ganancias netas que son 
    #         ganadas "por cada accion".
            
    #     """
    #     if not hasattr(self, "ticker"):
    #         self.ticker = yf.Ticker(self.symbol)
        
    #     return self.ticker.info['trailingEps']

    # def _g_score(self):
    #     raise NotImplementedError

    # def _book_to_market(self, quarterly = True):
    #     """ 
    #         Book to Markt Ratio = Book Value of Equity / Market Value of Equity
    #     """
    #     return self._book_value(quarterly=quarterly)  / self._market_value()

    # def _book_value(self, quarterly = True):
    #     """ 
    #         Regresa una seria del Book Value 
        
    #         De acuerdo a investopedia, book value puede ser calculado:
    #         Book value = Total assets - Total liabilites
    #     """

    #     df = self.ticker.quarterly_balance_sheet.T if quarterly else self.ticker.balance_sheet.T
    #     return pd.DataFrame( df['Total Assets'] - df['Total Liab'] )
    
    # def _market_value(self):
    #     """  
    #         Market Value or Market Capitalization
    #     """
    #     raise NotImplementedError

    # Technical analyzers
        
    def adx(self, length, high = 'High', low = 'Low', close = 'close'):
        """ Regresa tres SERIES de Average Directional Movement Index 
                                ADX, DI+, DI-

            Mide la fuerza de una tendencia, independiente de su direccion

            Go Long:
            Go Short:
        """
        adx_object = ta.trend.ADXIndicator(high=self.df[high], low=self.df[low], \
            close=self.df[close], window = length)
        
        return adx_object.adx(), adx_object.adx_pos(), adx_object.adx_neg()

    def aroon(self, length, target='close'):
        """ Regresa tres SERIES de Aroon Indicator 
            arron indicator, aroon_up, aroon_down

            Indica cuando una tendecias es más capaz de cambiar
            de direccion
            aroon_up (uptrend)
            aroon_down (downtrend)
        """
        aroon_object = ta.trend.AroonIndicator(close=self.df[target], \
            window=length)

        return aroon_object.aroon_indicator(), aroon_object.aroon_up(),\
            aroon_object.aroon_down()

    def aroon_down(self, length, target = 'close'):
        """ Regresa una SERIE de Aroon Indicator 

            Indica cuando una tendencia es más capaz de cambiar de direccion
            (downtrend)
        """
        return ta.trend.arron_down(close=self.df[target], window=length)

    def aroon_up(self, length, target = 'close'):
        """ Regresa una SERIE de Aroon Indicator 

            Indica cuando una tendencia es más capaz de cambiar de direccion
            (uptrend)
        """
        return ta.trend.arron_up(close=self.df[target], window=length)

    def bollinger_bands(self, length=20, std=2, close='close'):
        """ Regrea tres SERIES de Bollinger Bands
            High, Medium y Low Band.

            Cuando la banda media es cruzada por el close
            se considera una señal de compra.
            Y cuando el close supera a la banda alta,
            se vende.
            * Desconozco que uso puede tener la banda baja.

            Defaults por: https://school.stockcharts.com/doku.php?id=technical_indicators:bollinger_bands
            std (int): Factor para la desviacion estandar
        """

        bb_obj = ta.volatility.BollingerBands(close=self.df[close], \
            window=length, ndev=std)

        return bb_obj.bollinger_hband(), bb_obj.bollinger_mavg(), bb_obj.bollinger_lband()

    def cci(self, length, constant = 0.015, close = 'close', high = 'High', low = 'Low'):
        """ Regresa una SERIE de Commodity Channel Index 
            
            CCI mide la diferencia entre al cambio en el precio, y su cambio promedio.
            Lecturas positivas indican que el precio esta arriba de su promedio, 
            lo cual significa fuerza.
            Lecturas negaticas indican que el precio esta debajo de su promedio,
            lo cual significa debilidad.
        """
        return ta.trend.CCIIndicator(high=self.df[high], low=self.df[low], close=self.df[close], \
            window=length, constant = constant ).cci()
    
    def dpo(self, length, target = 'close'):
        """ Regresa una SERIE de Detrended Price Oscillator
            
            Es un indicador que permite remover las tendencias del target
            haciendo capaz, observar sus ciclos.
        """
        return ta.trend.DPOIndicator(close=self.df[target], window=length).dpo()

    def easy_of_movement(self, length, high='High', low='Low', volume='Volume'):
        """ Regresa una SERIE de Easy of Movement 
        
            Hace la relacion entre el cambio de precio contra su volumen.
            Es importante para observar la fuerza de una tendencia.
        """
        return ta.volume.EaseOfMovementIndicator(high=self.df[high], low=self.df[low], \
            volume=self.df[volume], window=length).easy_of_movement()

    def easy_of_movement_signal(self, length, high='High', low='Low', volume='Volume'):
        """ Regresa una SERIE la señal de Easy of Movement
        
            Hace la relacion entre el cambio de precio contra su volumen.
            Es importante para observar la fuerza de una tendencia.
        """
        return ta.volume.EaseOfMovementIndicator(high=self.df[high], low=self.df[low], \
            volume=self.df[volume], window=length).sma_easy_of_movement()
    
    def engulfing(self):
        df = copy(self.df)
        df["o"] = self.df["Open"].diff().apply(lambda x : -1 if x > 0 else 1)
        df["c"] = self.df["close"].diff().apply(lambda x : 1 if x > 0 else -1)
        return df["o"] + df["c"]

    def force_index(self, length, close='close', volume='Volume'):
        """ Regresa una SERIe del Force Index 
        
            Ilustra que tan fuerte es la presion para comprar o vender.
            ALtos positivos significa que es fuerte la tendencia a la alza.
            Valores bajos, signica que es fuerte la tendencia a la baja.
        """
        return ta.volume.ForceIndexIndicator(close=self.df[close], volume=self.df[volume], \
            window=length).force_index()

    def hull_ema(self, length, target='close'):
        """ Regresa una SERIE de Hull Exponential Moving Average 
        
            Obtenido de TradingView
            De acuerdo a tradingview, si mi valor ahorita
            es mayor que el obtenido en t-2, se manda una señal
            de compra, si es menor, de venta.
        """
        self.df['hull_src'] = 2*self.ema(length//2) - self.ema(length)
        return self.ema(int( np.sqrt(length) ), target='hull_src' )

    def hull_twma(self, length, target='close'):
        """ Regresa una SERIE de Hull Triple Weighted Moving Average 
        
            Obtenido de TradingView
            De acuerdo a tradingview, si mi valor ahorita
            es mayor que el obtenido en t-2, se manda una señal
            de compra, si es menor, de venta.
        """
        self.df['hull_src'] = 3*self.wma(length//3) - self.wma(length//2) - self.wma(length)
        return self.wma(length , target='hull_src' )

    def hull_wma(self, length, target='close'):
        """ Regresa una SERIE de Hull Weighted Moving Average 
        
            Obtenido de TradingView
            De acuerdo a tradingview, si mi valor ahorita
            es mayor que el obtenido en t-2, se manda una señal
            de compra, si es menor, de venta.
        """
        self.df['hull_src'] = 2*self.wma(length//2) - self.wma(length)
        return self.wma(int( np.sqrt(length) ), target='hull_src' )

    def kama(self, length=10, fast_ema=2, slow_ema=30, close='close'):
        """ Regresa una SERIE de Kaufman's Adaptative Moving Average 
        
            Una media movil diseñada para reporta la volatilidad del mercado.
            KAMA seguira los precios cuando haya swings pequeños.
            Se ajustara cuando los swings sean más grandes y seguira los
            precios desde una mayor distancia

            Es como una media movil, cuando el precio de cierre
            supere al de KAMA, se mandara una señal de compra ...

            length (int): Periodo para el Efficiency Ratio
            Defaults basados en: https://school.stockcharts.com/doku.php?id=technical_indicators:kaufman_s_adaptive_moving_average
        """
        return ta.momentum.KAMAIndicator(close=self.df[close], \
            window=length, pow1=fast_ema, pow2=slow_ema).kama()

    def macd(self, fast, slow, sign, target = 'close'):
        """ Regresa una SERIE de Moving Average Convergence-Divergence """

        macd_object = ta.trend.MACD(close=self.df[target], window_fast = fast, \
            window_slow = slow, window_sign = sign)

        return macd_object.macd(), macd_object.macd_signal()
    
    def macd_hist(self, fast, slow, sign, target = 'close'):
        """ Regresa una SERIE de Moving Average Convergence-Divergence Histograma"""
        return ta.trend.MACD(close=self.df[target], n_fast = fast, \
            n_slow = slow, n_sign = sign).macd_diff()

    def macd_signal(self, fast, slow, sign, target = 'close'):
        """ Regresa una SERIE de Moving Average Convergence-Divergence Signal"""
        return ta.trend.MACD(closE=self.df[target], n_fast = fast, \
            n_slow = slow, n_sign = sign).macd_signal()

    def mass_index(self, low, high=9, low_target = 'Low', high_target = 'High'):
        """ Regresa una SERIE del Mass Index

            Usa el rango High-Low para identificar reversiones en la tendencia
            basandos en la expancion de dicho rango.
            Indentifica protuberancias en los rangos, para identificar reversiones
        """
        return ta.trend.MassIndex(high=self.df[high_target], low=self.df[low_target], \
            window_slow = high, window_fast = low).mass_index()
    
    def momentum(self, periodos, target = "close"):
        return self.df[target].pct_change(periods = periodos) + 1

    def roc(self, length, target = 'close'):
        """ Regresa una SERIE de Rate of Change

            Mide el cambio porcentual del target de un periodo al siguiente.
            Compara el precio de este periodo con el del "length" periodos atras
        """
        return ta.momentum.ROCIndicator(close=self.df[target], window=length).roc()
    
    def rsi(self, length, target = 'close'):
        """ Regresa una SERIE del Relative Strength Index 
            
            Compara la magnitud de ganancias y perdidas en un periodo de tiempo,
            para medir la velocidad y movimientos de cambios de precio de un Asset.
            Es usado principalmente para indentificar zonas de
            sobrevendido o sobrecomprado.
        """
        return ta.momentum.RSIIndicator(close=self.df[target], window=length).rsi()

    def stoch(self, length, sma, close = 'close', high = 'High', low = 'Low'):
        """ Regresa dos SERIES del Stochastic Oscillator
            La primera es la señal stochastica, y la segunda
            es la misma pero con un smooth.
        """

        stoch_object = ta.momentum.StochasticOscillator(high=self.df[high], low=self.df[low], \
            close=self.df[close], window=length, smooth_window=sma)

        return stoch_object.stoch(), stoch_object.stoch_signal()
    
    def support_resistance(self, length, support = 'High', resistance = "Low"):
        """ Regrea dos series indicando los MAXIMOS y 
            MINIMOS de una seria un periodo LENGTH 
            
            Go long: 
                - Si llega a la zona de soporte, y la rompe.
                - Si llega a la zona de resistencia, y sube. 
            Go short:
                - Si llega a la zona de soporte, y baja.
                - Si llega a la zona de resistencia y la rompe. 
            """
        return self.df[support].rolling(length).max(), self.df[resistance].rolling(length).min()

    def tema(self, length, target = 'close'):
        """ Regresa un SERIE de una Triple EMA 

            Se genera una EMA con una largo LENGTH sobre TARGET
            Luego otra EMA con el mismo LENGTH, pero sobre la primera EMA.
            Se repite el proceso con la segunda EMA
            La primera menos la segunda, por 3 (un valor aparentemente aleatorio)
            mas la ultima

            Go long: Target > TEMA
            Go short: Target < TEMA
        """
        self.df['tema1'] = self.ema(length=length, target=target)
        self.df['tema2'] = self.ema(length=length, target='tema1')
        self.df['tema3'] = self.ema(length=length, target='tema2')
        return 3*(self.df['tema1'] - self.df['tema2']) + self.df['tema3']

    def trix(self, length, close = 'close'):
        """ Regresa una SERIE de TRIX 
        
            Muestra el cambio porcentual de una trple media movil
            exponencial.
        """
        return ta.trend.TRIXIndicator(close = self.df[close], window=length).trix()

    def tsi(self, high, low, target = 'close'):
        """ Regresa una SERIE de True Strength Index 
            
            Demuestra la direccion de tendencias, así como condiciones
            de sobrecompra o sobreventa.
        """
        return ta.momentum.TSIIndicator(close=self.df[target], r=high, s=low).tsi()
    
    def uo(self, short, medium, long, wshort, wmedium, wlong, high='High', low='Low', close='close'):
        """ Regresa una Serie de Ultimate Oscillator 

            Oscilador de momentum que busca capturar el momentum a traves de 
            tres diferentes timeframes.

            short, medium, long (int)
            wshort, wmedium, wlong (float)
        """
        return ta.momentum.UltimateOscillator(high=self.df[high], low=self.df[low], \
            close=self.df[close], s=short, m=medium, len=long, ws=wshort, wm=wmedium, wl=wlong).uo()

    def vwap(self, length, high = 'High', low = 'Low', close = 'close', volume = 'Volume'):

        return ta.volume.VolumeWeightedAveragePrice(high = self.df[high], low=self.df[low], \
            close=self.df[close], volume=self.df[volume], window = length).volume_weighted_average_price()
    
    def vpt(self, close = 'close', volume = 'Volume'):

        return ta.volume.VolumePriceTrendIndicator( close = self.df[close], \
            volume = self.df[volume] ).volume_price_trend()

    def vortex_indicator(self, length, high='High', low='Low', close='close'):
        """ Regresa dos SERIES de dos osciladores que captura
            tendencias a la alza y a la baja.
         """
        vi = ta.trend.VortexIndicator(high=self.df[high], low=self.df[low], \
            close=self.df[close], window=length)

        return vi.vortex_indicator_pos(), vi.vortex_indicator_neg()

    def william(self, lookback_p, high='High', low='Low', close='close'):
        """ Regresa una Serie del Williams %R 
        
            Lecturas de entre 0, -20 se considera como sobrecomprado.
            Lecturas de -80, -100 se considera sobrevendido.
        """
        return ta.momentum.WilliamsRIndicator(high=self.df[high], low=self.df[low], close=self.df[close], \
            lbp=lookback_p).wr()

    