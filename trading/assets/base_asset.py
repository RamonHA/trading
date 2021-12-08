import pandas as pd
from datetime import datetime, date
import re
from dateutil import parser

from trading.func_aux import PWD

class BaseAsset():
    def __init__(
        self, 
        symbol, 
        start = None, 
        end = datetime.today(), 
        frequency = "1d", 
        from_api = True,
        sentiment = False,
        social_media = None,
    ):
        self.symbol = symbol.lower()
        self.start = start
        self.end = end
        self.frequency = frequency
        self.from_api = from_api

        self.period, self.interval = re.findall(r'(\d+)(\w+)', frequency)[0] if frequency is not None else (None, None)
        self.period = int(self.period) if self.period is not None else None

    @property
    def start(self):
        return self._start
    
    @start.setter
    def start(self, value):
        if value is None:
            self._inicio = None
        elif type(value) == datetime:
            self._inicio = value
        elif type(value) == date:
            self._inicio = datetime.combine(value, datetime.min.time())
        elif type(value) == str:
            self._inicio = parser.parse(value)
        else:
            raise ValueError("Start must be date, datetime, or str with valid format. Type {}.".format(type(value)))

    @property
    def end(self):
        return self._end

    @end.setter
    def end(self, value):
        if value is None:
            self._fin = None
        elif type(value) == datetime:
            self._fin = value
        elif type(value) == date:
            self._fin = datetime.combine(value, datetime.min.time())
        elif type(value) == str:
            self._fin = parser.parse(value)
        else:
            raise ValueError("End must be date, datetime, or str with valid format. Type {}.".format(type(value)))

    @property
    def df(self):
        if hasattr(self, "_df"):
            return self._df
        else:
            print("por configurarla")
            self.df = self.update_df()
            return self._df
    
    @df.setter
    def df(self, value):
        if isinstance(value, pd.DataFrame):
            self._df = value
        elif value is None:
            self._df = value
        else:
            raise ValueError("Not Pandas DataFrame. Type {}".format(type(value)))

    def df_db(self):
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
        except:
            print(
                "{} csv does not exist in {} interval in path {}.".format(
                    self.symbol_aux, 
                    aux[self.interval],
                    pwd
                )
            )
            return None
        
        df.set_index( "date", inplace = True )
        df.index = pd.to_datetime( df.index )

        return df.loc[ str(self.start):str(self.end) ]

    def df_api(self):
        raise NotImplementedError
    
    def df_ext_api(self):
        raise NotImplementedError

    def update(self, value = "df", pwd = None):
        self.from_api = True

        if value == "df":
            self.save( 
                self.df,
                pwd
            )
        elif value == "sentiment":
            raise NotImplementedError
        
        else:
            raise ValueError("Update of {} not recognize".format( value ))

    def update_df(self):
        print("En pdate")
        assert all([ self.symbol, self.start, self.fiat ]), "Either symbol, start, or fiat missing."
        
        if self.from_api:
            return self.df_ext_api() if self.from_ext else self.df_api()
        else:
            return self.df_db()
    
    def refresh(self):
        self.df = self.update_df()

    def save(self, value, pwd = None):
        if isinstance( value, pd.DataFrame ):
            self.to_csv( value, pwd )
        elif isinstance( value, dict ):
            self.to_json( value, pwd )
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