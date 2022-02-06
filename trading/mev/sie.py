import requests
import json
import pandas as pd


from .base_mev import BaseMEV
from trading.func_aux import get_assets, get_config

class SIE(BaseMEV):
    def __init__(
            self, 
            data, 
            frequency = None,
            start = None,
            end = None,
            from_= "db", 
            token = None,
            interpolate = "linear",
        ):
        super().__init__(
            data = data,
            frequency = frequency,
            start = start,
            end = end,
            from_ = from_,
            interpolate = interpolate
        )
        self.source = "sie"

        self.data = data

        if token is not None:
            self.token = token
        else:
            self.token = get_config()["sie"]["api_key"]

    @property
    def data(self):
        return self._data 
    
    @data.setter
    def data(self, value):
        if "sie" not in get_assets():
            self._data = value
        else:
            self._data = get_assets()["sie"].get( value, value )

    def df_api(self):

        url = 'https://www.banxico.org.mx/SieAPIRest/service/v1/series/{}/datos?token={}'
        
        try:
            response = requests.get( url.format( self.data, self.token ) )
            assert response.status_code == 200, "Error in url request"
            content = json.loads(response.content)
            series = content['bmx']['series'][0]['datos']
        except Exception as e:
            raise Exception( e )

        series = pd.DataFrame(series)
        series["dato"] = series["dato"].str.replace( ",", "" )
        series["dato"] = pd.to_numeric( series["dato"], errors = "coerce" )
        series.rename(columns = {"fecha":"date", "dato":self.data_orig}, inplace = True)
        
        def format(s):
            s = s.split("/")
            a = s[2]
            m = s[1]
            d = s[0]
            return "{}-{}-{}".format(a, m, d)

        series["date"] = pd.to_datetime( series["date"].apply(lambda x: format(x)) )

        return series