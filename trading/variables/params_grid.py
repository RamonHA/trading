
DT_R_GRID = {
    "criterion":[ "poisson"],
    "splitter":["best"],
    "max_features":["auto", "sqrt", "log2", None]
}

MLP_R_GRID = {
    "hidden_layer_sizes":[10, 20, 50],
    "activation":[ "logistic"],
    "solver":["adam"],
    "alpha":[ 0.0001, 0.00001, 0.000001],
    "learning_rate":["constant"],
    "learning_rate_init":[0.0001],
    "max_iter":[100],
    "tol":[0.0001]
}

LOG_R_GRID = {
    "penalty":["l1", "l2", "elasticnet", "none"],
    "tol":[0.1, 0.01, 0.001, 0.0001, 0.00001, 0.000001],
    "C":[100, 10, 1, 0.1, 0.01],
    "fit_intercept":[True, False],
    "solver":["newton-cg", "lbfgs", "liblinear", "sag", "saga"],
    "max_iter":[200, 100, 50]
}

LSTM_R_GRID = {
    "nb_epoch":[100, 200, 500, 1000, 2000, 5000, 10000, 20000],
    "neurons":[3,5,7,9]
}

RF_C_GRID = {
    "n_estimators":[10, 20, 50, 100, 200, 500],
    "criterion":["gini", "entropy", "log_loss"],
}

RF_R_GRID = {
    "n_estimators":[10, 20, 50, 100, 200, 500],
    "criterion":["squared_error", "absolute_error", "poisson"],
    "bootstrap":[False],
}

SVM_R_GRID = {
    "kernel":[ "rbf", "sigmoid"],
    "gamma":[ "auto"],
    "tol":[0.01, 0.001, 0.0001, 0.00001],
    "C":[ 0.1, 0.01, 0.001],
    "coef0":[10, 1, 0.1],
    "epsilon":[0.5, 0.1, 0.001],
    "shrinking":[True, False]
}

GRIDS = {
    "dt_r":DT_R_GRID,
    "mlp_r":MLP_R_GRID,
    "log_r":LOG_R_GRID,
    "lstm_r":LSTM_R_GRID,
    "rf_r":RF_R_GRID,
    "svm_r":SVM_R_GRID
}

# Posible class to manually modify the grid, but could be useless as it can be modified by the user
class GenerateGrid():
    def __init__(self, model, **kwargs):
        self.model = model
        for i, v in kwargs.items(): self.__dict__[i] = v
    
    @property
    def grid(self):
        return self.__grid
    
    @grid.setter
    def grid(self, value):
        try:
            self.__grid = {
                "rf":RF_R_GRID
            }[value]

        except:
            raise ValueError(f"Value {value} not available")