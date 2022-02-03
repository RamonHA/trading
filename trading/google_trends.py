# Google Trends
from pytrends import dailydata
from pytrends.request import TrendReq
import pandas as pd
from datetime import date, datetime
from dateutil import parser
import time
import re

class GoogleTrend():
    def __init__(
            self,
            keywords = [],
            start = date(2000,1,1),
            end = date.today(),
            frequency = "1m",
            from_ = "api",
            **kwargs
        ):

        self.keywords = keywords
        self.start = self.ensure_date(start)
        self.end = self.ensure_date(end)
        self.frequency = frequency
        self.period, self.interval = re.findall(r'(\d+)(\w+)', frequency)[0]
        self.period = int(self.period)
        self.from_ = from_

        self.__dict__.update( kwargs )
    
    def ensure_date(self, value):
        if type(value) not in [ date, datetime ]:
            value = parser.parse(value)

        return date

    @property
    def df(self):
        if hasattr(self, "_df"):
            return self._df
        else:
            self.df = self.get()
            return self._df
    
    @df.setter
    def df(self, value):
        self._df = value

    def get(self):
        if self.from_ == "db":
            return self.df_db()
        else:
            return {
                "m":self.month
            }[ self.interval ]()
    
    def df_db(self):
        raise NotImplementedError

    def month(self):
        df = pd.DataFrame()

        for keyword in self.keywords:
            data = dailydata.get_daily_data(
                keyword, 
                self.start.year, 
                self.start.month, 
                self.end.year, 
                self.end.month, 
                geo = "",
                verbose = False,
                wait_time = 20
            )

            df = pd.concat([ df, data[keyword] ], axis = 1)

            time.sleep(1)



