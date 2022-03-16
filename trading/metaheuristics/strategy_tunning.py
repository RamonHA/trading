

import numpy as np
from pymoo.model.problem import Problem

from .metaheuristics import Metaheuristic

class StrategyTunning(Metaheuristic):
    def __init__(
            self,
            strategy,
            ta,
            n_var,
            xu,
            xl,
            algorithm = "de", 
            algorithm_params ={},
            n_obj = 1,
            n_constr = 0,
            type_var = np.int,
            
        ):

        self.set_algorithm(algorithm, algorithm_params)

        self.problem = StrategyTunningProblem(
            strategy=strategy,
            ta=ta,
            n_var=n_var,
            xu=xu,
            xl=xl,
            n_obj = n_obj,
            n_constr = n_constr,
            type_var = type_var
        )

class StrategyTunningProblem(Problem):
    def __init__(
            self,
            strategy,
            ta,
            n_var,
            xu,
            xl,
            n_obj = 1,
            n_constr = 0,
            type_var = np.int
        ):
        """  
            strategy (Strategy): Strategy to follow
            ta (callable): callable that receives a vector with n_var length and the asset.
                This function must refrech the DatFrame of the Asset-Strategy, in order that the
                buy and sell orders are there to run the Strategy
                Returns Asset 
        """

        self.strategy = strategy
        self.ta = ta

        super().__init__(
            n_var=n_var, 
            n_obj=n_obj,
            n_constr=n_constr, 
            xl=xl, 
            xu=xu, 
            type_var=type_var ,
            elementwise_evaluation=True
        )
    
    def _evaluate(self, x, out, *args, **kwargs):
        x = x.astype(int)

        out["F"] = self.objective_function(x)
    
    def objective_function(self, vector):
        
        self.strategy.asset = self.ta( vector, self.strategy.asset )

        results = self.strategy.run()

        if results is None:
            return np.inf

        return 1 / results[ "acc" ] # So we can maximize accumulated return by minimizing its inverse



        