from datetime import datetime
import pandas as pd

# Binance
from binance.client import Client
from binance.enums import *
from dccd.histo_dl import binance

from .base_asset import BaseAsset

class Binance():
    def __init__(self, symbol, start = None, end = datetime.today(), frequency = "1d", fiat = "USDT", from_api = True, from_ext = False):
        
        super().__init__(
            symbol = symbol,
            start = start,
            end = end,
            frequency = frequency,
            from_api = from_api
        )

        self.fiat = fiat
        self.from_ext = from_ext
        self.symbol_aux = self.symbol + self.fiat
        self.broker = "binance"

    def df_api(self):
        raise NotImplementedError
    
    def df_db(self):
        raise NotImplementedError
    
    def df_ext_api(self):
        raise NotImplementedError

    def update(self):
        raise NotImplementedError
    
    def update_df(self):
        assert all([ self.symbol, self.start, self.fiat ]), "Either symbol, start, or fiat missing."
        
        if self.from_api:
            return self.df_ext_api if self.from_ext else self.df_api
        else:
            return self.df_db


