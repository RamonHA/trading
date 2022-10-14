
import warnings
from datetime import date, timedelta, datetime
from dateutil.relativedelta import relativedelta
from copy import copy
import multiprocess as mp
import re
import json
import pandas as pd
import math
from dateutil import parser
from trading.func_aux import PWD, folder_creation, get_config
from trading.assets import Asset


def strategy(
        asset,
        time,
        function,
        end,
        frequency,
        fiat,
        broker,
        from_ = "db",
        sentiment = False,
        verbose = False
    ):

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
    elif interval_analysis == "min":
        start = end - timedelta(seconds = 60*time*period_analysis )

    if verbose:
        print("Func Strategy", asset, start, end, frequency, fiat, broker)
    
    inst = Asset( 
        asset, 
        start, 
        end, 
        frequency = frequency, 
        fiat = fiat, 
        broker = broker, 
        from_ = from_, 
        sentiment = sentiment
    )

    if inst.df is None or len(inst.df) <= 3: 
        warnings.warn("Error in strategy. Df import issue")
        # print("Error in strategy. Df import issue")
        return None

    r = function(inst)

    if verbose:
        print( "{}: {}".format( asset, r ) )

    return r

class Setter():
    def __init__(
            self,
            broker = "yahoo_asset",
            fiat = None,
            commission = None,
            assets = None,
            **kwargs
        ):
        self.broker = broker.lower()
        self.commission = commission if commission is not None else get_config()[ self.broker ][ "commission" ]
        self.fiat = fiat if fiat is not None else self.set_fiat()
        self.assets = assets if assets is not None else self.get_assets()

        self.verbose = kwargs.get("verbose", 0)

    def print_func(self, value):
        print( "\n\n", "#"*20, value, "#"*20 )
    
    def print_0(self, value):
        print("- ", value)

    @property
    def assets(self):
        if hasattr(self, "_assets"):
            return self._assets
        else:
            self.assets = self.get_assets()
            return self._assets
    
    @assets.setter
    def assets(self, value):
        if value is not None:
            assert type(value) in [list, dict], "Asset must be a list or dictionary"
            self._assets = value
        else:
            warnings.warn("Asset list is empty")
            self._assets = {}

    def get_assets(self):
        from trading.func_aux import get_assets
        return get_assets().get( self.broker.lower(), None )

    def set_fiat(self):
        # Defaults values
        return {
            "gbm":"mx",
            "bitso":"mx",
            "binance":"usdt"
        }.get(self.broker, None)

class BaseProcess(Setter):
    def __init__(
            self,
            broker,
            fiat = None,
            commission = None,
            assets = None,
            end = date.today(),
            subdivision = None,
            parallel = False,
            **kwargs
        ):
        super().__init__(
            broker = broker, 
            fiat = fiat, 
            commission = commission,
            assets=assets,
            **kwargs
        )
        self.analysis = {}
        self.end = end
        self.subdivision = subdivision
        self.parallel = parallel

    @property
    def end(self):
        return self._end

    @end.setter
    def end(self, value):
        if value is None:
            self._end = None
        elif type(value) == datetime:
            self._end = value
        elif type(value) == date:
            self._end = datetime.combine(value, datetime.min.time())
        elif type(value) == str:
            self._end = parser.parse(value)
        else:
            raise ValueError("End must be date, datetime, or str with valid format. Type {}.".format(type(value)))

    def strategy(self, end, from_ = "db", **kwargs):

        cpus = kwargs.get( "cpus", -1 )

        or_assets = copy( self.assets )
        for a, v in self.analysis.items():

            if self.verbose > 0:
                self.print_0("Analysis: {}".format( a ) )
            
                if self.verbose > 1:
                    self.print_0("Assets: {}".format( len(or_assets)))

            next_assets = {}

            if self.parallel:
                with mp.Pool( cpus ) as pool:
                    r = pool.starmap(
                        strategy,
                        [(
                            i, 
                            v["time"],
                            v["function"],
                            end,
                            v.get( "frequency", self.frequency_analysis ),
                            self.fiat,
                            self.broker,
                            from_,
                            kwargs.get("sentiment", False),
                            True if self.verbose > 2 else False
                        ) for i in or_assets ]
                    )
            else:
                r = [   strategy(
                            i, 
                            v["time"],
                            v["function"],
                            end,
                            v.get( "frequency", self.frequency_analysis ),
                            self.fiat,
                            self.broker,
                            from_,
                            kwargs.get("sentiment", False),
                            True if self.verbose > 2 else False
                        ) for i in or_assets ]

            # if not all(r):
            #     if self.verbose > 0:
            #         self.print_0("Analysis: {} does not have any Trues".format( a ) )
                
            #     return {}

            next_assets = { inst:value for inst, value in zip( or_assets, r ) if value }

            if v.get("filter", "all") != "all":

                next_assets = self.filter(
                    next_assets,
                    v.get("filter", "all"),
                    filter_qty = v.get("filter_qty", 3),
                    **kwargs
                )

            or_assets = copy(next_assets)

        return next_assets # Al fin: or_instrumentos = next_instrumentos

    def asset_division(self, data):
        
        aux = {}
        
        for i, v in data.items():
            
            sd = self.assets[ i ][ self.subdivision ]

            if sd not in aux.keys(): aux[ sd ] = {}
            
            aux[ sd ][ i ] = v
                  
        return aux

    def filter(self, data, filter = "all", **kwargs):

        if self.verbose > 2: self.print_0("Filter data:\n{}".format( data))

        n = kwargs.get("filter_qty", 3)
        n = math.floor( len(data)*n ) if n < 1 else n

        if n < len(data): 
            n = len(data)
            warnings.warn( "Filter qty ({}) exceed the number of assets ({}).".format( n, len(data) ) )

        if self.subdivision is None:
            return {
                "all":data,
                "positive":{ i:v for i,v in data.items() if v > 0 },
                "highest":{k:v for k, v in sorted(data.items(), key = lambda item:item[1], reverse = True)[ 0: n] if v > 0},
                "lowest":{k:v for k, v in sorted(data.items(), key = lambda item:item[1], reverse = False)[ 0: n] if v > 0},
            }[filter]

        else:
            data = self.asset_division(data)

            if filter == "positive":
                aux = { i:{ j:k for j,k in v.items() if k > 0 } for i, v in data.items() }
            elif filter in ["highest", "lowest"]:
                aux = { i:{ j:k for j, k in sorted(
                            v.items(),
                            key = lambda item:item[1], 
                            reverse = True if filter == "highest" else False
                    )[ 0: n] if k > 0 
                } for i, v in data.items() }

            auxx = {}
            for i in aux: auxx.update( aux[i] )
            
            return auxx

    def preanalisis(self, data = None, pwd = None, filter = "positive", **kwargs ):

        if self.verbose > 0: 
            if pwd is not None: self.print_0("Preanalisis for {}".format( pwd))
            else: self.print_0("Preanalisis for {}".format( len(data)) )

        if data is None:
            with open( pwd, "r" ) as fp:
                data = json.load(fp)
        
        if self.verbose > 2: print( "Preanalisis data: \n{}".format( data) )

        if len(data) == 0: return None

        if isinstance(data, pd.DataFrame):
            col = data.columns
            assert len(col) == 1, "Exp returns data is a pandas DataFrame with more than one column"
            data = data[ col[0] ]

        data = self.filter(data, filter = filter, **kwargs)

        if len(data) == 0: return None

        return data

    def filter_by_qty(self, data, value=0, min_qty=0, lower_lim = 0):
        if min_qty > 0:
            min_pos = min_qty / value
        elif lower_lim > 0:
            min_pos = lower_lim
        
        n = int( 1 // min_pos ) - 1

        data = sorted( 
            data.items(), 
            key = lambda item: item[1] , 
            reverse = True 
        )[ 0: n ]
        data = { k:v for k,v in data }
        
        return data, min_pos

    def set_pwd_analysis(self, frequency, test_time, analysis, folder):
        aux_analysis = "_".join( list( analysis.keys() ) )

        aux = []
        for k, v in analysis.items():

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

    def start_end(self, end, time, interval, period, simulations = 1):
        if interval == "m":
            start = end - relativedelta(months = period*time*simulations - 1)
            start = start.replace(day = 1)
        elif interval == "w":
            start = end - timedelta(days = 7*simulations*period*time)
        elif interval == "d":
            start = end - timedelta(days = simulations*period*time)
        elif interval == "h":
            end = datetime.combine( end, datetime.min.time() )
            start = end - timedelta(seconds = 3600*simulations*period*time)            
        elif interval == "min":
            start = end - timedelta(seconds = 60*simulations*period*time)

        return start, end

    def start_end_relative(self, test_time, analysis_time, interval, period, simulation = 1, verbose = True):
        if interval == "m":
            start = self.start + relativedelta(months = (simulation-1)*period*test_time)
            start = start.replace(day = 1)

            end = self.start + relativedelta(months = (simulation)*period*test_time)
            # end -= timedelta(days = 1)

            end_analysis = start - timedelta(days = 1)
            start_analysis = end_analysis - relativedelta( months = analysis_time*period )
        
        elif interval == "w":
            start = self.start + timedelta(days = 7*simulation*test_time*period)
            end = start + timedelta(days = 7*test_time*period)
            end_analysis = start
            start_analysis = end_analysis - timedelta(days = 7*analysis_time*period)

        elif interval == "d":
            start = self.start + timedelta( days = simulation*test_time*period )
            end = start + timedelta(days = test_time*period )
            end_analysis = start
            start_analysis = end_analysis - timedelta(days = period*analysis_time)

        elif interval == "h":
            start = self.start + timedelta( seconds = simulation*test_time*self.period_analysis*3600 )
            end = start + timedelta( seconds = test_time*self.period_analysis*3600 ) 
            end_analysis = datetime.combine(start, datetime.min.time())
            start_analysis = end_analysis - timedelta(seconds=3600*analysis_time*period)

        elif interval == "min":
            start = self.start + timedelta( seconds = simulation*test_time*self.period_analysis*60 )
            end = start + timedelta( seconds = test_time*self.period_analysis*60 ) 
            end_analysis = start
            start_analysis = end_analysis - timedelta(seconds=60*analysis_time*period)


        return start, end, end_analysis, start_analysis
