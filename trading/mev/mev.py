# Macroeconomic variables
import pandas as pd
from trading.assets import TimeSeries
from trading.func_aux import PWD, get

config = get( "mev/mevs.json" )
mevs = config[ "mevs" ]
modes = config[ "modes" ]

def mevs_to_csv(mode, frequency = "1m"):
    mev_df = pd.DataFrame()
    for i, v in modes[mode].items():
        df = MEV(
                data = i,
                source = v,
                frequency = "1m",
                source="db"
            ).df

        if "close" in df.columns:
            df = df[["close"]]
        else:
            if "Unnamed: 0" in df.columns:
                df.drop(columns = "Unnamed: 0", inplace = True)

        df.columns = [i]

        if len(mev_df) == 0:
            mev_df = df
        else:
            mev_df = pd.concat([
                mev_df, 
                df
            ], axis = 1)

    mev_df.sort_index(inplace = True, ascending=True)
    mev_df.dropna( inplace = True )
    mev_df.to_csv( PWD( "MEV/{}_{}.csv".format( mode, frequency ) ) )

def mevs(mode = "all", frequency = "1m", force = False):

    if force:
        mevs_to_csv( mode, frequency )
        
    try:
        df = pd.read_csv( PWD( "MEV/{}_{}.csv".format( mode, frequency ) ) )
    except:
        mevs_to_csv( mode, frequency )
        df = pd.read_csv( PWD( "MEV/{}_{}.csv".format( mode, frequency ) ) )
    
    df.set_index("date", inplace = True)

    return df
    

class MEV(TimeSeries):
    def __init__(
            self,
            data,
            source,
            frequency = None,
            start = None,
            end = None,
            source = "api",
            token = None,
            interpolate = "linear",
        ):
        """  
            source (str): inegi, sie (Banxico)
            source (str): db or api

        """
        super().__init__()

        self.frequency = frequency
        self.start = start
        self.end = end

        self.source = source
        self.data = data
        self.token = token
        self.source = source

        self.interpolate = interpolate

        self.set_mev(source)

        self.symbol = self.symbol_aux = self.mev.data

    def get_mev(self, source):        
        
        if source == "inegi":
            from .inegi import Inegi
            return Inegi

        elif source == "sie":
            from .sie import SIE
            return SIE

        elif source == "investing":
            from .investing import Investing
            return Investing
        
        elif source == "yahoo":
            from .base_mev import BaseMEV
            return BaseMEV

        else:
            raise ValueError("No {} source".format(source) )

    def set_mev(self, source):
        mev = self.get_mev(source)

        self.mev = mev(
            data = self.data,
            frequency = self.frequency,
            start = self.start,
            end = self.end,
            source = self.source,
            token = self.token,
            interpolate = self.interpolate,
        )

    
    @property
    def df(self):
        return self.mev.df

    @df.setter
    def df(self, value):
        self.mev.df = value

