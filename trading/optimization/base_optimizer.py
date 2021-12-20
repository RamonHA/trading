

class BaseOptimizer():
    def __init__(
            self,
            value,
            limits = (0, 1)
        ):
        self.value = value

    def N(self):
        """ 1/N Optimizer """
        raise NotImplementedError