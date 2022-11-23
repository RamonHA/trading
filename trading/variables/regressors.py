


def rf(train, test, target, **kwargs):
    from sklearn.ensemble import RandomForestRegressor
    params = kwargs.get("params")

    regr = RandomForestRegressor()

    if params is not None: 
        for i, v in params.items(): regr.__dict__[i] = v



REGR = {
    "rf":rf
}