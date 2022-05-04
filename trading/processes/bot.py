from datetime import date, datetime
import re
import json
import os

from requests import get

from .base_process import BaseProcess
from trading.func_aux import PWD, folder_creation, get_last_date_file
from trading.optimization import Optimization

class Bot(BaseProcess):
    def __init__(
            self,
            broker = "yahoo_asset",
            fiat = None,
            commission = None,
            assets = None,
            end = date.today(),
            subdivision = None,
            verbose = 0,
            **kwargs
        ):
        super().__init__(
            broker = broker, 
            fiat = fiat, 
            commission = commission,
            assets=assets,
            end = end,
            subdivision = subdivision,
            **kwargs
        )

        folder_creation( PWD( "{}/bots/{}".format( self.broker, self.fiat ) ) )
        self.pwd = PWD( "{}/bots/{}/{}".format( self.broker, self.fiat, "{}" ) )
        self.bot_date = str(datetime.today()).replace(":", " ").split(".")[0]

        self.resume = {
            "date":str(datetime.today()),
            "subdivision":subdivision,
            "comission":self.commission
        }
    
        self.asset = self.set_asset()()

        self.verbose = verbose

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
            test_time = None,
            folder = None,
            run = True,
            **kwargs
        ):
        self.analysis = analysis
        self.test_time = test_time
        self.frequency_analysis = frequency
        self.period_analysis, self.interval_analysis = re.findall(r'(\d+)(\w+)', frequency)[0]
        self.period_analysis = int( self.period_analysis )

        if run:
            self.results = self.strategy( self.end, **kwargs )

            analisis_aux = {}
            for j, k in analysis.items():
                analisis_aux[j] = {}
                for i, v in k.items():
                    if i == "function": continue
                    analisis_aux[ i ] = v

            self.resume["frequency"] = frequency
            self.resume["analysis"] = analisis_aux
            self.resume["results"] = {"analysis":self.results}

            try:
                with open( self.pwd.format( "{}.json".format(self.bot_date)  ) , "w") as fp:
                    json.dump( self.resume, fp )
            except Exception as e:
                print("Cannot dump json with exception {}.\n{}".format(e, self.resume))

    def ensure_results(self):
        if not hasattr(self, "results"):
            self.resume = self.past_resume()
            self.results = self.resume["results"]

    def optimize(
            self,
            balance_time, 
            time = 0,
            frequency = None,
            value = 0,
            exp_return = "mean",
            risk = "efficientfrontier",
            objective = "maxsharpe",
            limits = (0,1),
            min_qty = 0,
            **kwargs
        ):

        self.ensure_results()

        time = self.test_time if time == 0 else time
        frequency = self.frequency_analysis if frequency is None else frequency
        period, interval = re.findall(r'(\d+)(\w+)', frequency)[0]
        period = int(period)

        data = self.preanalisis( data = self.results["analysis"], **kwargs )

        if data is None: raise ValueError("No data to work with.")

        ll, ul = limits

        if min_qty != 0 or ll > 0 :
            data, ll = self.filter_by_qty(data, value=value, min_qty = min_qty, lower_lim = ll)
            limits = ( ll, ul )

        self.start, _  = self.start_end( end = self.end, interval=interval, period=period, simulations=1 , time=time)
        _, _, end_analysis, start_analysis = self.start_end_relative( test_time = time, analysis_time=balance_time, interval = interval, period = period, simulation = 1, verbose = True )

        opt = Optimization(
            assets= list( data.keys() ),
            start = start_analysis,
            end = end_analysis,
            frequency=frequency,
            exp_returns = exp_return if isinstance(exp_return, str) else data,
            risk = risk,
            objective=objective,
            broker = self.broker,
            fiat = self.fiat,
            from_ = kwargs.get("from_", "db"),
            interpolate=kwargs.get("interpolate", True),
            verbose = self.verbose,
            **kwargs
        )   

        self.allocation, self.qty, self.pct = opt.optimize( value, time = time, limits = limits )

        self.resume["optimization"] = {
            "risk":risk,
            "objective":objective,
            "time":time,
            "frequency":frequency,
            "balance_time":balance_time,
            "start":str(start_analysis),
            "end":str(end_analysis),
            "limits":limits,
            "value":value
        }

        self.resume["results"]["optimization"] = {
            "allocation":self.allocation,
            "qty":self.qty,
            "pct":self.pct
        }

        with open( self.pwd.format( "{}.json".format(self.bot_date)  ) , "w") as fp:
            json.dump( self.resume, fp )

        return self.allocation, self.qty, self.pct

    def buy(self, positions, **kwargs):
        return self.asset.buy( positions, **kwargs )
    
    def sell(self, positions, **kwargs):
        """ Returns orders that were not closed (no sold) """
        return self.asset.sell( positions, **kwargs )

    def past_resume(self):
        
        json_files = get_last_date_file( self.pwd[:-3], file="json" )
        
        if len(json_files) == 0: return None

        print("File to check is ", json_files)

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

    
