import riskfolio.Portfolio as pf
from riskfolio.AuxFunctions import weights_discretizetion

def riskfolio(
            df, 
            valor_portafolio,
            exp_return = None, 
            metodo = "MV",
            optimizacion = "Sharpe",
            tiempo_testeo = None,
            **kwargs
    ):
    """  
        Risk measure used, this time will be variance
        The risk measure used to optimze the portfolio. The default is ‘MV’. Posible values are:

            ’MV’: Standard Deviation.
            ’MAD’: Mean Absolute Deviation.
            ’MSV’: Semi Standard Deviation.
            ’FLPM’: First Lower Partial Moment (Omega Ratio).
            ’SLPM’: Second Lower Partial Moment (Sortino Ratio).
            ’CVaR’: Conditional Value at Risk.
            ’EVaR’: Entropic Value at Risk.
            ’WR’: Worst Realization (Minimax)
            ’MDD’: Maximum Drawdown of uncompounded cumulative returns (Calmar Ratio).
            ’ADD’: Average Drawdown of uncompounded cumulative returns.
            ’CDaR’: Conditional Drawdown at Risk of uncompounded cumulative returns.
            ’EDaR’: Entropic Drawdown at Risk of uncompounded cumulative returns.
            ’UCI’: Ulcer Index of uncompounded cumulative returns.

        Objective function, could be MinRisk, MaxRet, Utility or Sharpe
        Objective function of the optimization model. The default is ‘Sharpe’. Posible values are:

            ’MinRisk’: Minimize the selected risk measure.
            ’Utility’: Maximize the Utility function μw−lϕi(w).
            ’Sharpe’: Maximize the risk adjusted return ratio based on the selected risk measure.
            ’MaxRet’: Maximize the expected return of the portfolio.

    """
    
    df = df.replace([np.inf, -np.inf], np.nan).dropna()

    if len(df) < 2:
        return None, None

    latest_price = df.iloc[-1]

    port = pf.Portfolio(returns = df.pct_change(periods = 1).dropna())

    port.assets_stats()

    if exp_return is not None:
        port.mu = exp_return
    
    model = 'Classic' # Could be Classic (historical), BL (Black Litterman) or FM (Factor Model)
    rm = metodo        
    obj = optimizacion

    hist = True # Use historical scenarios for risk measures that depend on scenarios
    rf = 0 # Risk free rate

    l = 2 # Risk aversion factor, only useful when obj is 'Utility'
            # Es el factor de cuanto un inversionista es capaz de aceptar riesgo

    w = port.optimization(model=model, rm=rm, obj=obj, rf=rf, l=l, hist=hist)

    discrete = weights_discretizetion(w, latest_price, valor_portafolio)

    discrete = discrete[0].to_dict()

    total_money = 0
    for i in discrete:
        total_money += ( latest_price[i]*discrete[i] )

    discrete_weights = {}
    for i in discrete:
        discrete_weights[i] = (latest_price[i]*discrete[i]) / total_money

    return w.to_dict(), discrete_weights