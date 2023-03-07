# -*- coding: utf-8 -*-

# Librerias generales
from copy import copy
import pandas as pd
import numpy as np
from datetime import datetime

import pandas_ta as pta
import ta

from trading.func_aux import *
from .timeseries import TimeSeries

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
            verbose = 0,
            **kwargs
            ):
        """  
        """

        super().__init__()

        self.broker = broker.lower() 
        self.verbose = verbose

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

    @property
    def descr(self):
        """ Returns Json description of asset 
            Information logged on assets.json
        """
        return self.asset.descr

    @descr.setter
    def descr(self, value):
        self.asset.descr = value

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

    def google_trends(self, keywords = [], from_ = "api", **kwargs):
        if len(keywords) == 0:
            keywords = self.asset.descr[ "google_trends" ]

        from trading.google_trends import GoogleTrend

        self.gt = GoogleTrend( 
            keywords=keywords,
            start = self.asset.start,
            end = self.asset.end,
            frequency = self.asset.frequency,
            from_ = from_,
            **kwargs
        )

        return self.gt.df

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
        
    def adx(self, length, high = 'high', low = 'low', close = 'close'):
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
            high, Medium y low Band.

            Cuando la banda media es cruzada por el close
            se considera una señal de compra.
            Y cuando el close supera a la banda alta,
            se vende.
            * Desconozco que uso puede tener la banda baja.

            Defaults por: https://school.stockcharts.com/doku.php?id=technical_indicators:bollinger_bands
            std (int): Factor para la desviacion estandar
        """

        bb_obj = ta.volatility.BollingerBands(close=self.df[close], \
            window=length, window_dev=std)

        return bb_obj.bollinger_hband(), bb_obj.bollinger_mavg(), bb_obj.bollinger_lband()

    def cci(self, length, constant = 0.015, close = 'close', high = 'high', low = 'low'):
        """ Regresa una SERIE de Commodity Channel Index 
            
            CCI mide la diferencia entre al cambio en el precio, y su cambio promedio.
            Lecturas positivas indican que el precio esta arriba de su promedio, 
            lo cual significa fuerza.
            Lecturas negaticas indican que el precio esta debajo de su promedio,
            lo cual significa debilidad.
        """
        return ta.trend.CCIIndicator(high=self.df[high], low=self.df[low], close=self.df[close], \
            window=length, constant = constant ).cci()
    
    def cci_slope( self, length, slope ):
        return self.cci( length=length ).pct_change( slope )

    def dpo(self, length, target = 'close'):
        """ Regresa una SERIE de Detrended Price Oscillator
            
            Es un indicador que permite remover las tendencias del target
            haciendo capaz, observar sus ciclos.
        """
        return ta.trend.DPOIndicator(close=self.df[target], window=length).dpo()

    def easy_of_movement(self, length, high='high', low='low', volume='volume'):
        """ Regresa una SERIE de Easy of Movement 
        
            Hace la relacion entre el cambio de precio contra su volumen.
            Es importante para observar la fuerza de una tendencia.
        """
        return ta.volume.EaseOfMovementIndicator(high=self.df[high], low=self.df[low], \
            volume=self.df[volume], window=length).easy_of_movement()

    def easy_of_movement_signal(self, length, high='high', low='low', volume='volume'):
        """ Regresa una SERIE la señal de Easy of Movement
        
            Hace la relacion entre el cambio de precio contra su volumen.
            Es importante para observar la fuerza de una tendencia.
        """
        return ta.volume.EaseOfMovementIndicator(high=self.df[high], low=self.df[low], \
            volume=self.df[volume], window=length).sma_easy_of_movement()
    
    def engulfing(self):
        df = copy(self.df)
        df["o"] = df["open"].diff().apply(lambda x : -1 if x > 0 else 1)
        df["c"] = df["close"].diff().apply(lambda x : 1 if x > 0 else -1)
        df["oc"] = df["o"] + df["c"]
        df["bear"] = ( df["open"] >= df["close"].shift(1) ) & ( df["close"] <= df["open"].shift(1) ) & ( df["oc"] == -2 )
        df["bull"] = ( df["close"] >= df["open"].shift(1) ) & ( df["open"] <= df["close"].shift(1) ) & ( df["oc"] == 2 )
        
        df["bear"] = df["bear"].apply(lambda x : -1 if x else 0)
        df["bull"] = df["bull"].apply(lambda x : 1 if x else 0)

        return df["bear"] + df["bull"]

    def force_index(self, length, close='close', volume='volume'):
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

    def keltner(self, window = 20, windows_atr = 10, high = "high", low = "low", close = "close", original_version = True ):
        """ Keltner Channel 
        
            Trend following indicator used to identify revsal with channel breakouts 
            channel directions

            original_version (bool) – if True, use original version as the centerline (SMA of typical price) if False, use EMA of close as the centerline. More info: https://school.stockcharts.com/doku.php?id=technical_indicators:keltner_channels
        """
        keltner = ta.volatility.Keltner_Channel(
            high = high,
            low = low, 
            close = close,
            window = window,
            windows_atr = windows_atr,
            original_version = original_version
        )

        return 

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

    def mass_index(self, low, high=9, low_target = 'low', high_target = 'high'):
        """ Regresa una SERIE del Mass Index

            Usa el rango high-low para identificar reversiones en la tendencia
            basandos en la expancion de dicho rango.
            Indentifica protuberancias en los rangos, para identificar reversiones
        """
        return ta.trend.MassIndex(high=self.df[high_target], low=self.df[low_target], \
            window_slow = high, window_fast = low).mass_index()
    
    def momentum(self, periodos, target = "close"):
        return self.df[target].pct_change(periods = periodos) + 1

    def obv(self):
        """ On Balance Volume """
        return ta.volume.OnBalanceVolumeIndicator( self.df["close"], self.df["volume"] ).on_balance_volume()

    def roc(self, length, target = 'close'):
        """ Regresa una SERIE de Rate of Change

            Mide el cambio porcentual del target de un periodo al siguiente.
            Compara el precio de este periodo con el del "length" periodos atras
        """
        return ta.momentum.ROCIndicator(close=self.df[target], window=length).roc()
    

    def rolling_fractals(self, lenght, period, shift = False, order = "buy"):
        v = self.william_fractals(period, shift = shift, order = order)
        return v.rolling( lenght ).sum()

    def rsi(self, length, target = 'close'):
        """ Regresa una SERIE del Relative Strength Index 
            
            Compara la magnitud de ganancias y perdidas en un periodo de tiempo,
            para medir la velocidad y movimientos de cambios de precio de un Asset.
            Es usado principalmente para indentificar zonas de
            sobrevendido o sobrecomprado.
        """
        return ta.momentum.RSIIndicator(close=self.df[target], window=length).rsi()

    def rsi_smoth(self, length, smoth, target = "close"):
        return self.rsi( length=length, target = target ).rolling(smoth).mean()
    
    def rsi_smoth_slope(self, length, smoth, slope, target = "close"):
        return self.rsi_smoth( length=length, smoth=smoth, target = target ).pct_change(periods = slope)

    def stoch(self, length, sma, close = 'close', high = 'high', low = 'low'):
        """ Regresa dos SERIES del Stochastic Oscillator
            La primera es la señal stochastica, y la segunda
            es la misma pero con un smooth.
        """

        stoch_object = ta.momentum.StochasticOscillator(high=self.df[high], low=self.df[low], \
            close=self.df[close], window=length, smooth_window=sma)

        return stoch_object.stoch(), stoch_object.stoch_signal()
    
    def supertrend(self, length=None, multiplier=None, order = "buy", close = 'close', high = 'high', low = 'low'):
        df = pta.supertrend( high = self.df["high"], low = self.df["low"], close = self.df["close"], length = length, multiplier=multiplier )
        col = "SUPERTl" if order == "buy" else "SUPERTs"
        col = [ c for c in df.columns if col in c ][0]
        
        return df[col]

    def support_resistance(self, length, support = 'high', resistance = "low"):
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
        return ta.momentum.TSIIndicator(close=self.df[target], window_fast=high, window_slow=low).tsi()
    
    def uo(self, short, medium, long, wshort, wmedium, wlong, high='high', low='low', close='close'):
        """ Regresa una Serie de Ultimate Oscillator 

            Oscilador de momentum que busca capturar el momentum a traves de 
            tres diferentes timeframes.

            short, medium, long (int)
            wshort, wmedium, wlong (float)
        """
        return ta.momentum.UltimateOscillator(high=self.df[high], low=self.df[low], \
            close=self.df[close], s=short, m=medium, len=long, ws=wshort, wm=wmedium, wl=wlong).uo()

    def vwap(self, length, high = 'high', low = 'low', close = 'close', volume = 'volume'):

        return ta.volume.VolumeWeightedAveragePrice(high = self.df[high], low=self.df[low], \
            close=self.df[close], volume=self.df[volume], window = length).volume_weighted_average_price()
    
    def vpt(self, close = 'close', volume = 'volume'):

        return ta.volume.VolumePriceTrendIndicator( close = self.df[close], \
            volume = self.df[volume] ).volume_price_trend()

    def vortex_indicator(self, length, high='high', low='low', close='close'):
        """ Regresa dos SERIES de dos osciladores que captura
            tendencias a la alza y a la baja.
         """
        vi = ta.trend.VortexIndicator(high=self.df[high], low=self.df[low], \
            close=self.df[close], window=length)

        return vi.vortex_indicator_pos(), vi.vortex_indicator_neg()

    def william(self, lookback_p, high='high', low='low', close='close'):
        """ Regresa una Serie del Williams %R 
        
            Lecturas de entre 0, -20 se considera como sobrecomprado.
            Lecturas de -80, -100 se considera sobrevendido.
        """
        return ta.momentum.WilliamsRIndicator(high=self.df[high], low=self.df[low], close=self.df[close], \
            lbp=lookback_p).williams_r()

    def william_fractals(self, period = 2, shift = False, order = "buy"):
        """Indicate bearish and bullish fractal patterns using shifted Series.

        :param df: OHLC data
        :param period: number of lower (or higher) points on each side of a high (or low)
        :return: tuple of boolean Series (bearish, bullish) where True marks a fractal pattern
        """

        df = self.df

        periods = [p for p in range(-period, period + 1) if p != 0] # default [-2, -1, 1, 2]

        if order == "buy":
            lows = [df['low'] < df['low'].shift(p) for p in periods]
            bulls = pd.Series(np.logical_and.reduce(lows), index=df.index)

            if shift:
                bulls = bulls.shift( period )
        
            return bulls

        elif order == "sell":
            highs = [df['high'] > df['high'].shift(p) for p in periods]
            bears = pd.Series(np.logical_and.reduce(highs), index=df.index)

            if shift:
                bears = bears.shift( period )

            return bears
