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

    mev = {
        "bonos":{"sie":"SF117753"},
        "cetes":{"sie":"SF43936"},
        "consumo frecuente":{"investing":27260},         # 27260
        "consumo no basico":{"investing":27259},         # 27259
        "dax":{"yahoo":"^GDAXI"},
        "desempleo":{"inegi":"6200093973", "sie":"SL1"},
        "financiero":{"investing":27262},                # 27262, RT 27240
        "industrial":{"investing":27242},                # 27258, RT 27242
        "inpc":{"sie":"SP1"},                            # SP1
        "er":{"yahoo":"MXN=X"},
        "inflacion":{"sie":"SP68257"},
        "intereses":{"sie":"SF3338"},
        "materiales":{"investing":27265},               # 27265, RT 27243
        "mexbol":{"yahoo":"^MXX", "investing":27254},
        "petroleo":{"sie":"SP67185", "yahoo":"CL=F"},
        "pib":{"inegi":"6207061899", "sie":"SR16643"},
        "mexbol":{"yahoo":"^MXX"},
        "nikkei":{"yahoo":"^N225"},
        "reservas internacionales":{"sie":"SF43707"},
        "salud":{"investing":27263},
        "s&p500":{"yahoo":"^GSPC"},
        "sse":{"yahoo":"000001.SS"},
        "telecomunicaciones":{"investing":27266},
        "tsx":{"yahoo":"^GSPTSE"},
    }

    modes = {
        "all":[
            ("petroleo", "yahoo"),
            ("er", "yahoo"),
            ("inflacion", "sie"),
            ("pib", "inegi"),
            ("cetes", "sie"),
            ("inpc", "sie"),
            ("reservas internacionales", "sie"),
            ("desempleo", "inegi"),
            
            ("s&p500", "yahoo"),
            ("sse", "yahoo"),
            ("nikkei", "yahoo"),
            ("tsx", "yahoo"),
            ("dax", "yahoo"),

            ("industrial", "investing"),
            ("materiales", "investing"),
            ("financiero", "investing"),
            ("consumo frecuente", "investing"),
            ("consumo no basico", "investing"),
            ("salud", "investing"),
            ("telecomunicaciones", "investing"),

            ("mexbol", "yahoo")

        ],
    }

    mode = modes.get( mode, mode ) if isinstance(mode, str) else mode
    
    for s in ["sie", "yahoo", "inegi", "investing"]:
        folder_creation( 
                PWD(
                    "MEV/{}/{}".format(
                        s, 
                        aux[ frequency ]
                    )
                )
            )

    for d, s in mode:
        if verbose:
            print( " - Download of : {} - {}".format( d, s ) )
            
        mevv = MEV(
            data = mev[ d ][ s ],
            source = s,
            frequency = frequency,
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



