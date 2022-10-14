from sklearn.metrics import mean_squared_error, mean_absolute_error, precision_score

ERRORS = {
    "rmse":mean_absolute_error,
    "mae":mean_absolute_error,
    "precision":precision_score
}
