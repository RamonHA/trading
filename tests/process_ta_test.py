import pytest
from datetime import date
from sklearn.ensemble import RandomForestRegressor
import numpy as np

from trading.processes import Simulation

# def test_analysis():

#     def func(inst):
#         # Funcion para prediccion de ret0rno
#         return inst.rsi(14).iloc[-1]

#     sim = Simulation(
#         broker = "binance",
#         fiat = "usdt",
#         commission=0,
#         simulations=10
#     )

#     sim.analyze(
#         frequency="1d",
#         test_time=1,
#         analysis={
#             "RSI":{
#                 "type":"analysis",
#                 "function":func,
#                 "time":60,
#                 "best":"highest"
#             }
#         },
#         save = False
#     )

#     print( "Length:\n{}\nResults:\n{}".format(len(sim.results), sim.results) )
        
#     assert len(sim.results) > 0, "Length:\n{}\nResults:\n{}".format(len(sim.results), sim.results)


# def test_optimize():

#     def func(inst):
#         return inst.rsi(14).iloc[-1]

#     sim = Simulation(
#         broker = "gbm",
#         fiat = "mx",
#         commission=0,
#         simulations=12,
#         verbose = 3
#     )

#     sim.analyze(
#         frequency="1m",
#         test_time=1,
#         analysis={
#               "RSI":{
#                 "type":"analysis",
#                 "function":func,
#                 "time":60
#             }
#         },
#         save = True,
#         run = False
#     )

#     sim.optimize(
#         balance_time=15,
#         filter = "highest"    ,
#         filter_qty = 5
#         )

#     assert len(sim.df) > 0, "Len of df is 0"


def test_optimize_exp_return():
    def rf(inst):
        inst.df.dropna(inplace = True)
        inst.df["target"] = inst.df["close"].pct_change().shift(-1)

        train = inst.df.iloc[:-1]
        test = inst.df.iloc[-1:]

        train = train.replace( [np.inf, -np.inf], np.nan ).dropna()

        if train is None or len(train) == 0: return None

        regr = RandomForestRegressor()

        regr.fit( train.drop(columns = "target"), train[["target"]] )

        pred = regr.predict( test.drop(columns = "target") )
        

        return pred[-1]

    def func(inst):
        return inst.rsi(14).iloc[-1]

    sim = Simulation(
        broker = "gbm",
        fiat = "mx",
        commission=0,
        simulations=12,
        verbose = 3
    )

    sim.analyze(
        frequency="1m",
        test_time=1,
        analysis={
            "rsi":{
                "type":"analysis",
                "time":60,
                "function":func,
                "filter":"highest",
                "filter_qty":12
            },
            "rf":{
                "type":"prediction",
                "time":240,
                "function":rf,
            }
        },
        save = True,
        run = True
    )

    sim.optimize(
        balance_time=12,
        value = 10000,
        exp_return=True
    )

    assert len(sim.df) > 0, "Len of df is 0"