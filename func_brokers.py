
import time
import pandas as pd
from datetime import date, timedelta

from .instrumento import Instrumento
from .func_aux import *
from .tokens import *


def descarga_historica(broker, fiat, frecuencia, verbose = True):

    start = time.time()

    tiempo_dormir = 14 if broker == "Bitso" else 0.5

    pwd = PWD("/{}/Mercado/{}/{}.csv")

    aux = {
        '1min':'Minutos',
        '1h':'Hora',
        '1d':'Diario',
        '1w':'Semanal',
        '1m':'Mensual'
    }

    if broker == "Bitso":
        from .instrumentos import Bitso
        data = Bitso
    elif broker == "Binance":
        from .instrumentos import Binance
        data = Binance
    elif broker == "GBM":
        from .instrumentos import GBM
        data = GBM
    elif broker == "Tesis":
        from .instrumentos import Tesis
        data = Tesis
    else:
        raise ValueError("Broker {} es incorrecto".format(broker))

        
    for i in data:
        print(i)

        inst = Instrumento(
            simbolo = i,
            inicio = date(1990,1,1),
            fin = date.today() - timedelta(days = 1),
            frecuencia=frecuencia,
            fiat = fiat,
            broker = broker,
            desde_api = True
        )

        if inst.df is None or len(inst.df) == 0:
            print("{} no se decargo su tiempo historico, pues puede que no este con dicho FIAT ({})".format(i, fiat))
            continue

        if frecuencia == "1w" and broker in ["Tesis", "GBM"]:
            inst.df.index = inst.df.index.map(lambda x: x - timedelta(days = 1))

            inst.df = inst.df.reindex(pd.date_range(inst.df.head(1).index.item(), inst.df.tail(1).index.item(), freq =  {"1m":"1MS", "1d":"1D", "1w":"1W"}[frecuencia]), fill_value="NaN")
            
            for j in inst.df.columns:
                inst.df[j] = pd.to_numeric( inst.df[j], errors = "coerce" )
            # inst.df[ inst.df.columns ] = pd.to_numeric(inst.df[ inst.df.columns ], errors='coerce')
            
            inst.df.ffill(inplace = True)
        
        elif frecuencia == "1m":
            inst.df.reset_index(inplace = True)
            inst.df = inst.df[ inst.df["Date"].astype(str).str.endswith("01") ]
            inst.df.set_index("Date", inplace = True)

        if broker in ["GBM", "Tesis"]:
            auxx = data[i]["ticker"].replace(".", "")
        else:
            auxx = i + fiat

        inst.df.index.name = "Date"

        # print(auxx)
        inst.df.to_csv(pwd.format(broker, aux[frecuencia], auxx ))

        time.sleep(tiempo_dormir)

    if verbose:
        hours, rem = divmod( time.time()-start , 3600)
        minutes, seconds = divmod(rem, 60)
        print_str = "\nTiempo total de ejecucion: {:0>2}:{:0>2}:{:07.4f}".format(int(hours),int(minutes),seconds)
        print(print_str)

def cantidad_por_sector(acciones, porcentaje = True):

    counter = pd.DataFrame.from_dict( acciones, orient = "index")["sector"].value_counts()
    
    if porcentaje: counter = counter//10 + 2

    return counter.to_dict()

