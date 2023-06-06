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
            source= "db", 
            token = None,
            interpolate = "linear",
        ):
        super().__init__(
            data = data,
            frequency = frequency,
            start = start,
            end = end,
            source = source,
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
        header = {
            "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36"
        }

        try:
            response = requests.get( url.format( self.data ), headers=header )
            assert response.status_code == 200, "Error in url request"
            data = json.loads(response.content)
        except Exception as e:
            raise Exception( e )

        data = data["data"]
        df = pd.DataFrame.from_dict(data)
        df.columns = ["date", "open", "high", "low", "close", "volume", "adj"]
        df["date"] = df["date"].apply(lambda x: datetime.fromtimestamp(x/1000).date().replace(day = 1) )

        return df