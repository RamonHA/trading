# Timeseries + statsmodels
from statsmodels.tsa.stattools import kpss, adfuller
from statsmodels.stats.stattools import durbin_watson
from statsmodels.tsa.api import VAR
from statsmodels.tsa.stattools import grangercausalitytests
import statsmodels.api as sm
from scipy.ndimage import gaussian_filter1d
import numpy as np
import pandas as pd
import yfinance as yf
import re

from trading.func_aux import *

class TimeSeries():
    """ Clase Time Series 
        Esta clase permite definir aquellas variables que sean TimeSeries, y las dota
        de caracteristicas estadisticas, etc.
    """
    def __init__(self, df = None):
        
        if df is not None:
            self.df = df

    def __repr__(self):
        return '{}: {}'.format(type(self).__name__,  self.symbol )

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

    def target_testetor(self, targets = []):
        if len(targets) == 0:
            targets = self.df.columns
            testetors = targets
        else:
            testetors = list( set(self.df.columns) - set(targets) )

        return targets, testetors

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
            columns = {
                "adf": [ "t_stat", "p_value", "lags", "len", "1%", "5%", "10%", "resstore" ] ,
                "kpss": [ "t_stat", "p_value", "lags", "1%", "5%", "10%", "resstore" ]
            }[method],
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
            self.df.dropna(inplace = True)

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
        targets, testetors = self.target_testetor(targets)

        r = pd.DataFrame( index = testetors, columns = targets )

        for target in targets:
            for tester in testetors:
                r_aux = self._causality( self.df, target, tester, lag, verbose = verbose  )

                r.loc[ tester, target ] = 1 if r_aux.values.any() <= p_value else 0

        return r

    def corr(self, df = None, targets = [], method = "pearson"):
        self.ensure_df(df)
        targets, testetors = self.target_testetor(targets)
        
        corr = self.df.corr()

        return corr.loc[ testetors, targets ]

    def redundancy(self, df = None, targets = [], threshold = 0.08, above = False):
        """ 
            Redundancy is considered below certain threshold.

            If want above threshold, set above = True
        """
        
        self.ensure_df(df)

        if len(targets) == 0:
            targets = df.columns
            testetors = targets
        else:
            testetors = list( set(df.columns) - set(targets) )

        df = df.loc[ testetors, targets ]

        r = [] # Remove

        if above:
            for c in df.columns:
                if (c in r): continue
                for i in df.index:
                    if (i == c) or (i in r): continue
                    if df.loc[ i, c ] > threshold:
                        r.append( i )

        else:
            for c in df.columns:
                if (c in r): continue
                for i in df.index:
                    if (i == c) or (i in r): continue
                    if df.loc[ i, c ] < threshold:
                        r.append( i )

        return r

    def oneside_gaussian_filter(self, sigma, target = "close"):
        return gaussian_filter1d( self.df[ target ], sigma = sigma )

    def oneside_gaussian_filter_slope(self, sigma, slope, target = "close"):
        return pd.Series(self.oneside_gaussian_filter( sigma, target )).pct_change( periods=slope ).values

    # Some other aux

    def reindex(self, df, frequency, interpolate = "linear", end = None):
        df = df.reindex( 
            pd.date_range(
                start = df.index[0],
                end = df.index[-1] if end is None else end,
                freq = {
                    "1m":"1MS",
                }[frequency]
            ),
            fill_value = "NaN"
        )

        df[ df.columns[0] ] = pd.to_numeric( df[df.columns[0]], errors="coerce" )

        return df.interpolate(method = interpolate)

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

        diff_time = df["date"].diff().mean()

        frequencies = {
            "dailys":{
                1:"1a",
                2:"1b",
                3:"1t",
                4:"1q",
                6:"1sem",
                12:"1m",
                52:"1w",
                360:"1d"
            },
            "minutes":{
                1:"1d",
                2:"12h",
                3:"8h",
                4:"6h",
                6:"4h",
                8:"3h",
                12:"2h",
                24:"1h",
                48:"30min",
                96:"15min",
                144:"10min",
                288:"5min",
                480:"3min",
                1440:"1min"
            }
        }

        if diff_time.days >= 1:
            t = 360 / diff_time.days
            mode = "dailys"

        else:
            diff_time = diff_time.seconds / 60
            t = 1440 / diff_time
            mode = "minutes"

        times = list(frequencies[mode].keys())

        dist = lambda x: abs(x - t)

        closes = min(times, key = dist)

        return frequencies[mode][closes]

    def to_lower_freq(self, df, frequency):

        df.set_index("date", inplace = True)

        return self.reindex( df, frequency=frequency )

    def to_higher_freq(self, df, p, f):
        """ https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#dateoffset-objects   """
        # p, f  = re.findall(r'(\d+)(\w+)', frequency)[0]
        df["date"] = pd.to_datetime( df["date"] ) 

        new_freq = "{}{}".format( p, {
            "m":"MS",
            "min":"min",
            "h":"H",
            "d":"D"
        }[f] )

        if "close" in df.columns:

            return df.resample( new_freq , on = "date" ).agg( {
                "open":"first", 
                "low":"min",
                "high":"max",
                "close":"last",
                "volume":"sum"
            } )
        
        else:
            return df.resample( new_freq, on = "date" ).agg( {self.data:"last"} )

    def transform(self, df, frequency):
        
        df = self.ensure_date_col(df)

        try:
           freq = self.asset.frequency_db
        except Exception as e:
            try:
                freq = self.frequency_db
            except Exception as ee:
                freq = self.get_frequency( df )

        if freq == frequency: return df

        freq_p, freq_i = re.findall(r'(\d+)(\w+)', freq)[0]
        frequency_p, frequency_i = re.findall(r'(\d+)(\w+)', frequency)[0]

        freq_p = int(freq_p)
        frequency_p = int(frequency_p)

        freqs = {
            "q":6,
            "m":5,
            "w":4,
            "d":3,
            "h":2,
            "min":1,
            "s":0
        }

        if ( freqs[frequency_i] > freqs[freq_i] ) or \
            ( freqs[frequency_i] == freqs[freq_i] and frequency_p > freq_p ):
            return self.to_higher_freq( df, frequency_p, frequency_i )
        else:
            return self.to_lower_freq( df, frequency )

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
   
    def ema_slope(self, length, slope, target = "close"):
        return self.ema( length=length, target = target ).pct_change( periods=slope )

    def sma(self, length, target = 'close'):
        """ Regresa una SERIE de Moving Average """
        return self.df[target].rolling(length).mean()

    def sma_slope(self, length, slope, target = "close"):
        return self.sma( length=length, target = target ).pct_change( periods=slope )

    def wma(self, length, target = "close"):
        """ Regresa una SERIE de Weighted Moving Average """
        weights = np.arange(1, length+1)
        return self.df[target].rolling(length).apply(lambda prices: np.dot(prices, weights)/weights.sum(), raw=True)

    def wma_slope(self, length, slope, target = "close"):
        return self.wma( length=length, target = target ).pct_change( periods=slope )
