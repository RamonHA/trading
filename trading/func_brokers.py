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

    if broker.lower() == "binance":
        from binance.client import Client

        try:
            api = Client(get_config()["binance"]["api_key"], get_config()["binance"]["secret_key"])
        except:
            raise Exception("Problemas Cliente Binance")

        octetos = {}

        Binance = get_assets()["binance"]

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

    return octetos

def historic_download(broker, fiat, frequency, start = date(1990, 1, 1), from_ = "yahoo", verbose = False):
    
    if verbose:
        print("Historic Download for {} {} in {} from {} to today, through {}".format( broker, fiat, frequency, start, from_ ))

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

def mev_download(mode = "all", frequency = "1m", verbose = False):
    from trading.mev import MEV
    
    if verbose:
        print("MEV Download: {} - {}".format( mode, frequency ) )

    aux = {
            '1min':'minutes',
            '1h':'hour',
            '1d':'daily',
            '1w':'weekly',
            '1m':'monthly'
        }

    config = get( "mev/mevs.json" )
    mevs = config[ "mevs" ]
    modes = config[ "modes" ]

    mode = modes[mode] if isinstance(mode, str) else mode
    
    for s in ["sie", "yahoo", "inegi", "investing"]:
        folder_creation( 
                PWD(
                    "MEV/{}/{}".format(
                        s, 
                        aux[ frequency ]
                    )
                )
            )

    for d, s in mode.items():
        if verbose:
            print( " - Download of : {} - {}".format( d, s ) )
            
        mevv = MEV(
            data = mevs[ d ][ s ],
            source = s,
            frequency = frequency,
            from_="api"
        )

        mevv.df.to_csv( 
            PWD(
                "MEV/{}/{}/{}.csv".format(
                    s, 
                    aux[ frequency ], 
                    d 
                )
            ) 
        )



