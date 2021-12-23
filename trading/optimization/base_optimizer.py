

class BaseOptimizer():
    def __init__(
            self,
            df,
            value = 0,
            exp_returns = None,
            risk = None,
            objective = None,
            time = 1,
            limits = (0, 1),
            target_return = 0
        ):
        self.value = value
        self.df = df
        self.exp_returns = exp_returns
        self.risk = risk.lower()
        self.objective = objective.lower()
        self.time = time
        self.limits = limits
        self.target_return = target_return

    def N(self):
        """ 1/N Optimizer """
        raise NotImplementedError

    def optimize(self):
        raise NotImplementedError