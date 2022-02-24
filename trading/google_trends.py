# Google Trends
from dataclasses import dataclass
from pytrends import dailydata
from pytrends.request import TrendReq
import pandas as pd
from datetime import date, datetime
from dateutil import parser
import time
import re

from trading.func_aux import PWD, folder_creation

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

        """  

            cat: Default = 0 ("all categories"). See: https://github.com/pat310/google-trends-api/wiki/Google-Trends-Categories

        """

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

        return value

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
            df = {
                "m":self.monthly,
                "d":self.daily
            }[ self.interval ]()

            self.update( df )

            return df

    def update(self, df):

        pwd = PWD( "/sentiment/google_trends/{}".format( 
                {
                    "m":"monthly",
                    "d":"daily",
                    "h":"hourly"
                }[ self.interval ] 
            ) 
        )
        
        folder_creation(pwd)

        aux = {
            "m":"monthly",
            "d":"daily",
            "h":"hourly"
        }[ self.interval ] 

        for c in df.columns: df[[c]].to_csv( PWD( "/sentiment/google_trends/{}/{}.csv".format( aux , c) ) )

    def df_db_indv(self, pwd):
        df = pd.read_csv( pwd )

        df.set_index("date", inplace = True)

        return df

    def df_db(self):

        pwd = PWD( "/sentiment/google_trends/{}/{}.csv".format( 
                {
                    "m":"monthly",
                    "d":"daily",
                    "h":"hourly"
                }[ self.interval ] ,
                "{}"
            ) 
        )

        df = pd.DataFrame()
        for k in self.keywords:
            data = self.df_db_indv( pwd.format(k) )
            df = pd.concat( [df, data], axis = 1 )
        
        return df


    def hourly(self):
        pytrends = TrendReq()

        df = pytrends.get_historical_interest(
            self.keywords, 
            year_start=self.start.year, month_start=self.start.month, day_start=self.start.day, hour_start=self.start.hour, 
            year_end=self.end.year, month_end=self.end.month, day_end=self.end.hour, hour_end=self.end.hour, 
            cat=0 if not hasattr(self, "cat") else self.cat, 
            sleep = self.sleep if hasattr(self, "sleep") else 5
        )

        return df[ self.keywords ]

    def daily(self):
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

        return df
    
    def monthly(self):
        pytrends = TrendReq()

        pytrends.build_payload(self.keywords, timeframe='all', cat=0 if not hasattr(self, "cat") else self.cat)

        df = pytrends.interest_over_time()

        if len(df) == 0: 
            return pd.DataFrame()

        return df.loc[ self.start:self.end ][ self.keywords ]


