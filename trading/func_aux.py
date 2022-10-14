import json
import os
import pandas as pd
import pkg_resources
import math
from datetime import datetime
import numpy as np
import time

def get_pwd(file):
    return pkg_resources.resource_filename("trading", file)

def get(file):
    pwd = get_pwd(file)

    with open(pwd, 'r') as fp:
        data = json.load(fp)
    
    return data

def get_assets():
    return get("assets.json")

def get_config():    
    return get("config.json")

def get_settings():
    return get("settings.json")

def PWD(pwd):    
    data = get("config.json")
    return os.path.normpath( "{}/{}".format( data["pwd"], pwd) )

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

    if "resume.csv" in files:
        
        try:
            d = pd.read_csv(pwd + "/resume.csv")
            data[pwd] = {}
            data[pwd]["sharpe"] = d["net"].mean() / d["net"].std()
            data[pwd]["sortino"] = d["net"].mean() / d[d["net"] < 0]["net"].std()
            data[pwd]["std"] = d["net"].std()
            data[pwd]["neg std"] = d[d["net"] < 0]["net"].std()
            data[pwd]["min net"] = d["net"].min()
            data[pwd]["acc"] = d["acc"].iloc[-1]
            data[pwd]["mean net"] = d["net"].mean()
        except:
            print("Could not read file ", pwd)
            pass

    else:
        new_files = [j for j in files if j.split(".")[-1] not in ["csv", "json", "txt", "png"] ]

        if len(new_files) > 0:
            for i in new_files:
                data = bring_results( pwd + "/{}".format(i), data )

    return data

def time_diff(start, end, frequency):
    
    # assertions of date and datetime
    
    if frequency == "d":
        diff = ( end - start ).days
    elif frequency == "h":
        diff = ( end - start ).total_seconds() / 3600
    elif frequency == "m":
        diff = ( end - start ).days / 30
    elif frequency == "min":
        diff = ( end - start ).total_seconds() / 60

    return math.ceil( diff )

def get_last_date_file(pwd, file = "json"):

    json_files = [j for j in os.listdir( pwd ) if j.endswith('.{}'.format(file))]

    if len(json_files) == 0: return None

    json_files_order = [ i.split(".")[0] for i in json_files ]

    json_files_order.sort(key = lambda date: datetime.strptime(date, '%Y-%m-%d %H %M %S')) 

    json_files = [i for i in json_files if json_files_order[-1] in i][0]

    return json_files

def prettify_time(time):
    """ 
        Makes a function to prettify time
            Hour:Minuts:Seconds

        time (float): time in seconds 
    """
    hours = time // 3600
    time %= 3600
    minutes = time // 60
    time %= 60
    print( "%02d:%02d:%02d" % (hours, minutes, time) )

def dropna(axis = 1):
    assert axis == 1, NotImplementedError("Axis '0' not implemented yet.")
    
    axis = { 0:"index", 1:"columns" }  

    df = df.replace( [np.inf, -np.inf], np.nan )
        
    names = df.isna().all()
    names = names[ names ].index.to_list()

    return df.drop(columns = names)

def timing(func):
    def wrapper(*arg, **kw):
        '''source: http://www.daniweb.com/code/snippet368.html'''
        t1 = time.time()
        res = func(*arg, **kw)
        t2 = time.time() - t1
        h = int(t2 // 3600)
        a = (t2 % 3600)
        m = int( a / 60 )
        s = a % 60
        
        print( "{}:{}:{:0.2f}".format(h, m, s ) )

        return res

    return wrapper 