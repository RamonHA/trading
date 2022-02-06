
import requests
import json
import pandas as pd


from .base_mev import BaseMEV
from trading.func_aux import get_assets, get_config

class Inegi(BaseMEV):
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
        self.source = "inegi"

        self.data = data

        if token is not None:
            self.token = token
        else:
            self.token = get_config()["inegi"]["api_key"]

    @property
    def data(self):
        return self._data 
    
    @data.setter
    def data(self, value):
        if "inegi" not in get_assets():
            self._data = value
        else:
            self._data = get_assets()["inegi"].get( value, value )

    def df_api(self):

        url = 'https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR/{}/es/0700/false/BISE/2.0/{}?type=json'
        
        try:
            response = requests.get( url.format( self.data, self.token ) )
            assert response.status_code == 200, "Error in url request"
            content = json.loads( response.content )
            series = content["Series"][0]["OBSERVATIONS"]

        except Exception as e:
            raise Exception( e )


        series = pd.DataFrame(series)

        def format(s):
            s = s.split("/")
            a = s[0]
            m = int(s[1])*3 
            return "{}-{}-{}".format(a, m, 1)

        series.rename( columns = {"TIME_PERIOD":"date", "OBS_VALUE":self.data_orig}, inplace = True )
        series[self.data_orig] = pd.to_numeric( series[self.data_orig], errors = "coerce" )
        series["date"] = pd.to_datetime( series["date"].apply(lambda x: format(x)) )

        return series[[ "date", self.data_orig ]]