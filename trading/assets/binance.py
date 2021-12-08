from datetime import datetime, timedelta
import pandas as pd
import time
import warnings

# Binance
from binance.client import Client
from binance.enums import *
from dccd.histo_dl import binance

from .base_asset import BaseAsset
from trading.func_aux import PWD, time_diff

class Binance(BaseAsset):
    def __init__(
        self, 
        symbol, 
        start = None, 
        end = datetime.today(), 
        frequency = "1d", 
        fiat = "usdt", 
        from_api = True, 
        from_ext = False,
        sentiment = False,
        social_media = None,
    ):
        
        super().__init__(
            symbol = symbol,
            start = start,
            end = end,
            frequency = frequency,
            from_api = from_api,
            sentiment=sentiment,
            social_media=social_media
        )

        self.fiat = fiat.lower() if fiat is not None else "usdt"
        self.from_ext = from_ext
        self.symbol_aux = self.symbol + self.fiat
        self.broker = "binance"

    def df_api(self):
        raise NotImplementedError

    def df_ext_api_aux(self, b):
        """ Auxuliar function for df_ext_api """

        def sum_time(start, frequency, t = 400):
            if frequency == "d":
                end = start + timedelta(days = t)
            elif frequency == "h":
                end = start + timedelta(seconds = t*3600)
            elif frequency == "min":
                end = start + timedelta(seconds = t*60)
            
            return end

        start = self.start
        df = pd.DataFrame()
        end = sum_time( start, self.interval )

        while True:
        
            try:
                dff = b.import_data(start = str(start), end = str(end)).get_data()
            except:
                dff = pd.DataFrame() 
            
            df = pd.concat( [ df, dff ], axis = 0 )

            tdiff = time_diff( end, self.end ) 

            if tdiff == 0:
                break
            elif tdiff > 400:
                start = end
                end = sum_time( start, self.interval )
            else: 
                start = end
                end = self.end
            
            time.sleep(0.2)

        df.drop_duplicates(inplace = True)
    
        return df

    def df_ext_api(self):
        pwd = PWD("/binance/dccd")

        aux = {
            'm':'minutely',
            'h':'hourly',
            'd':'daily',
            'w':'weekly'
        }
        b = binance.FromBinance( pwd, crypto=self.symbol.upper(), span= aux[self.interval],fiat=self.fiat.upper())

        tdiff = time_diff( self.start, self.end, self.interval )

        if tdiff > 450:
            df = self.df_ext_api_aux( b )
        else:
            try:
                df = b.import_data(start = str(self.start), end = str(self.end)).get_data()
            except Exception as e:
                warnings.warn("Binance data importation Exception: {}".format(e))
                df = pd.DataFrame()    

        if len(df) == 0: return None

        df.drop(columns = ['date', 'TS', 'time'], inplace=True)
        df.columns = [i.lower() for i in df.columns]
        df.set_index('date', inplace = True)
        df.sort_index(inplace = True)

        return df


