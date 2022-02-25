# Macroeconomic variables
import pandas as pd
from trading.assets import TimeSeries
from trading.func_aux import PWD

# Easy path for now
mev = {
        "bonos":{"sie":"SF117753"},
        "cetes":{"sie":"SF43936"},
        "consumo frecuente":{"investing":27260},         # 27260
        "consumo no basico":{"investing":27259},         # 27259
        "dax":{"yahoo":"^GDAXI"},
        "desempleo":{"inegi":"6200093973", "sie":"SL1"},
        "financiero":{"investing":27262},                # 27262, RT 27240
        "industrial":{"investing":27242},                # 27258, RT 27242
        "inpc":{"sie":"SP1"},                            # SP1
        "er":{"yahoo":"MXN=X"},
        "inflacion":{"sie":"SP68257"},
        "intereses":{"sie":"SF3338"},
        "materiales":{"investing":27265},               # 27265, RT 27243
        "mexbol":{"yahoo":"^MXX", "investing":27254},
        "petroleo":{"sie":"SP67185", "yahoo":"CL=F"},
        "pib":{"inegi":"6207061899", "sie":"SR16643"},
        "mexbol":{"yahoo":"^MXX"},
        "nikkei":{"yahoo":"^N225"},
        "reservas internacionales":{"sie":"SF43707"},
        "salud":{"investing":27263},
        "s&p500":{"yahoo":"^GSPC"},
        "sse":{"yahoo":"000001.SS"},
        "telecomunicaciones":{"investing":27266},
        "tsx":{"yahoo":"^GSPTSE"},
    }

modes = {
    "all":[
            ("petroleo", "yahoo"),
            ("er", "yahoo"),
            ("inflacion", "sie"),
            ("pib", "inegi"),
            ("cetes", "sie"),
            ("inpc", "sie"),
            ("reservas internacionales", "sie"),
            ("desempleo", "inegi"),
            
            ("s&p500", "yahoo"),
            ("sse", "yahoo"),
            ("nikkei", "yahoo"),
            ("tsx", "yahoo"),
            ("dax", "yahoo"),

            ("industrial", "investing"),
            ("materiales", "investing"),
            ("financiero", "investing"),
            ("consumo frecuente", "investing"),
            ("consumo no basico", "investing"),
            ("salud", "investing"),
            ("telecomunicaciones", "investing"),

            ("mexbol", "yahoo")
    ]
}

def mevs_to_csv(mode, frequency = "1m"):
    mev_df = pd.DataFrame()
    for i, v in modes[mode]:
        df = MEV(
                data = i,
                source = v,
                frequency = "1m",
                from_="db"
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
            from_ = "api",
            token = None,
            interpolate = "linear",
        ):
        """  
            source (str): inegi, sie (Banxico)
            from_ (str): db or api

        """
        super().__init__()

        self.frequency = frequency
        self.start = start
        self.end = end

        self.from_ = from_
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
            from_ = self.from_,
            token = self.token,
            interpolate = self.interpolate,
        )

    
    @property
    def df(self):
        return self.mev.df

    @df.setter
    def df(self, value):
        self.mev.df = value

