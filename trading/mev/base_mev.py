import pandas as pd

from trading.assets import TimeSeries
from trading.func_aux import PWD

class BaseMEV(TimeSeries):
    def __init__(self, from_ = "db"):
        super().__init__()

        self.from_ = from_

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
        return {
            "api":self.df_api,
            "db":self.df_db
        }[ self.from_ ]()

    def df_db(self):
        raise NotImplementedError
    
    def df_api(self):
        raise NotImplementedError

    def update(self, value = "df", pwd = None, from_ = "api"):
        self.from_ = from_
        aux = {
            'min':'minutes',
            'h':'hour',
            'd':'daily',
            'w':'weekly',
            'm':'monthly'
        }

        pwd = pwd if pwd is not None else PWD("/MEV/{}/{}/{}.csv".format(self.source, aux[ self.interval ], self.data ))

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