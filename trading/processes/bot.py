from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import re
import json
import pandas as pd

from .base_process import BaseProcess
from trading.func_aux import PWD, folder_creation, get_last_date_file
from trading.optimization import Optimization
from trading import Asset

class Bot(BaseProcess):
    def __init__(
            self,
            name,
            broker = "yahoo_asset",
            fiat = None,
            assets = None,
            end = datetime.today(),
            subdivision = None,
            verbose = 0,
            account = None,
            **kwargs
        ):
        super().__init__(
            broker = broker, 
            fiat = fiat, 
            commission = 0,
            assets=assets,
            end = end,
            subdivision = subdivision,
            **kwargs
        )

        self.name = name
        folder_creation( PWD( "{}/bots/{}/{}".format( self.broker, self.fiat, self.name ) ) )
        self.pwd = PWD( "{}/bots/{}/{}/{}".format( self.broker, self.fiat, self.name, "{}" ) )
        self.bot_date = self.clean_date( self.end )

        self.account = account

        self.resume = {
            "date":str(self.end),
            "subdivision":subdivision,
            # "comission":self.commission
        }
    
        self.asset = self.set_asset()()

        self.verbose = verbose

        self.cache = {}

    def clean_date(self, d):
        return str(d).replace(":", " ").split(".")[0]

    def set_asset(self):
        if self.broker == "binance":
            from trading.assets.binance import Binance
            asset = Binance
        elif self.broker == "bitso":
            from trading.assets.bitso import Bitso
            asset = Bitso
        else:
            from trading.assets.base_asset import BaseAsset
            asset = BaseAsset
        
        return asset
    
    def analyze(
            self,
            frequency,
            analysis,
            run = True,
            **kwargs
        ):
        self.analysis = analysis
        self.frequency_analysis = frequency
        self.period_analysis, self.interval_analysis = re.findall(r'(\d+)(\w+)', frequency)[0]
        self.period_analysis = int( self.period_analysis )

        self.analysis_params = kwargs

        if run:
            self._analyze( **kwargs )

    def _analyze(self, **kwargs):

        self.results = self.strategy( self.end, **kwargs )

        analisis_aux = {}
        for j, k in self.analysis.items():
            analisis_aux[j] = {}
            for i, v in k.items():
                if i == "function": continue
                analisis_aux[ i ] = v

        self.resume["frequency"] = self.frequency_analysis
        self.resume["analysis"] = analisis_aux
        self.resume["results"] = {"analysis":self.results}

        # No es realmente necesario que este guardando los resultados de los analisis como tal

        # self.last_analysis = self.pwd.format( 
        #     "{}.json".format( 
        #         self.clean_date( datetime.today() )
        #     )  
        # )

        # try:
        #     with open( self.last_analysis , "w") as fp:
        #         json.dump( self.resume, fp )
        # except Exception as e:
        #     print("Cannot dump json with exception {}.\n{}".format(e, self.resume))

    def ensure_results(self):
        if not hasattr(self, "results"):
            self.resume = self.past_resume()
            self.results = self.resume["results"]["analysis"]
            self.bot_date = self.cache["past_resume"].split(".")[0]

    def optimize(
            self,
            balance_time, 
            frequency = None,
            value = 0,
            exp_return = "mean",
            risk = "efficientfrontier",
            objective = "maxsharpe",
            limits = (0,1),
            min_qty = 0,
            run = True,
            **kwargs
        ):

        # self.ensure_results()

        frequency = self.frequency_analysis if frequency is None else frequency
        period, interval = re.findall(r'(\d+)(\w+)', frequency)[0]
        period = int(period)

        kwargs.update(
            {
                "balance_time":balance_time,
                "value":value,
                "exp_return":exp_return,
                "risk":risk,
                "objective":objective,
                "limits":limits,
                "min_qty":min_qty,
                "period":period,
                "interval":interval
            }
        )

        self.optimize_params = kwargs

        if run:
            self._optimize( **kwargs )

    def _optimize(self, **kwargs):

        data = self.preanalisis( data = self.results, **kwargs )

        if data is None: raise ValueError("No data to work with.")

        ll, ul = kwargs["limits"]

        if kwargs["min_qty"] != 0 or ll > 0 :
            data, ll = self.filter_by_qty(data, value=kwargs["value"], min_qty = kwargs["min_qty"], lower_lim = ll)
            limits = ( ll, ul )

        start_analysis = self.end - relativedelta( 
            **{
                {
                   "min":"minutes",
                   "h":"hours",  
                   "d":"days", 
                   "w":"weeks",
                   "m":"months"
                }[ kwargs["interval"] ]:kwargs["balance_time"]*kwargs["period"]
            }
        )

        opt = Optimization(
            assets= list( data.keys() ),
            start = start_analysis,
            end = self.end,
            frequency=kwargs["frequency"],
            exp_returns = kwargs["exp_return"] if isinstance(kwargs["exp_return"], str) else data,
            risk = kwargs["risk"],
            objective= kwargs["objective"],
            broker = self.broker,
            fiat = self.fiat,
            from_ = kwargs.get("from_", "db"),
            interpolate=kwargs.get("interpolate", True),
            verbose = self.verbose,
            **kwargs
        )   

        self.allocation, self.qty, self.pct = opt.optimize( kwargs["value"], time = kwargs["time"], limits = limits )

        self.resume["optimization"] = {
            "risk":kwargs["risk"],
            "objective":kwargs["objective"],
            "frequency":kwargs["frequency"],
            "balance_time":kwargs["balance_time"],
            "start":str(start_analysis),
            "end":str(self.end),
            "limits":limits,
            "value":kwargs["value"]
        }

        self.resume["results"]["optimization"] = {
            "allocation":self.allocation,
            "qty":self.qty,
            "pct":self.pct
        }

        self.resume["choose"] = self.qty

        # with open( self.pwd.format( "{}.json".format(self.bot_date)  ) , "w") as fp:
        #     json.dump( self.resume, fp )

        # return self.allocation, self.qty, self.pct

    def choose(self, value, filter, filter_qty, allocation = 1, source = "db", run = True ):
        """  

        """
        
        if filter_qty >= 1:
            if type(allocation) in [ int, float ]:
                assert filter_qty*allocation > 1, "The quantity of filter_qty times allocation cannot go above 1."
        
        # Add more filter

        self.choose_params = { 
            "value":value,
            "filter":filter, 
            "filter_qty":filter_qty,
            "allocation":allocation,
            "source": source
        }
    
    def _choose(self, **kwargs):
        data = self.filter( data = self.results, **kwargs )
        assets = list(data.keys())

        allocation = kwargs.get("allocation")
        filter_qty = kwargs.get("filter_qty")
        source = kwargs.get("source")
        value = kwargs.get("value")

        if filter_qty >= 1:
            if type(allocation) in [ int, float ]:
                pct = { a:allocation for a in assets } 

        start = self.end - relativedelta( 
            **{
                {
                   "min":"minutes",
                   "h":"hours",  
                   "d":"days", 
                   "w":"weeks",
                   "m":"months"
                }[ kwargs["interval"] ]:2
            }
        )

        qty = {}
        if source not in ["api"]:
            for i, v in pct.items():
                inst = Asset(
                    i,
                    start = start,
                    end = self.end,
                    frequency=self.frequency_analysis,
                    broker = self.broker,
                    fiat = self.fiat,
                    from_ = source
                )

                if inst.df is None or len(inst.df) == 0: continue

                price = inst.df["close"].iloc[-1]
                qty[i] = (value*v) / price

        self.resume["choose"] = self.qty
        

    def run(self):
        pass

    def buy(self, positions, **kwargs):
        return self.asset.buy( positions, **kwargs )
    
    def sell(self, positions, **kwargs):
        """ Returns orders that were not closed (no sold) """
        return self.asset.sell( positions, **kwargs )

    def past_resume(self):
        
        json_files = get_last_date_file( self.pwd[:-3], file="json" )
        
        if len(json_files) == 0: return None

        print("File to check is ", json_files)
        self.cache["past_resume"] = json_files

        with open( self.pwd.format( json_files ), "r" ) as fp:
            json_files = json.load(fp)
        
        print("With following information:\n", json_files)

        return json_files

    def positions_to_close(self, open_positions):
        return list( set( open_positions ) - set( self.allocation ) )
    
    def position_to_open(self, open_positions):
        return list( set( self.allocation ) - set( open_positions ) )
    
    def run(self):

        past_resume = self.past_resume()

        if past_resume is None or "final_real_allocation" not in past_resume:
            open_positions = {}
        else:
            open_positions = past_resume["final_real_allocation"].keys()

        ptc = self.positions_to_close( open_positions )

        no_sell = self.sell( { i:v for i, v in self.qty.items() if i in ptc} )

        pto = self.position_to_open( open_positions )

        real_bougth = self.buy( { i:v for i, v in self.qty.items() if i in pto} )

        real_bougth.update( { i:v for i, v in open_positions.items() if i in no_sell } )

        self.resume["final_real_allocation"] = real_bougth

        with open( self.pwd.format( "{}.json".format(self.bot_date)  ), "w" ) as fp:
            json.dump( self.resume, fp )

    
