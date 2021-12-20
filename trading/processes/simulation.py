from copy import deepcopy
import re
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
import json
import warnings

from trading.assets import Asset
from .base_process import BaseProcess
from trading.func_aux import PWD, folder_creation

def relative_time(end, time, frequency):
    period_analysis, interval_analysis = re.findall(r'(\d+)(\w+)', frequency)[0]
    period_analysis = int(period_analysis)

    if interval_analysis == "m":
        start = end - relativedelta(months = time*period_analysis) 
        start = start.replace(day = 1)
    elif interval_analysis == "w":
        start = end - timedelta(days = 7*time*period_analysis)
    elif interval_analysis == "d":
        start = end - timedelta(days = time*period_analysis ) 
    elif interval_analysis == "h":
        start = end - timedelta(seconds = 3600*time*period_analysis )

    return start

def ind_strategy(inst, end, time, frequency, function):
    instt = deepcopy( inst )

    start = relative_time(end, time, frequency)

    instt.df = instt.df.loc[ start:end ]

    if len(instt.df) == 0: return None

    return [ end, function(instt) ]

def strategy_dummy(
        asset,
        start_abs,
        end_abs,
        time,
        end_analysis,
        frequency,
        fiat,
        broker,
        function,
        from_ = "db",
        parallel = 0,

    ):

    start = relative_time( end_analysis[0][-1], time, frequency )

    inst = Asset( 
        asset, 
        start, 
        end_abs, 
        frequency = frequency, 
        fiat = fiat, 
        broker = broker, 
        from_ = from_, 
        sentiment = False
    )

    if inst.df is None or len(inst.df) <= 3: 
        warnings.warn("Error in strategy. Df import issue")
        return None

    if parallel == 0:
        r = [ ind_strategy( inst, end[-1], time, frequency, function ) for end in end_analysis ]

    return r


class Simulation(BaseProcess):
    def __init__(
            self,
            broker = "yahoo_asset",
            fiat = None,
            commission = None,
            assets = None,
            end = date.today(),
            simulations = 0,
        ):
        super().__init__(
            broker = broker, 
            fiat = fiat, 
            commission = commission,
            assets=assets,
            end = end
        )

        self.simulations = simulations

        self.pwd = PWD( "{}/results/{}/{}".format( self.broker, self.fiat, "{}" ) )

    def set_pwd_analysis(self, frequency, test_time, analysis, folder):
        aux_analysis = "_".join( list( analysis.keys() ) )

        aux = []
        for k, v in analysis.items():
            if v["type"] == "prediction" and "time" in v:
                aux.append( [v["time"]] )

            if "parameters" in v:
                if isinstance(v["parameters"], list):
                    aux.append( v["parameters"] )
                if isinstance(v["parameters"], dict):
                    aux.append(  list(v["parameters"].values()) )

            if "frequency" in v:
                aux.append([ v["frequency"] ])

        aux_param = "_".join( [ str(item) for s in aux for item in s ] )

        aux = [ v["best"] for k, v in analysis.items() if "best" in v]
        aux_best = "_".join( aux )

        if folder is None:
            self.pwd_analysis = self.pwd.format( "{}_{}/{}/{}_{}".format( frequency, test_time, aux_analysis, aux_param, aux_best ) )
        else:
            self.pwd_analysis = self.pwd.format( "{}_{}/{}/{}_{}/{}".format( frequency, test_time, aux_analysis, aux_param, aux_best, folder ) )

        folder_creation(self.pwd_analysis)
        
        self.pwd_analysis += "/{}"

    def start_end(self, test_time):
        if self.interval_analysis == "m":
            self.start = self.end - relativedelta(months = self.period_analysis*test_time*self.simulations - 1)
            self.start = self.start.replace(day = 1)
        elif self.interval_analysis == "w":
            self.start = self.end - timedelta(days = 7*self.simulations*self.period_analysis*test_time)
        elif self.interval_analysis == "d":
            self.start = self.end - timedelta(days = self.simulations*self.period_analysis*test_time)
        elif self.interval_analysis == "h":
            self.end = datetime.combine( self.end, datetime.min.time() )
            self.start = self.end - timedelta(seconds = 3600*self.simulations*self.period_analysis*test_time)            

    def analyze(
            self,
            frequency,
            test_time,
            analysis,
            save = True,
            run = True,
            folder = None,
            **kwargs
        ):
        self.test_time = test_time
        self.analysis = analysis
        self.frequency_analysis = frequency
        self.period_analysis, self.interval_analysis = re.findall(r'(\d+)(\w+)', frequency)[0]
        self.period_analysis = int( self.period_analysis )

        self.set_pwd_analysis( frequency, test_time, analysis, folder )        

        self.start_end(test_time)

        if run: self._analyze( test_time, save = save, **kwargs )
    
    def start_end_relative(self, simulation, test_time, verbose = True):
        if self.interval_analysis == "m":
            start = self.start + relativedelta(months = simulation*self.period_analysis*test_time)
            start = start.replace(day = 1)

            end = self.start + relativedelta(months = (simulation+1)*self.period_analysis*test_time)
            end -= timedelta(days = 1)

            end_analysis = start - timedelta(days = 1)
            # start_analisis = end_analysis - relativedelta( months = test_time*self.period_analysis )
        
        elif self.interval_analysis == "w":
            start = self.start + timedelta(days = 7*simulation*test_time*self.period_analysis)
            end = start + timedelta(days = 7*test_time*self.period_analysis)
            end_analysis = start

        elif self.interval_analysis == "d":
            start = self.start + timedelta( days = simulation*test_time*self.period_analysis )
            end = start + timedelta(days = test_time*self.period_analysis)
            end_analysis = start

        elif self.interval_analysis == "h":
            start = self.start + timedelta( seconds = simulation*test_time*self.period_analysis*3600 )
            end = start + timedelta( seconds = test_time*self.period_analysis*3600 ) 
            end_analysis = start

        return start, end, end_analysis

    def _analyze(
            self,
            test_time,
            save = True,
            **kwargs
        ):

        # self.assets_inst = [ Asset() for i in self.assets ]

        for simulation in range( self.simulations ):
            start, end, end_analysis = self.start_end_relative( simulation, test_time, verbose = True )

            self.results = self.strategy( end_analysis, **kwargs )

            if save:
                with open( self.pwd_analysis.format( "{}_{}_analysis.json".format( start, end ) ), "w" ) as fp:
                    json.dump( self.results, fp )
    
    def strategy_dummy(self):
        pass

    def _analyze_dummy(self,
            test_time,
            save = True,
            parallel = 0,
            **kwargs
        ):

        dates = [ self.start_end_relative( simulation, test_time, verbose = True ) for simulation in range(self.simulations) ]


        if parallel == 0:
            r = {}
            
