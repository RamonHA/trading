from copy import deepcopy
import re
from datetime import date, timedelta, datetime
import time
from dateutil.relativedelta import relativedelta
import json
import pandas as pd
import warnings
import os

from trading.assets import Asset
from .base_process import BaseProcess
from trading.func_aux import PWD, folder_creation, bring_results
from trading.optimization import Optimization

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
            parallel = False,
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
            parallel = parallel,
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

        if self.verbose > 0: self.print_func("Analyze")

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
            test_time,
            save = True,
            **kwargs
        ):

        # self.assets_inst = [ Asset() for i in self.assets ]
        
        self.analysis_times = {
            "simulations":[]
        }

        a_st = time.time()

        for simulation in range( self.simulations ):
            s_st = time.time()
            start, end, end_analysis, _ = self.start_end_relative( test_time, 0, self.interval_analysis, self.period_analysis, simulation=simulation, verbose = True )

            if self.verbose > 0:
                self.print_0( "{} {}".format( start, end) )

            self.results = self.strategy( end_analysis, **kwargs )

            # if self.verbose > 2:
            #     print(" --- Results dictionary: ", self.results)

            if save:
                pwd = self.pwd_analysis.format( "{}_{}_analysis.json".format( start, end ).replace(":", "-") )
                try:
                    with open( pwd, "w" ) as fp:
                        json.dump( self.results, fp )
                except Exception as e:
                    raise ValueError("Exception in json dump: {}. \nAnalysis json: {}\nType: {}".format(e, self.results, type(self.results)))

            self.analysis_times["simulations"].append( [simulation, time.time() - s_st] )

        self.analysis_times["total"] = time.time() - a_st

        if self.verbose > 0:
            print(" Total analysis time: {}".format( self.analysis_times["total"] ))

        if save:
            with open( self.pwd_analysis.format( "resume.json" ), "w" ) as fp:
                json.dump( self.analysis_times, fp )

    def optimize_pwd(self, risk, objective, test_time, frequency, balance_time, **kwargs):

        if kwargs.get("target_return", 0) == 0:
            self.pwd_balance = self.pwd_analysis.format( 
                "{}/{}/{}_{}_{}".format( risk, objective, test_time, frequency, balance_time )         
            )
        else:
            self.pwd_balance = self.pwd_analysis.format( 
                "{}/{}_{}/{}_{}_{}".format( risk, objective, kwargs["target_return"], test_time, frequency, balance_time )         
            )

        folder_creation( self.pwd_balance )

        self.pwd_balance += "/{}"

    def optimize(
            self,
            balance_time, 
            test_time = 0,
            frequency = None,
            value = 0,
            exp_return = "mean",
            risk = "efficientfrontier",
            objective = "maxsharpe",
            limits = (0,1),
            min_qty = 0,
            run = True,
            track = False,
            max_positions = 0,
            **kwargs
        ):
        """  
            balance_time (int): Time considered to optimize a portfolio
            test_time (int): Default = 0
                        Time considered to optimize to portfolio to (similat to test_time)
            
        """
        
        if self.verbose > 0: self.print_func( "Optimize" )

        test_time = self.test_time if test_time == 0 else test_time
        frequency = self.frequency_analysis if frequency is None else frequency

        if value > 0 and self.realistic == 0:
            self.realistic = 1
        
        if min_qty != 0 and value == 0:
            raise ValueError( "If min_qty, input portfolio value." ) 

        self.optimize_pwd( risk, objective, test_time, frequency, balance_time, **kwargs )

        if run:
            self._optimize(
                test_time = test_time, 
                frequency = frequency, 
                balance_time = balance_time, 
                value = value,
                exp_return = exp_return,
                risk = risk,
                objective = objective,
                limits = limits,
                min_qty = min_qty,
                track = track,
                max_positions = max_positions,
                **kwargs
            )

    def _optimize(
            self, 
            test_time, 
            frequency, 
            balance_time, 
            value = 0,
            exp_return = "mean",
            risk = "efficientfrontier",
            objective = "maxsharpe",
            limits = (0,1),
            min_qty = 0,
            track = False,
            max_positions = 0,
            **kwargs
        ):

        if ( value != 0 and self.realistic == 0 ):
            warnings.warn("Value of portfolio is set to 0 to run simultion. Priority of value over realistic")
            self.realistic = 1
        
        period, interval = re.findall(r'(\d+)(\w+)', frequency)[0]
        period = int(period)
        tracker = []

        tr = 1

        self.df = []

        for simulation in range( self.simulations ):
            start, end, end_analysis, start_analysis = self.start_end_relative( test_time = test_time, analysis_time=balance_time, interval = interval, period = period, simulation = simulation, verbose = True )

            if self.verbose > 0:
                self.print_0( "{} {}".format(start, end) )

            pwd = self.pwd_analysis.format( "{}_{}_analysis.json".format( start, end ).replace(":", "-") )

            data = self.preanalisis(
                pwd = pwd,
                # filter = kwargs.get("filter", "all"),
                **kwargs
            )

            if data is None:
                print("No data to work with. Pwd".format( self.pwd_analysis.format( "{}_{}_analysis.json".format( start, end ) ) ))
                continue

            ll, ul = limits

            if min_qty != 0 or ll > 0 :
                data, ll = self.filter_by_qty(data, value=value, min_qty = min_qty, lower_lim = ll)
                limits = ( ll, ul )

                if self.verbose > 2: self.print_0( "Filter: Data:\n{}".format( data) )

            self.opt = Optimization(
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
    
            allocation, qty, pct = self.opt.optimize( value, time = test_time, limits = limits )

            pwd = self.pwd_balance.format( "{}_{}.json".format( start, end ).replace(":", "-") )

            with open( pwd, "w" ) as fp:
                json.dump(
                    {
                        "allocation":allocation,
                        "qty":qty,
                        "pct":pct
                    },
                    fp
                )
            
            if allocation is None: continue

            fr = {
                "m":5,
                "w":4,
                "d":3,
                "h":2,
                "min":1,
                "s":0
            }

            tr_aux = self.test(
                assets= pct if self.realistic > 0 else allocation,
                start = start,
                end = end,
                frequency = frequency if fr[interval] < 3 else "1d",
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
        if self.verbose > 2: self.print_0("Test for assets:\n{}".format( assets))

        if isinstance( assets, list ):
            l = len(assets)
            assets = { i:(1/l) for i in assets }

        tr = 0
        if frequency == "1d":
            start -= timedelta(days=1)

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


            if inst.df is None or len(inst.df) == 0: 
                print( "Issues to download {} from {} to {}".format(i, start, end) )
                continue

            # Here should be immplemented realistic

            r = ( inst.df["close"].iloc[-1] / inst.df["close"].iloc[0] ) - 1

            tr += ( v*r )

            if self.verbose > 2: 
                print("-- Test return for {} with allocation {} is {}".format(i, v, r))
                print("-- With close price {} and open price {}".format( inst.df["close"].iloc[-1] , inst.df["close"].iloc[0] ))


        return tr

    def results_compilation(self, pwd = None, extend = False):
        """  """
        pwd = pwd if pwd is not None else self.pwd_analysis[:-3]
        dicc = pd.DataFrame.from_dict( bring_results(pwd, data = {}) , orient="index").reset_index().rename(columns = {"index":"route"})

        if dicc.empty:
            return dicc
        
        try:
            dicc = dicc.sort_values(by = "acc", ascending=False).reset_index(drop = True)
        except Exception as e:
            print("Result compilation df does not have 'acc' column. Exception: ", e)
            return dicc

        if extend:
            extended = []
            for i in dicc["route"]:
                extended.append(i.replace(self.pwd[:-2], "").split(os.path.sep))
            
            extended = pd.DataFrame( extended, columns = ["freq", "analysis", "analysis_params", "po_risk", "po_target", "po_params"] )

            dicc = pd.concat([ dicc, extended ], axis = 1)

        return dicc

    def behaviour(self, route):

        route = route if "resume.csv" in route else ( route + "/resume.csv" )

        try:
            df = pd.read_csv( route )
        except:
            print("No file in resume route {}".format(route))
            return None
        
        if "Unnamed: 0" in df.columns:
            df.drop(columns = ["Unnamed: 0"], inplace = True)
        
        df.set_index("end", inplace = True)
        df.index = pd.to_datetime( df.index ) 

        return df
