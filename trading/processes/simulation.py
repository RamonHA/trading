from copy import deepcopy
import re
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
import json
import pandas as pd
import warnings

from trading.assets import Asset
from .base_process import BaseProcess
from trading.func_aux import PWD, folder_creation
from trading.optimization import Optimization

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
            realistic = 0,
            subdivision = None,
            **kwargs
        ):
        """  
            realistic (int): How realisitic to drive the simulation
                            0: Only consider a realistic allocation
                                Will drive the portfolio value to 0
                                And performance is measure with absolute percentage retunr
                            1: Allocate a portfolio. Asume buy/sell order are fullfilled inmediatly
                            2: Will considered volume of transaction to determine whether orders 
                                are fullfilled correctly.
                                Market characterization.
        """
        super().__init__(
            broker = broker, 
            fiat = fiat, 
            commission = commission,
            assets=assets,
            end = end,
            subdivision = subdivision,
            **kwargs
        )

        self.simulations = simulations
        self.realistic = realistic

        self.pwd = PWD( "{}/results/{}/{}".format( self.broker, self.fiat, "{}" ) )

    

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

        self.start, self.end = self.start_end(self.end, test_time, self.interval_analysis, self.period_analysis, self.simulations)

        if run: self._analyze( test_time, save = save, **kwargs )

    def _analyze(
            self,
            time,
            save = True,
            **kwargs
        ):

        if self.verbose > 0:
            self.print_func("Analyze")

        # self.assets_inst = [ Asset() for i in self.assets ]

        for simulation in range( self.simulations ):
            start, end, end_analysis, _ = self.start_end_relative( time, 0, self.interval_analysis, self.period_analysis, simulation=simulation, verbose = True )

            if self.verbose > 1:
                self.print_for( "{} {}".format( start, end) )

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
            run = True,
            **kwargs
        ):
        """  
            balance_time (int): Time considered to optimize a portfolio
            time (int): Default = 0
                        Time considered to optimize to portfolio to (similat to test_time)
            
        """
        
        time = self.test_time if time == 0 else time
        frequency = self.frequency_analysis if frequency is None else frequency

        if value > 0 and self.realistic == 0:
            self.realistic = 1

        self.pwd_balance = self.pwd_analysis.format( 
            "{}_{}_{}_{}_{}".format( risk, objective, time, frequency, balance_time )         
        )

        folder_creation( self.pwd_balance )

        self.pwd_balance += "/{}"

        if run:
            self._optimize(
                time = time, 
                frequency = frequency, 
                balance_time = balance_time, 
                value = value,
                exp_return = exp_return,
                risk = risk,
                objective = objective,
                limits = limits,
                **kwargs
            )

    def _optimize(
            self, 
            time, 
            frequency, 
            balance_time, 
            value = 0,
            exp_return = "mean",
            risk = "efficientfrontier",
            objective = "maxsharpe",
            limits = (0,1),
            **kwargs
        ):

        if self.verbose > 0: self.print_func( "Optimize" )

        if ( value != 0 and self.realistic == 0 ):
            warnings.warn("Value of portfolio is set to 0 to run simultion. Priority of value over realistic")
            self.realistic = 1
        
        period, interval = re.findall(r'(\d+)(\w+)', frequency)[0]
        period = int(period)

        tr = 1

        self.df = []

        for simulation in range( self.simulations ):
            start, end, end_analysis, start_analysis = self.start_end_relative( test_time = time, analysis_time=balance_time, interval = interval, period = period, simulation = simulation, verbose = True )

            if self.verbose > 1:
                self.print_for( "Opt for {} {}".format(start, end) )

            data = self.preanalisis(
                pwd = self.pwd_analysis.format( "{}_{}_analysis.json".format( start, end ) ),
                # filter = kwargs.get("filter", "all"),
                **kwargs
            )

            if data is None:
                raise ValueError("No data to work with. Pwd".format( self.pwd_analysis.format( "{}_{}_analysis.json".format( start, end ) ) ))

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
                verbose = self.verbose
            )   

            allocation, qty, pct = opt.optimize( value, time = time, limits = limits )

            with open( self.pwd_balance.format( "{}_{}.json".format( start, end ) ), "w" ) as fp:
                json.dump(
                    {
                        "allocation":allocation,
                        "qty":qty,
                        "pct":pct
                    },
                    fp
                )
            
            if allocation is None: continue

            tr_aux = self.test(
                assets= pct if self.realistic > 0 else allocation,
                start = start,
                end = end
            )
        

            tr *= ( 1+tr_aux )
            value *= (1+tr_aux)
        
            self.df.append(
                [start, end, tr_aux, tr, value]
            )
        
        self.df = pd.DataFrame(
            data = self.df,
            columns = ["start", "end", "net", "acc", "portfolio"]
        )

        self.df.to_csv( self.pwd_balance.format("resume.csv"), index = False )

    def test(self, assets, start, end, frequency = "1d", from_ = "db"):
        """  
            allocation (dict): If None (Defualt) assume 1/N allocation
        """

        if isinstance( assets, list ):
            l = len(assets)
            assets = { i:(1/l) for i in assets }

        tr = 0

        for i, v in assets.items():
            inst = Asset(
                symbol=i,
                start = start,
                end = end,
                frequency=frequency,
                broker = self.broker,
                fiat = self.fiat,
                from_ = from_
            )


            if inst.df is None or len(inst.df) == 0: continue

            # Here should be immplemented realistic

            r = ( inst.df["close"].iloc[-1] / inst.df["close"].iloc[0] ) - 1

            tr += ( v*r )
        
        return tr
