from datetime import datetime
import yfinance as yf

from .base_asset import BaseAsset

class YahooAsset(BaseAsset):
    def __init__(
        self, 
        symbol, 
        start = None, 
        end = datetime.today(), 
        frequency = "1d", 
        fiat = "mx", 
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

        self.fiat = fiat.lower() if fiat is not None else None
        self.from_ext = from_ext
        self.symbol_aux = self.set_symbol_aux()
        self.broker = "yahoo_asset"
    
    def set_symbol_aux(self):
        if self.fiat == "mx":
            return "{}.{}".format(self.symbol.upper(), self.fiat.upper()) if ".mx" not in self.symbol else self.symbol.upper()
        else:
            return self.symbol.upper()
        # Integration of stocks from other countries

    def df_api(self):
        aux = { # 1m,2m,5m,15m,30m,60m,90m,1h, 1d (Default),5d,1wk,1mo,3mo
            'min':'1m',
            'h':'1h',
            'd':'1d',
            'w':'1wk',
            'm':'1mo',
            'q':'3mo'
        }

        if self.interval != "min":
            df = yf.download(self.symbol_aux, start = self.start, end = self.end, interval= aux[self.interval] ,progress=False)
    
        else:
            raise NotImplementedError
        
        df.columns = [ i.lower() for i in df.columns ]

        return df

    def df_api_aux(self):
        pass