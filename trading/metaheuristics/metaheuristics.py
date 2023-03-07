import numpy as np
# from pymoo.model.problem import Problem
from pymoo.core.problem import ElementwiseProblem

from pymoo.optimize import minimize

class Metaheuristic():
    
    @property
    def algorithm(self):
        return self._algorithm

    def de(self):
        # from pymoo.algorithms.so_de import DE
        from pymoo.algorithms.soo.nonconvex.de import DE

        return  DE(
            pop_size = 100,
            variant="DE/best/2/bin",
            CR = 0.8,
            F = 0.1,
            dither = "scalar",
        )

    @algorithm.setter
    def algorithm(self, value):
        if type(value) == "str":
            self._algorithm = {
                "de":self.de
            }[value]()
        
        else:
            self._algorithm = value

    def set_algorithm(self, algorithm, params):
        self.algorithm = algorithm

        if len(params) > 0 :
            self.algorithm.__dict__ = params

    def optimize(self, gen = 1, verbose = False):
        
        res = minimize(
            self.problem,
            self.algorithm,
            ("n_gen", gen),
            seed = 1,
            verbose = verbose
        )
        
        return res.X.astype(int)

class MetaheuristicProblem(ElementwiseProblem):
    def __init__(
            self,
            objective_function,
            n_var,
            xu,
            xl,
            minimize = True,
            n_obj = 1,
            n_constr = 0,
            type_var = np.int
        ):

        self.minimize = minimize
        self.objective_function = objective_function

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

        out["F"] = self.objective_function(x) if self.minimize else 1/self.objective_function(x)

