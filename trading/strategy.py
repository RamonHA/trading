from copy import copy
import pandas as pd
from trading.evaluator.value_strategy import ValueStrategy

class Ta:
    def __init__(self, sample = None, ta = None, params = None, move = None, func = None):
        self.sample = sample
        self.ta =  ta
        self.params = params
        self.move = move
        self.func = func

class Strategy():
    
    TAS_AVAILABLE = [ "all" ]
    TA_TYPES = [ "trend", "oscillators" ]
    PARAM_TYPES = [ "one_param", "two_params" ]

    TREND_FIRST_PARAM = ( 5, 200, 5 )
    OSCILLATORS_FIRST_PARAM = (3, 60, 2)

    TREND_SLOPE = OSCILLATORS_SLOPE = 3
    TREND_SLOPE_CHANGE = OSCILLATORS_SLOPE_CHANGE = 3

    def __init__(self, asset, tas = "all", parallelize = False):
        """  

            tas (str): Which set of tas to run (Default = 'all'). Options:
                - 'all'
                - 'all_trend'
                - None (if None, then it is assumed that the asset object dataframe 
                    already has the tas in it, for this option, modified_cols var (list) must be filled 
                    with the columns corresponding to the TAs)
        """
        # make asset Assert
        self.asset = asset
        self.init_cols = self.asset.df.columns.to_list()
        self.tas = tas

        self.init_vars()

        self.parallelize = parallelize
    
    def init_vars(self):
        self.TREND_ONE_PARAM = {
            "sma":self.asset.sma,
            "ema":self.asset.ema,
            "wma":self.asset.wma,
            "dema":self.asset.dema,
            "hull_ema":self.asset.hull_ema,
            "hull_twma":self.asset.hull_ema,
            "hull_wma":self.asset.hull_ema,
            "tema":self.asset.tema,
        }

        self.OSCILLATORS_ONE_PARAM = {
            "adx":self.asset.adx,
            "aroon":self.asset.aroon,
            "cci":self.asset.cci,
            "dpo":self.asset.dpo,
            "easy_of_movement":self.asset.easy_of_movement,
            "force_index":self.asset.force_index,
            "keltner":self.asset.keltner,
            "momentum":self.asset.momentum,
            "roc":self.asset.roc,
            "rsi":self.asset.rsi,
            "trix":self.asset.trix,
            "vo":self.asset.vortex_indicator,
            "william":self.asset.william
        }

        self.OSCILLATORS_MULTI_RETURN = [ "adx", "aroon" , "vo"]

        self.one_param_dict = {
            "trend":( self.TREND_ONE_PARAM, self.TREND_FIRST_PARAM ),
            "oscillators":( self.OSCILLATORS_ONE_PARAM, self.OSCILLATORS_FIRST_PARAM )
        }

    @property
    def tas(self):
        return self.__tas
    
    def parse_ta_name( self, name ):
        """ Gets the structure of the TA to know what is going to be executed. 
                                            all
                            _________________|______________________
                            |                                       |
                        all_trend                           all_oscillators
                    _______|____________                ____________|____________
                    |                   |               |                       |
                oneparam            twoparam        oneparam                twoparam
                ____|___________      
               |      |        |
            normal  slope   change


                                            all
                            _________________|______________________
                            |                                       |
                        one_param                               twoparams
        """

        new_name = None

        if "all" in name:
            new_name = ["all"]
        else:
            new_name = [None]

        if "trend" in name:
            new_name.append( "trend" )
        elif "oscillators" in name:
            new_name.append("oscillators" )
        else:
            new_name.append( None )
        
        if "oneparam" in name or "one_param" in name:
            new_name.append("oneparam")
        elif "twoparams" in name or "two_params" in name:
            new_name.append("twoparams")
        else:
            new_name.append( None )
        
        if "slope" in name:
            new_name.append("slope")
        elif "change" in name:
            new_name.append("change")
        else:
            new_name.append( None )
        
        name_obj = Ta( *tuple( new_name ) )

        return None if new_name.count(None) == len(new_name) else name_obj

    def parse_tas(self, value):
        value_list = []
        if isinstance( value, str ):       
            v = self.parse_ta_name( value )
            if v is not None:
                value_list.append( v )
        
        elif callable( value ):
            value_list.append( Ta( func = value ) )
        
        elif isinstance(value, list):
            for v in value: value_list.extend( self.parse_tas(v) )
        
        elif isinstance( value, Ta ):
            value_list.extend( self.parse_tas( "_".join(i for i in value.__dict__.values() if i) ) )

        else:
            raise ValueError(  )
        
        return value_list

    @tas.setter
    def tas(self, value):
        self.__tas = self.parse_tas(value)

    @property
    def tas_slope(self):
        return self.__tas_slope
    
    @tas_slope.setter
    def tas_slope(self, value):
        TREND_SLOPE = OSCILLATORS_SLOPE = self.__tas_slope = value

    @property
    def tas_slope_change(self):
        return self.__tas_slope_change
    
    @tas_slope_change.setter
    def tas_slope_change(self, value):
        TREND_SLOPE = OSCILLATORS_SLOPE = self.__tas_slope_change = value

    @property
    def all_diff(self):
        return self.__all_diff
    
    @all_diff.setter
    def all_diff(self, value):
        self.tas_slope_change = self.tas_slope = self.__all_diff = value

    @property
    def all_trends_diff(self):
        return self.__all_trends_diff
    
    @all_trends_diff.setter
    def all_trends_diff(self, value):
        self.TREND_SLOPE_CHANGE = self.TREND_SLOPE = self.__all_trends_diff = value

    @property
    def all_oscillators_diff(self):
        return self.__all_oscillators_diff
    
    @all_oscillators_diff.setter
    def all_oscillators_diff(self, value):
        self.OSCILLATORS_SLOPE_CHANGE = self.OSCILLATORS_SLOPE = self.__all_oscillators_diff = value

    def _one_param(self, tas):
        names, ranges = self.one_param_dict[ tas ]

        cols = []
        for name, operation in names.items():
            for i in range( *ranges ):
                col = f"{name}_{i}"
                cols.append( col )
                self.asset.df[ col ] = operation( i )

        return cols

    def slope(self, ori_cols, col_suffix = "_slope"):
        cols = []

        for c in ori_cols:
            col = c + col_suffix
            cols.append( col )
            self.asset.df[ col ] = self.asset.df[ c ].pct_change( self.TREND_SLOPE )

        return cols

    def one_param(self, ta):

        cols = []

        col_aux = self._one_param( ta.ta )
        cols = col_aux

        if ta.move in ["slope", None]:
            col_slope_aux  = self.slope(col_aux, col_suffix="_slope")

            if "all" not in self.tas:
                cols = col_slope_aux
            else:
                cols.extend( col_slope_aux )

        if ta.move in ["change", None]:
            col_slope_change_aux  = self.slope(col_slope_aux, col_suffix="_change")

            if "all" not in self.tas:
                cols = col_slope_change_aux
            else:
                cols.extend( col_slope_change_aux )
        
        return cols

    def two_params(self, ta):
        raise NotImplementedError

    def run_tas(self, verbose = False):
        cols = []

        for ta in self.tas:
            if ta.func is not None:
                self.asset, col = ta.func( self.asset )
                cols.extend( col )
                continue

            if ta.sample == "all" or ta.params in ["oneparam", None]:
                if ta.ta is None:
                    for ta_type in self.TA_TYPES:
                        aux_ta = copy(ta)
                        aux_ta.ta = ta_type
                        cols.extend( self.one_param(aux_ta) )  
                else:
                    cols.extend( self.one_param(ta) )     

            if ta.sample == "all" or ta.params in ["twoparams", None]:
                if ta.ta is None:
                    for ta_type in self.TA_TYPES:
                        aux_ta = copy(ta)
                        aux_ta.ta = ta_type
                        cols.extend( self.two_params(aux_ta) )  
                else:
                    cols.extend( self.two_params(ta) )     

        self.modified_cols = cols
        our_cols = copy( self.init_cols )
        our_cols.extend( self.modified_cols )
        self.asset.df = self.asset.df[ our_cols ]

    def value(self, target = 1, method = "distribution_similarity", hold = False, verbose = False):
        """  
            hold (str): Not Implemented Yet
        """
        self.run_tas()

        if 0 in self.asset.df.shape:
            print(f"{self.asset} has no data after tas.")
            return pd.DataFrame()

        # if target is list
        if isinstance( target, list ):
            def check(x):
                if x is None or type(x) not in [ int, float ]:
                    return False
                return True

            target = [ i for i in target if check(i) ]

        elif type(target) in [int, float]:
            target = [ int(target) ]

        results = []

        for t in target:

            if verbose > 0:
                print(" - Target: ", t)

            self.asset.df[ "target" ] = self.asset.df[ "close" ].pct_change( t ).shift( -t ).apply( lambda x : 1 if x > 0 else 0 )

            for col in self.modified_cols:

                if verbose > 1:
                    print(" -- Col: ", col)

                vs = ValueStrategy(self.asset.df , cols = [ "target", col ])

                v = vs.value( method = method )
                
                if v is None: continue

                range_up = self.asset.df[ self.asset.df["target"] == 1 ][ col ].quantile( [0.25, 0.75] ).values.tolist()
                range_down = self.asset.df[ self.asset.df["target"] == 0 ][ col ].quantile( [0.25, 0.75] ).values.tolist()

                results.append( [ t, col, v , range_up, range_down] )

        self.results = pd.DataFrame(results, columns = [ "target", "col", "result" , "range_up", "range_down"])

        return self.results
