import pytest
from datetime import date


from trading.processes import Simulation

def test_analysis():
    
    def func(inst):
        return inst.rsi(14).iloc[-1]

    sim = Simulation(
        broker = "binance",
        fiat = "usdt",
        commission=0,
        simulations=10
    )

    sim.analyze(
        frequency="1d",
        test_time=1,
        analysis={
            "RSI":{
                "type":"analysis",
                "function":func,
                "time":60,
                "best":"highest"
            }
        },
        save = False
    )

    print( "Length:\n{}\nResults:\n{}".format(len(sim.results), sim.results) )
        
    assert len(sim.results) > 0, "Length:\n{}\nResults:\n{}".format(len(sim.results), sim.results)


def test_optimize():

    def func(inst):
        return inst.rsi(14).iloc[-1]

    sim = Simulation(
        broker = "binance",
        fiat = "usdt",
        commission=0,
        simulations=10
    )

    sim.analyze(
        frequency="1d",
        test_time=1,
        analysis={
            "RSI":{
                "type":"analysis",
                "function":func,
                "time":60,
                "best":"highest"
            }
        },
        save = True
    )

    sim.optimize(
        time = 1,
        balance_time=15,
        exp_return = False
    )

    assert len(sim.df) > 0, "Len of df is 0"