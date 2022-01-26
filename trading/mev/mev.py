# Macroeconomic variables

from trading.assets import TimeSeries

class MEV(TimeSeries):
    def __init__(
            self,
            data,
            source,
            frequency = None,
            start = None,
            end = None,
            from_ = "api",
            token = None
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

        self.set_mev(source)

        self.symbol_aux = self.mev.data

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
            token = self.token
        )

    
    @property
    def df(self):
        return self.mev.df

    @df.setter
    def df(self, value):
        self.mev.df = value

