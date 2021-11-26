
import os
import pandas as pd
import warnings

def PWD(pwd):
    return os.path.normpath( ROUTE.format(pwd) )

def folder_creation(pwd, verbose = True):
    # Creacion de carpeta de la estrategia completa, para guardar los correspondientes CSV y JSON
    if not os.path.exists(pwd):
        try:
            os.makedirs(pwd)
        except:
            raise Exception("Folder creation failed {}.".format(pwd))
        else:
            if verbose:
                print("Folder creation {}".format(pwd))
    else:
        if verbose:
            print("Folder already exists {}".format(pwd))

def min_max(df, exception = []):
    
    for i in df.columns:
        if i in exception: continue
        df[i] = ( df[i] - df[i].min() ) / ( df[i].max() - df[i].min())
    
    return df

def bring_results(pwd, data = {}):

    files = os.listdir(pwd)

    if "resumen.csv" in files:
        
        try:
            d = pd.read_csv(pwd + "/resumen.csv")
            data[pwd] = {}
            data[pwd]["sharpe"] = d["net"].mean() / d["net"].std()
            data[pwd]["sortino"] = d["net"].mean() / d[d["net"] < 0]["net"].std()
            data[pwd]["std"] = d["net"].std()
            data[pwd]["neg std"] = d[d["net"] < 0]["net"].std()
            data[pwd]["min net"] = d["net"].min()
            data[pwd]["acc"] = d["acc"].iloc[-1]
            data[pwd]["mean net"] = d["net"].mean()
        except:
            pass

    else:
        new_files = [j for j in files if j.split(".")[-1] not in ["csv", "json", "txt", "png"] ]

        if len(new_files) > 0:
            for i in new_files:
                data = bring_results( pwd + "/{}".format(i), data )

    return data
