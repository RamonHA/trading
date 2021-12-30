import json
import time
import pandas as pd
import numpy as np
from datetime import date, timedelta

from .assets import Asset
from .func_aux import *

DATA = get_config()

def cantidad_por_sector(acciones, porcentaje = True):

    counter = pd.DataFrame.from_dict( acciones, orient = "index")["sector"].value_counts()
    
    if porcentaje: counter = counter//10 + 2

    return counter.to_dict()

def octetos(broker, fiat):
    """ Funcion auxiliar para guardar en JSON una lista con 
        los octetos de cada crypto.

        Esta funcion podra ser llamada despues con el objetivo
        de "actualizar" dichas listas 
    """

    if broker == "Binance":
        from binance.client import Client

        try:
            api = Client(DATA["binance"]["api_key"], DATA["binance"]["secret_key"])
        except:
            raise Exception("Problemas Cliente Binance")

        octetos = {}

        from .instrumentos import Binance

        for i in Binance:    
            # Ahora hay que redondear el numero a los decimales especificados
            # por la cryptomoneda
            try:
                asset_info = api.get_symbol_info(symbol=i + fiat)['filters']
            except:
                # print(i)
                # octetos[i] = 8
                continue

            asset_info = [i for i in asset_info if i['filterType'] == 'LOT_SIZE'][0]
            decimals = float( asset_info['stepSize'] )

            if int(decimals) == 0:
                decimals = str(decimals)
                decimals = decimals[::-1].find('.')
            elif int(decimals) == 1:
                decimals = 0
            else:
                decimals = - ( np.log(decimals) / np.log(10) )

            octetos[i] = int(decimals)

            # Solucion temporal en lo que se arregla el problema 
            # de tantos requests
            # octetos[i] = 8

        with open( PWD( "/{}/octetos_{}.json".format(broker, fiat) ) , "w") as fp:
            json.dump(octetos, fp)
        
        print("Done!")

def historic_download(broker, fiat, frequency, start = date(1990, 1, 1), from_ = "yahoo", verbose = False):
    
    if verbose:
        print("Historic Download for {} {} in {} from {} to today".format( broker, fiat, frequency, start ))

    carpeta = {
        '1min':'minutes',
        '1h':'hour',
        '1d':'daily',
        '1w':'weekly',
        '1m':'monthly'
    }

    broker = broker.lower()

    sleep_time = 14 if broker == "bitso" else 0.5

    folder_creation( 
            PWD( 
                "/{}/data/{}".format( 
                    broker, 
                    carpeta[ frequency ]
                ) 
            ) 
        )

    try:
        data = get_assets()[ broker ]
    except Exception as e:
        print("Error con broker {}. Exception: {}".format(broker, e) )

    for i in data:
        print(i)

        try:
            Asset(
                symbol = i,
                start = start,
                end = date.today() - timedelta(days = 1),
                frequency = frequency,
                broker = broker,
                fiat = fiat,
                from_ = from_
            ).update()
        except Exception as e:
            print("No download for {}. Exception: {}".format(i, e) )
            continue
    
        time.sleep( sleep_time )
    
    print("Done!")

