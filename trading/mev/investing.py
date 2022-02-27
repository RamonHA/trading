import requests
import json
import pandas as pd
from datetime import datetime

from .base_mev import BaseMEV
from trading.func_aux import get, get_config

class Investing(BaseMEV):
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
        self.source = "investing"

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
        f = get("mev/mevs.json")
        if value in f["mevs"]:
            self._data = f["mevs"][ value ].get( "investing" , value)
        else:
            self._data = value 

    def df_api(self):

        url = "https://api.investing.com/api/financialdata/{}/historical/chart/?period=MAX&interval=P1M&pointscount=120"
        
        try:
            response = requests.get( url.format( self.data ) )
            assert response.status_code == 200, "Error in url request"
            data = json.loads(response.content)
        except Exception as e:
            raise Exception( e )

        data = data["data"]
        df = pd.DataFrame.from_dict(data)
        df.columns = ["date", "open", "high", "low", "close", "volume", "adj"]
        df["date"] = df["date"].apply(lambda x: datetime.fromtimestamp(x/1000).date().replace(day = 1) )

        return df