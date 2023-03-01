import pandas as pd
from datetime import datetime, date
import re
from dateutil import parser
import yfinance as yf

from trading.assets import TimeSeries
from trading.func_aux import PWD, get_assets

class BaseAsset(TimeSeries):
    def __init__(
        self, 
        symbol = "", 
        start = None, 
        end = datetime.today(), 
        frequency = "1d", 
        broker = "yahoo",
        fiat = None,
        source = "yahoo",

    ):
        super().__init__()

        self.broker = broker
        self.fiat = fiat 
        self.symbol = symbol 
        self.start = start
        self.end = end
        self.frequency = frequency
        self.source = source

        self.period, self.interval = re.findall(r'(\d+)(\w+)', frequency)[0] if frequency is not None else (None, None)
        self.period = int(self.period) if self.period is not None else None

        self.symbol_aux = f"{self.symbol}.{self.fiat}"
        # Fix variables
        self.default_source = "yahoo"

    @property
    def descr(self):
        if hasattr(self, "_descr"):
            return self._descr
        else:
            self.descr = self.get_descr()
            return self._descr
    
    @descr.setter
    def descr(self, value):
        self._descr = value

    def get_descr(self):
        return get_assets()[ self.broker ][ self.symbol.upper() ]

    @property
    def start(self):
        return self._start
    
    @start.setter
    def start(self, value):
        if value is None:
            self._start = None
        elif type(value) == datetime:
            self._start = value
        elif type(value) == date:
            self._start = datetime.combine(value, datetime.min.time())
        elif type(value) == str:
            self._start = parser.parse(value)
        else:
            raise ValueError("Start must be date, datetime, or str with valid format. Type {}.".format(type(value)))

    @property
    def end(self):
        return self._end

    @end.setter
    def end(self, value):
        if value is None:
            self._end = None
        elif type(value) == datetime:
            self._end = value
        elif type(value) == date:
            self._end = datetime.combine(value, datetime.min.time())
        elif type(value) == str:
            self._end = parser.parse(value)
        else:
            raise ValueError("End must be date, datetime, or str with valid format. Type {}.".format(type(value)))

    @property
    def symbol_aux(self):
        if hasattr(self, "_symbol_aux"):
            return self._symbol_aux
        else:
            self.symbol_aux = self.get_symbol_aux()
            return self._symbol_aux
    
    @symbol_aux.setter
    def symbol_aux(self, value):
        self._symbol_aux = value

    def get_symbol_aux(self):
        if self.fiat == "mx":
            return "{}.{}".format(self.symbol.upper(), self.fiat.upper()) if ".mx" not in self.symbol else self.symbol.upper()
        else:
            return self.symbol.upper()

    @property
    def df(self):
        if hasattr(self, "_df"):
            return self._df
        else:
            self.df = self.get()
            return self._df
    
    @df.setter
    def df(self, value):
        if isinstance(value, pd.DataFrame):
            self._df = value
        else:
            raise ValueError("Not Pandas DataFrame. Type {}".format(type(value)))

    def df_yahoo(self):
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
        
        df.reset_index(inplace = True)
        df.columns = [ i.lower() for i in df.columns ]
        df.set_index("date", inplace = True)

        return df

    def df_db_(self, verbose = True):
        aux = {
            'min':'minutes',
            'h':'hour',
            'd':'daily',
            'w':'weekly',
            'm':'monthly'
        }

        pwd = PWD("/{}/data/{}/{}.csv".format(self.broker, aux[ self.interval ], self.symbol_aux ))

        try:
            df = pd.read_csv( pwd )
            self.frequency_db = "1" + self.interval
        except:
            if verbose:
                print(
                    "{} csv does not exist in {} interval in path {}.".format(
                        self.symbol_aux, 
                        aux[self.interval],
                        pwd
                    )
                )
            return None
        
        if df is None or len(df) == 0: return None

        df.set_index( "date", inplace = True )
        # df.index = pd.to_datetime( df.index )

        return df

    def df_db(self,verbose = True):
        
        df = self.df_db_(verbose = verbose)

        if df is None or len(df) == 0: return None

        return df.loc[ str(self.start):str(self.end) ]

    def df_api(self):
        raise NotImplementedError
    
    def df_ext_api(self):
        raise NotImplementedError

    def update(self, value = "df", pwd = None, source = "yahoo"):
        
        aux = {
            'min':'minutes',
            'h':'hour',
            'd':'daily',
            'w':'weekly',
            'm':'monthly'
        }

        pwd = pwd if pwd is not None else PWD("/{}/data/{}/{}.csv".format(self.broker, aux[ self.interval ], self.symbol_aux ))
        if value == "df":
            df_source = self.get( self.default_source )
            if df_source is None or df_source.empty:
                raise ValueError( "Error downloading information from ", self.default_source )

            df_source.index = pd.to_datetime( df_source.index )

            df_db = self.df_db_()
            if df_db is None or len(df_db) == 0:
                df = df_source
            else:            
                df_db.index = pd.to_datetime( df_db.index )
                df = pd.concat( [ df_db, df_source ], axis = 0 )


            df.sort_index(inplace=True, ascending=True)

            df = df[~df.index.duplicated(keep='last')]
            
            self.save( 
                df,
                pwd
            )

        elif value == "sentiment":
            raise NotImplementedError
        
        else:
            raise ValueError("Update of {} not recognize".format( value ))

    def get(self, source = None):
        assert all([ self.symbol, self.start, self.fiat ]), "Either symbol, start, or fiat missing."
        
        if source is None: source = self.source

        df = {
            "yahoo":self.df_yahoo,
            "api":self.df_api,
            "ext_api":self.df_ext_api,
            "db":self.df_db
        }[ source ]()

        if df is None: return pd.DataFrame()

        # Maybe this will be done for all sources
        if source == "db" and self.period > 1:
            df = self.transform( df, self.frequency )

        return df if df is not None else pd.DataFrame()
    
    def refresh(self):
        # self.df = self.update_df()
        raise NotImplementedError

    def save(self, value, pwd = None):
        if isinstance( value, pd.DataFrame ):
            value.to_csv( pwd )
        elif isinstance( value, dict ):
            value.to_json( pwd )
        else:
            raise ValueError("Save to {} not recognize".format(value))
    
    def to_csv(self, value, pwd = None):

        if pwd is None:        
            aux = {
                'min':'minutes',
                'h':'hour',
                'd':'daily',
                'w':'weekly',
                'm':'monthly'
            }

            value.to_csv(
                PWD( 
                    "/{}/data/{}/{}.csv".format( 
                        self.broker, 
                        aux[ self.interval ],  
                        self.symbol_aux
                    ) 
                ) 
            )
        else:
            value.to_csv(
                PWD( 
                    pwd
                ) 
            )

    def to_json(self, value, pwd = None):
        raise NotImplementedError
    
    # Bot Functions

    def buy(self, positions):
        """ Positions to Buy 
        
            positions (dict): { asset:position }
        """
        return positions
    
    def sell(self, positions):
        """ Positions to Sell 

            positions (dict): { asset:position }
        """
        return positions

    def value(self):
        """ Value of Portfolio """
        raise NotImplementedError