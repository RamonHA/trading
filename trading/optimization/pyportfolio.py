from pypfopt import EfficientFrontier, EfficientSemivariance, EfficientCVaR, EfficientCDaR
from pypfopt import risk_models
from pypfopt import expected_returns
from pypfopt.discrete_allocation import DiscreteAllocation, get_latest_prices

import warnings
import pandas as pd

from .base_optimizer import BaseOptimizer



class PyPort(BaseOptimizer):
    def __init__(
            self,
            df,
            value = 0,
            exp_returns = "mean",
            risk = "efficientfrontier",
            objective = "maxsharpe",
            time = 1,
            limits = (0, 1),
            target_return = 0,
            risk_aux = "simple",
            **kwargs
        ):
        super().__init__(
            df = df,
            value = value,
            time = time,
            limits = limits,
            target_return = target_return,
            **kwargs
        )

        self.risk = risk.lower()
        self.objective = objective.lower()
        
        try:
            self.exp_returns = exp_returns if not isinstance(exp_returns, str) else self.get_exp_returns(exp_returns)
        except Exception as e:
            print("Could compute exp returns with exception {}".format(e))
            print(self.df)

        self.exp_returns = self.exp_returns.loc[ self.df.columns ]

        self.risk_aux = risk_aux

    def get_exp_returns(self, value):
        m = {
            "mean":expected_returns.mean_historical_return,
            "ema":expected_returns.ema_historical_return
        }[value](self.df, frequency = self.time)

        return m

        # if type(m) == pd.Series:
        #     return m
        # else:

        #     # When dealing with dataframes and want only a Series
        #     return m[0]

    def get_risk(self, value):
        return {
            "exp":risk_models.exp_cov,
            "simple":risk_models.sample_cov
        }[ value ](self.df, frequency = self.time)

    def raw_weigths(self, ef):
        
        if self.objective == "maxsharpe":
            raw_weights = ef.max_sharpe()
        elif self.objective == "minvol":
            raw_weights = ef.min_volatility()
        elif self.objective == "minsemivariance":
            raw_weights = ef.min_semivariance()
        elif self.objective == "mincvar":
            raw_weights = ef.min_cvar()
        elif self.objective == "mincdar":
            raw_weights = ef.min_cdar()
        elif self.objective == "efficientreturn":
            raw_weights = ef.efficient_return( target_return = self.target_return )

        return ef

    def optimize(self, **kwargs):
        
        if self.verbose > 0: print("- ", "Optimization: Optimize with ", self.risk)

        ef = {
            "efficientfrontier":self.efficient_frontier,
            "efficientsemivariance":self.efficient_semivariance,
            "efficientcvar":self.efficient_cvar,
            "efficientcdar":self.efficient_cdar
        }[ self.risk ]()

        if ef is None:
            er = "Error with EF object"
            if self.verbose > 1:
                print(er)
            warnings.warn(er)
            return None, None, None

        return self.discretization( ef )

    def efficient_frontier(self):    
        
        s = self.get_risk( self.risk_aux )

        ef = EfficientFrontier(self.exp_returns, s, weight_bounds = self.limits )
        
        try:
            ef = self.raw_weigths( ef )
            
        except Exception as e:
            er = "Error with Raw Weights in EfficientFrontier. Exception: {}".format(e)
            if self.verbose > 1:
                print(er)
            warnings.warn(er)
            return None

        return ef
    
    def efficient_semivariance(self):
        h = expected_returns.returns_sourceprices(self.df)

        ef = EfficientSemivariance( self.exp_returns, h, weight_bounds = self.limits)

        try:
           ef = self.raw_weigths( ef )
        except Exception as e:
            warnings.warn("Error con RawWeights en Efficient Semivariance. Exception: {}".format(e))
            return None

        return ef

    def efficient_cvar(self, beta = 0.95):

        try:
            h = expected_returns.returns_sourceprices(self.df)
        except Exception as e:
            warnings.warn("Error with returns_sourceprices. Exception: {}".format(e) )

        ef = EfficientCVaR( 
                    self.exp_returns, 
                    h,
                    beta = beta,
                    weight_bounds = self.limits 
                    )
        
        try:
            ef = self.raw_weigths( ef )
        except Exception as e:
            warnings.warn("Error with RawWeights in Efficient CVaR. Exception: {}".format(e))
            return None

        return ef

    def efficient_cdar(self, beta = 0.95):

        h = expected_returns.returns_sourceprices(self.df)

        ef = EfficientCDaR( 
                    self.exp_returns, 
                    h,
                    beta = beta,
                    weight_bounds = self.limits                    
        )
        
        try:
           ef = self.raw_weigths( ef )
        except Exception as e:
            warnings.warn("Error with RawWeights in Efficient CDaR. Exception: {}".format(e))
            return None

        return ef

    def discretization(self, ef):
        """  
            Objeto de frontera eficiente
        """
        
        if self.verbose > 1: print("- ", "Optimization: Discretization")

        latest_prices = get_latest_prices(self.df)
        cleaned_weights = ef.clean_weights()

        if self.value > 0:
            try: 
                da = DiscreteAllocation(cleaned_weights, latest_prices, total_portfolio_value=self.value)
                allocation, leftover = da.lp_portfolio()
            except:
                er = "Error in linear discretization, greedy portfolio to test"
                if self.verbose > 1:
                    print(er)
                
                warnings.warn( er )

                try:
                    da = DiscreteAllocation(cleaned_weights, latest_prices, total_portfolio_value=self.value)
                    allocation, leftover = da.greedy_portfolio()
                
                except:
                    er = "Error with greedy portfolio"
                    if self.verbose > 1:
                        print(er)
                    warnings.warn( er )
                    return None, None, None
        else:
            allocation = dict(cleaned_weights)

        qty = { i:( v*latest_prices[i] ) for i,v in allocation.items() }
        
        total_money = sum(qty.values())
        pct = { i:(v/total_money) for i,v in qty.items() }

        return allocation, qty, pct

