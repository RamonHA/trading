import pandas as pd
import re
import yfinance as yf
from trading.assets import TimeSeries
from trading.func_aux import PWD

class BaseMEV(TimeSeries):
    def __init__(
            self, 
            data, 
            frequency = None,
            start = None,
            end = None,
            from_ = "db",
            **kwargs
        ):
        super().__init__()

        self.source = "yahoo"
        self.data_orig = data
        self.data = data
        self.from_ = from_
        self.frequency = frequency
        self.start = start
        self.end = end
        if frequency is not None:
            self.period, self.interval = re.findall(r'(\d+)(\w+)', self.frequency)[0]

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
        df = {
            "api":self.df_api,
            "db":self.df_db
        }[ self.from_ ]()

        if self.from_ == "db": return df

        if self.frequency is not None:
            df = self.transform(df, self.frequency)

        else:
            df.set_index("date", inplace = True)

        return df

    def df_db(self, verbose = True):
        aux = {
            'min':'minutes',
            'h':'hour',
            'd':'daily',
            'w':'weekly',
            'm':'monthly'
        }

        pwd = PWD(
            "MEV/{}/{}/{}.csv".format(
                self.source, 
                aux[ self.interval ], 
                self.data_orig 
            )
        )

        try:
            df = pd.read_csv( pwd )
        except:
            if verbose:
                print(
                    "{} csv does not exist in {} interval in path {}.".format(
                        self.data_orig, 
                        aux[self.interval],
                        pwd
                    )
                )
            return None
        
        if "date" not in df.columns:
            col = list(df.columns)
            col[0] = "date"
            df.columns = col

        df.set_index( "date", inplace = True )

        return df
    
    def df_api(self):
        """  
            Yahoo function
        """
        aux = { # 1m,2m,5m,15m,30m,60m,90m,1h, 1d (Default),5d,1wk,1mo,3mo
            'min':'1m',
            'h':'1h',
            'd':'1d',
            'w':'1wk',
            'm':'1mo',
            'q':'3mo'
        }

        if self.interval != "min":
            df = yf.download(self.data,  interval = aux[ self.interval ], period = "max", progress=False)
        else:
            raise NotImplementedError
        
        df.reset_index(inplace = True)
        df.columns = [ i.lower() for i in df.columns ]
        df.set_index("date", inplace = True)

        return df

    def update(self, value = "df", pwd = None, from_ = "api"):
        self.from_ = from_
        aux = {
            'min':'minutes',
            'h':'hour',
            'd':'daily',
            'w':'weekly',
            'm':'monthly'
        }

        pwd = pwd if pwd is not None else PWD("MEV/{}/{}/{}.csv".format(self.source, aux[ self.interval ], self.data_orig ))

        if value == "df":
            self.save( 
                self.df,
                pwd
            )
        elif value == "sentiment":
            raise NotImplementedError
        
        else:
            raise ValueError("Update of {} not recognize".format( value ))

    def save(self, value, pwd = None):

        if isinstance( value, pd.DataFrame ):
            value.to_csv( pwd )
        elif isinstance( value, dict ):
            value.to_json( pwd )
        else:
            raise ValueError("Save to {} not recognize".format(value))