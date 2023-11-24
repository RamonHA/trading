import operator
from copy import deepcopy
import re
import pandas as pd
import numpy as np
from sklearn.model_selection import ParameterGrid
from itertools import combinations
import multiprocess as mp


def rule_validation(asset):
    buy = False
    price_bought = None
    price_sold = None
    returns = []
    df = asset.df[ (asset.df["buy"] == True) | ( asset.df["sell"] == True ) ]
    df = df.replace(np.nan, 0)
    df = df[ (df[ "buy" ] != df["buy"].shift()) | (df[ "sell" ] != df["sell"].shift()) ]
    for i in range(len(df)):
        if not buy and df.iloc[i]["buy"] :
            buy = True
            price_bought = df.iloc[i]["close"]
            date_bought = df.index[ i ]

            trans = [ date_bought, price_bought ]
        
        elif buy and df.iloc[i]["sell"]:
            buy = False
            price_sold = df.iloc[i]["close"]
            date_sold = df.index[ i ]
            
            trans += [ date_sold, price_sold ]
            returns.append( trans )

    df = pd.DataFrame(returns, columns = ["date_bought", "bought", "date_sold", "sold"] )
    df["returns"] = ((df["sold"] / df["bought"]) - 1).round(3)
    df[ "acc" ] = (df["sold"] / df["bought"]).cumprod().round(3)
    # df["open"] = df["date_sold"] - df["date_bought"]

    return df

def rule_testing_parallelize():
    pass

class Element():
    def __init__(self, element):
        """ Element class: help representation of a rule """
        self.element = element
    
    @property
    def element(self):
        return self.__element
    
    @element.setter
    def element(self, value):
        self.__element = self.parse_element(value)
    
    def str2bool(self, value):
        if "True" in value:
            return True
        elif "False" in value:
            return False

    def parse_element(self, value):
        
        if "True" in value or "False" in value:
            self.type = "boolean"
            return self.str2bool( value )

        try:
            value = float(value)
            self.type = "constant"
            return value

        except Exception as e:
            self.type = "column"
            return value

class Rule():

    __OPERATORS = {
            '>': operator.gt,
           '<': operator.lt,
           '>=': operator.ge,
           '<=': operator.le,
           '==': operator.eq,
           '!=': operator.ne
        }

    def __init__(self, rule):
        """ Rule Class """
        self.error = None
        self.rule = rule
        
        self.parse_operator(rule)

        self.elements = [ Element(e.strip()) for e in rule.split( self.operator ) ]
        
        # Join types of elements in rule to determine rule type
        # Sort help us in Ruletesting
        
        types = [ e.type for e in self.elements ]
        types.sort()
        self.type = "_".join( types )
    
    def parse_operator(self, rule):

        for o, application in self.__OPERATORS.items():
            if o in rule:
                self.operator = o
                self.apply_op = application
                return

        raise ValueError( f"No operator was found on rule: {rule}" )

    def boolean_column(self):
        """ The application of boolean and constant follow the same operator application """
        return self.column_constant()

    def column_constant(self):
        return self.__OPERATORS[ self.operator ]( self.asset.df[ self.elements[ 0 ].element ], self.elements[ 1 ].element )

    def column_column(self):
        return self.__OPERATORS[ self.operator ]( self.asset.df[ self.elements[ 0 ].element ], self.asset.df[ self.elements[ 1 ].element ] )

    def apply(self, asset):
        self.asset = asset

        return {
            "boolean_column":self.boolean_column,
            "column_constant":self.column_constant,
            "column_column":self.column_column
        }[ self.type ]()

class RuleTesting():

    __OPERATORS = [ "and", "or", "xor" ]
    
    def __init__(self, asset, rules, target = None, **kwargs):
        
        self.asset = deepcopy(asset)
        self.rules = rules
        self.target = target

    def __str__(self):
        return f"Rules: "

    @property
    def target(self): return self.__target
    
    @target.setter
    def target(self, value):

        if self.type == "both":
            self.type_target = value = "sell"
        elif value is None:
            raise ValueError( f"If not sell rule, then a target value must be set" )
        elif value >= 1:
            self.type_target = "places"
        elif value < 1:
            self.type_target = "pct"
        else: 
            raise ValueError( f"Target value '{value}' is not valid." )

        self.__target = value

    @property
    def rules(self): return self.__rules
    
    @rules.setter
    def rules(self, value):
        assert isinstance(value, dict), f"Rules is not dictionary, is type {type(value)}"
        assert "buy" in value or "sell" in value, f"Rules keys must be 'buy' or 'sell'."
        
        keys = list( value.keys() )
        self.type = "both" if len(keys) == 2 else keys[0]

        self.__rules = value

    def apply(self, rules, operators):

        for i, rule in enumerate(rules):
            rule_elem = Rule( rule )
            self.asset.df[ rule ] = rule_elem.apply( self.asset )
            
            if i == 0: 
                first_series = self.asset.df[ rule ]
            elif operators[i] == "and":
                first_series += self.asset.df[ rule ]
            elif operators[i] == "or":
                first_series *= self.asset.df[ rule ]
            elif operators[i] == "xor":
                first_series ^= self.asset.df[ rule ]

        return first_series

    def get_operator(self, string):
        for o in self.__OPERATORS:
            if o in string:
                return o
        
        raise ValueError( f"No operator valid on str '{string}'")

    def parse_rule(self, rule):
        # rule = rule.lower()

        operators_pattern = "|".join( self.__OPERATORS )

        operators = [m.start() for m in re.finditer(operators_pattern, rule )]        
        operators = [self.get_operator( rule[o:(o+3)] ) for o in operators ]
        operators = [None] + operators

        rules =  [ r.strip() for r in re.split( operators_pattern, rule ) ]

        assert len(operators) == len(rules), f"Rule and operators do not math in rule '{rule}'."

        return rules, operators

    def buy(self):
        rules, operators = self.parse_rule( self.rules["buy"] )
        self.asset.df["buy"] = self.apply( rules, operators ) 
    
    def clean_buy(self):
        df = self.asset.df.copy()

        df["extra_buy"] = df["buy"] != df["buy"].shift(1)

        df["buy"] = df["buy"] & df["extra_buy"]

        self.asset.df["buy"] = df["buy"]

    def sell_column(self):
        # Clean buy column because Buy orders can be subsequent period to period
        # So sell orders can be misguided when validating
        self.clean_buy()

        if self.type_target == "places":
            self.asset.df["sell"] = self.asset.df["buy"].shift( self.target )

        elif self.type_target == "pct":
            self.asset.df["sell"] = False
            true_values = self.asset.df[ self.asset.df["buy"] == True ].index.tolist()
            close = self.asset.df["close"]

            for i in true_values:
                close_price = close[i]
                close_aux = close[ i: ]
                close_aux = ( close_aux / close_price ) - 1
                pct_index = close_aux[ close_aux > self.target ]

                if len(pct_index) == 0:
                    # Este mensaje no importa por el momento, solo nos indica que como no hay mejor, yo no
                    # nos moveremos a los siguientes puesto
                    # que al no cerrarse esta orden, no podemos abrir ni cerrar las demas.
                    # raise Exception( "Testing did not prove a better return." )
                    pct_index = -1
                else:
                    pct_index = pct_index.index[0]

                try:
                    self.asset.df.loc[ pct_index, "sell" ] = True
                except Exception as e:
                    raise Exception( f"{e}. Got {type(pct_index)} from {pct_index}." )

    def run(self):
        if self.type == "both":
            self.buy()
            self.sell()
        
        elif self.type == "buy":
            self.buy()
            self.sell_column()
        
        return self.validate()

    def validate(self):
        self.results = rule_validation( self.asset )
        
        return self.results

class RulesGenerator():
    def __init__(self, asset, rules, and_or = True, columns = {}, universe = [], target = [], **kwargs):
        """  
        
            universe (list):
                NOTE: AVOID INPUT with three annidated lists.
        """
        self.asset = asset
        self.rules = rules
        self.columns = columns

        # for i, v in kwargs.items(): self.__dict__[ i ] = v
        self.universe = universe
        self.target = target

        assert len(self.rules) >= len(self.universe), f"No same length universe of params and rules"

        self.and_or = and_or
        self.error = {}

    @property
    def columns(self):
        return self.__columns
    
    @columns.setter
    def columns(self, value):
        assert isinstance(value, dict), f"Column variable must be type dict, but got '{type(value)}'"
        
        # Some type of validation at this point
        self.__columns = value

    @property
    def grid(self):
        if hasattr(self, "__grid"):
            return self.__grid
        else:
            self.grid = self.get_grid()
            return self.__grid

    @grid.setter
    def grid(self, value):
        assert isinstance(value, list), f"Grid must be a list type, but got type {type(value)}"
        self.__grid = value

    def create_grid_from_list(self, universe):
        new_universe = { i:self.get_param_universe( single_universe ) for i, single_universe in enumerate(universe) }
        return [ tuple( p.values() ) for p in ParameterGrid( new_universe )]

    def get_param_universe(self, universe):
        """ Return list from param setting """
        if isinstance( universe, tuple ):
            return range( *universe )

        elif isinstance( universe, list ):
            types = set([type(i) for i in universe ])
            if list in types or tuple in types:
                # If got a universe where inside there are more list, we form a new grid of tupples
                universe = self.create_grid_from_list( universe )

        return universe

    def prep_rules(self):
        """ Generate a list of rule's combinations, considering even different universe parameters """
        if hasattr(self, "universe") and len(self.universe) > 0: 
            # Get rules to format
            rules2format = [ i for i, rule in enumerate(self.rules) if "{" in rule ]

            # Rules that do not have formatting in them
            remainrules = [ rule for i, rule in enumerate(self.rules) if "{" not in rule ]
            assert len(self.universe) <= len(rules2format), "Formating rules and universe of parameters do not match"

            # Iterate over formatting rules, and based on their universe, form the full set of rules from them.
            modified_rules = []
            for i, universe in enumerate( self.universe ):
                                
                if isinstance(universe, tuple):
                    # if tupple, we considere the universe as parameters for the range func
                    modified_rules.append( [ self.rules[ rules2format[i] ].format( pu ) for pu in range( *universe ) ] )

                elif isinstance(universe, list):
                    # When universe of parameter has a inside list that correspond to a str with two formatting areas
                    # From universe of params, create list of them and transform the universe to a grid of tupples to feed to formatting str
                    
                    if type(universe[0]) not in [list, tuple]:
                        modified_rules.append( [ self.rules[ rules2format[i] ].format( pu ) for pu in universe ] )
                        
                    else:
                        uni_param_grid = self.create_grid_from_list( universe )
                        modified_rules.append( [ self.rules[ rules2format[i] ].format( *u ) for u in uni_param_grid ] )
                    
                else:
                    raise ValueError( f"Invalid universe of parameters")
            
            # Add list of rules to LIST of LISTS [] + [ [] + [] ]
            rules = remainrules + modified_rules
        
        else:
            rules = self.rules
        
        # if more than one rule, then we have to do a combination
        if len(rules) > 1:
            rules_grid = []
            for L in range(1, len(rules) + 1):
                # Consider the "modified rules" as one
                for subset in combinations(rules, L):
                    subset = list(subset)
                    if L == 1:
                        if isinstance(subset[0], str):
                            rules_grid += subset
                        elif isinstance( subset[0], list ):
                            rules_grid += subset[0]

                    # if combination of more than one rule, we need to concatenate unmodified rule with set of modified rules
                    # Ex: 
                    # [sma > 0], [ rsi > 5, rsi > 10, rsi > 15 ]
                    # [sma > 0 , rsi > 5], [sma > 0 , rsi > 10], [sma > 0 , rsi > 15]
                    
                    else:
                        types_str = set([type(i) for i in subset ])
                        
                        # if only str types, then we can join to final list without further modification
                        if  types_str ==set([str]):
                            rules_grid += subset

                        # in this case, a str type and a list (as in the example) are in the subset array
                        else:
                            # Create a dictionary with possible values, to later on feed to ParemeterGrid 
                            def ensure_lists(x):
                                if isinstance(x, str):
                                    return [x]
                                elif isinstance(x, list):
                                    return x

                            subset_dict = { i:ensure_lists(s) for i, s in enumerate(subset) }

                            if isinstance( self.and_or, str ):
                                # Concat the operator to the combination rules generated on the ParameterGrid
                                join_str = f" {self.and_or} "
                                [ rules_grid.append( join_str.join( map( str, list(i.values())))) for i in ParameterGrid( subset_dict ) ]
                        
        else:
            rules_grid = rules

        self.rules_grid = rules_grid

        return [{"buy":r} for r in self.rules_grid]

    def prep_asset(self, columns):
        """ Returns a list of assets if columns variable has information """
        if len(columns) == 0:
            return [ self.asset ]

        assets = []

        columns = { col_name:self.get_param_universe( param ) for col_name, param in columns.items()}

        param_universe = list( ParameterGrid( columns ) )

        for param in param_universe:
            asset = deepcopy(self.asset)

            for col_name, p in param.items():
                    
                if isinstance(p, tuple):
                    asset.df[ col_name ] = getattr( asset, col_name )( *p )
                else:
                    asset.df[ col_name ] = getattr( asset, col_name )( p )
                
            asset.params = param

            assets.append( asset )

        # for col_name, param_universe in columns.items():
        #     param_universe = self.get_param_universe( param_universe )

        #     for param in param_universe:
        #         asset = deepcopy(self.asset)
        #         if isinstance(param, tuple):
        #             asset.df[ col_name ] = getattr( asset, col_name )( *param )
        #         else:
        #             asset.df[ col_name ] = getattr( asset, col_name )( param )

        #         assets.append( asset )

        return assets

    def get_grid(self):        
        
        rules = self.prep_rules()
        rules_grid = []

        for rule in rules:
            rule_str = list(rule.values())[0].split(" ")
            
            asset_params = { name:param for name, param in self.columns.items() if name in rule_str }

            rule_dict = {}
            rule_dict["rules"] = [ rule ]
            rule_dict["asset"] = self.prep_asset(asset_params)        

            if hasattr(self, "target"):
                rule_dict["target"] = self.target

            rule_grid = list(ParameterGrid( rule_dict ))
            rules_grid += rule_grid 

        return rules_grid

    def record_error(self, error, obj):
        if error in self.error:
            self.error.append( obj )
        else:
            self.error[ error ] = [obj]

    def run(self, verbose = True, parallel = False, **kwargs):
        
        if parallel:
            self.run_parallel(verbose = verbose, cpus = kwargs.get( "cpus", mp.cpu_count() // 2 ) )
        else:
            self.run_series(verbose = verbose)

    def run_series(self, verbose = True):
        self.rules_obj = [  RuleTesting( **params ) for params in self.grid ]
        results = []

        if verbose:
            print( "Rules to test: ", len(self.rules_obj) )

        for i, ro in enumerate(self.rules_obj):
            try:
                df_aux =  ro.run()
            except Exception as e:
                self.record_error( e, ro )
                continue
            
            if len(df_aux) == 0:
                continue
            
            positive = len( df_aux[df_aux["returns"] > 0])
            negative = len( df_aux[df_aux["returns"] <= 0])
            mean_ = df_aux["returns"].mean()
            min_ = df_aux["returns"].min()
            std_ = df_aux["returns"].std()
            sharpe = (mean_ / std_) if std_ != 0 else 0
            neg_std = df_aux[ df_aux["returns"] < 0]["returns"].std()
            sortino = (mean_ / neg_std) if neg_std != 0 else 0

            results.append( [ ro.asset.params, ro.rules, ro.target, len(df_aux),  df_aux["acc"].iloc[-1], mean_, min_, std_, sharpe, sortino, positive, negative ] )
        
        if len(results) == 0:
            raise Exception( "Experiment result in no result" )

        self.results = pd.DataFrame( results, columns = [ "params", "rules", "target", "qty_trans", "acc", "mean", "max_drawdown", "std", "sharpe", "sortino", "positive", "negative" ] )

        # assert len(self.results) == len(self.rules_obj), "Results and rule objects do not match"

    def run_parallel(self, cpus, verbose = True):

        with mp.Pool( cpus ) as pool:
            r = pool.starmap(
                RuleTesting,
                [  ]
            )

        self.rules_obj = [  RuleTesting( **params ) for params in self.grid ]
        results = []

        if verbose:
            print( "Rules to test: ", len(self.rules_obj) )
