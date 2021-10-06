# Este archivo debera de ir anexado en el PATH de systema para 
# ser ejecutado

# o ser cambiado a 
# Linux: /usr/local/bin

import sys
from datetime import date, timedelta

from .instrumento import Instrumento
from .func_aux import PWD

carpeta = {
    "1min":"Minutos",
    "1h":"Hora",
    "1d":"Diario",
    "1w":"Semanal",
    "1m":"Mensual"
}

def data_instrumentos( broker ):
    
    if broker == "Bitso":
        from instrumentos import Bitso
        data = Bitso
    elif broker == "Binance":
        from instrumentos import Binance
        data = Binance
    elif broker == "GBM":
        from instrumentos import GBM
        data = GBM
    elif broker == "Tesis":
        from instrumentos import Tesis
        data = Tesis
    else:
        raise ValueError("Broker {} es incorrecto.".format(broker) )
    
    return data

def extract_load(asset, broker, fiat):
    print(i)

    inst = Instrumento(
        simbolo=asset,
        inicio=date(1990, 1, 1),

    )

if __name__ == "__main__":

    broker = sys.argv[1]
    fiat = sys.argv[2]
    frecuencia = sys.argv[3]

    broker = broker.capitalize()

    tiempo_dormir = 14 if broker == "Bitso" else 0.5

    data = data_instrumentos( broker )

    for i in data:
        print(i)