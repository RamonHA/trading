from alpha_vantage.cryptocurrencies import CryptoCurrencies
from datetime import datetime

from trading.assets.base_asset import BaseAsset
from trading.func_aux import PWD, time_diff, get_config

class Bitso(BaseAsset):

    def __init__(
        self, 
        symbol = None, 
        start = None, 
        end = datetime.today(), 
        frequency = "1d", 
        broker = "bitso",
        fiat = "MXN", 
        from_ = "ext_api",
        sentiment = False,
        social_media = None,
    ):
        super().__init__(
            symbol = symbol,
            start = start,
            end = end,
            frequency = frequency,
            from_ = from_,
            sentiment=sentiment,
            social_media=social_media
        )

        self.symbol = self.symbol.upper()

        self.fiat = {
            "mx":"MXN",
            None:"MXN",
            "MXN":"MXN"
        }.get( fiat, fiat.upper() )

        self.symbol_aux = self.symbol + self.fiat
        self.broker = broker

        if frequency is not None:
            assert self.interval not in ["min", "h", "s"], "With Bitso there isnt still frequency lower than 1d"

    def alpha_vantage(self):
        return CryptoCurrencies(get_config()["alpha_vantage"]["api_key"], output_format='pandas')

    def df_api(self):
        raise NotImplementedError

    def df_ext_api(self):

        cr = self.alpha_vantage()

        data, meta_data = cr.get_digital_currency_daily(self.symbol, self.fiat)

        data.drop(columns = [i for i in data.columns if 'USD' in i], inplace = True)

        data.columns = ['open', 'high', 'low', 'close', 'volume']

        data.sort_index(ascending=True, inplace=True)

        return data.loc[ str(self.start):str(self.end) ]

    # Bot Functions

