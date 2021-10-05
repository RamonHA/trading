
import os

from .tokens import *

def PWD(pwd):
    return os.path.normpath( ROUTE.format(pwd) )

def creacion_carpeta(pwd, verbose = True):
    # Creacion de carpeta de la estrategia completa, para guardar los correspondientes CSV y JSON
    if not os.path.exists(pwd):
        try:
            os.makedirs(pwd)
        except:
            raise Exception("Creacion de la carpeta {} fallo".format(pwd))
        else:
            if verbose:
                print("Creacion de la carpeta {}".format(pwd))
    else:
        if verbose:
            print("Ya existe carpeta {}".format(pwd))

def min_max(df, exception = []):
    
    for i in df.columns:
        if i in exception: continue
        df[i] = ( df[i] - df[i].min() ) / ( df[i].max() - df[i].min())
    
    return df
