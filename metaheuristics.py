
from pymoo.core.problem import Problem
from pymoo.core.algorithm import Algorithm
from pymoo.optimize import minimize

def metaheuristics(m):
    if m == "cmaes":
        from pymoo.algorithms.soo.nonconvex.cmaes import CMAES as m
    elif m == "de":
        from pymoo.algorithms.soo.nonconvex.de import DE as m

    else:
        raise ValueError("{} no se encuentre n lista".format(m))

    return m

class ProblemTemplate(Problem):
    def __ini__(
            self,
            n_var = -1,
            n_obj = 1,
            n_constr = 0,
            xl = None,
            xu = None
        ):
        self.__init__( n_var=n_var, n_obj=n_obj, n_constr=n_constr, xl=xl, xu=xu )
    
    def _evaluate(self, x, out, *args, **kwargs):
        raise NotImplementedError

    def objective_function(self):
        raise NotImplementedError

class Metaheuristic(Problem):
    def __ini__(
            self,
            problem,
            metaheuristic,
            meta_param = None,
            **kwargs
        ):

        self.problem = problem
        self.metaheuristic = metaheuristic

        if meta_param is not None: self.meta_param( meta_param )

    @property
    def problem(self):
        return self._problem
    
    @problem.setter
    def problem(self, value):
        if issubclass(value, Problem):
            self._problem = value
        else:
            raise ValueError("Se entrego como problema {}".format(type(value)))

    def meta_param(self, params):
        for i,v in params: self.metaheuristic.__dict__[i] = v

    @property
    def metaheuristic(self):
        return self._metaheuristic
    
    @metaheuristic.setter
    def metaheuristic(self, value):
        if isinstance(value, str):
            self._metaheuristic = metaheuristics( value )
        elif issubclass( value, Algorithm ):
            self._metaheuristic = value
        else:
            raise ValueError("Se entrego como metaheuristica {}".format(type(value)))

    def optimize(self, n_gen, seed = 1, verbose = False):
        self.res =  minimize(
                self.problem,
                self.metaheuristic,
                ("n_gen", n_gen),
                seed = seed,
                verbose = verbose
            )
        
        return self.res