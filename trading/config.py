# Configuration functions
import pkg_resources

def config(func):
    import json
    try:
        pwd = pkg_resources.resource_filename("trading", "config.json")

        with open(pwd, 'r') as fp:
            data = json.load(fp)
    except:
        print("Config.json creation")
        data = {}
    
    def wrapped(*args, **kwargs):
        func(*args, **kwargs)
        with open(pwd, "w") as fp:
            json.dump( data, fp )
            
    wrapped.data = data

    return wrapped

@config
def get_config():
    print( get_config.data )

@config
def create_config():
    pass

@config
def set_keys(name, api_key, secret_key):
    set_keys.data[name.lower()] = {
        "api_key" : api_key,
        "secret_key" : secret_key 
    }

@config
def set_fees(name, commission):
    set_fees.data[ name.lower() ] = {
        "commission":float(commission)
    }

def set_broker():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-name', dest = 'name', help = 'API name (Binance, Bitso, Alpha_Vantage). If more than one word, separate it with "_".')
    parser.add_argument('-apikey', dest = 'apikey', help = 'Api key')
    parser.add_argument('-secretkey', dest = 'secretkey', help = 'API Secret key')
    parser.add_argument('-commission', dest = 'commission', help = 'Brokers commission fees')
    args = parser.parse_args()

    if args.name is None:
        raise ValueError("Broker name must be filled")

    if args.commission is not None:
        set_fees(args.name, args.commission)
    else:
        set_keys(args.name, args.apikey, args.secretkey)

def set_api():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-name', dest = 'name', help = 'API name (Binance, Bitso, Alpha_Vantage). If more than one word, separate it with "_".')
    parser.add_argument('-apikey', dest = 'apikey', help = 'Api key')
    parser.add_argument('-secretkey', dest = 'secretkey', help = 'API Secret key')
    args = parser.parse_args()

    if args.name is None:
        raise ValueError("API name must be filled")

    set_keys(args.name, args.apikey, args.secretkey)

@config
def set_pwd_f(pwd):
    set_pwd_f.data["pwd"] = pwd

def set_pwd():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("pwd", help = "Folder destination where asset historic data, simulation and results are to be safe. If does not exist, it will create it.")
    args = parser.parse_args()

    if args.pwd is None:
        raise ValueError("No pwd added")
    
    set_pwd_f(args.pwd)

def historic_download():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-broker', dest = 'broker', help = 'Broker name')
    parser.add_argument('-fiat', dest = 'fiat', help = 'Fiat to download info (If not, defualt values from Instrumento are taken.)')
    parser.add_argument('-frequency', dest = 'frequency', help = 'Data frequency')
    parser.add_argument('-start', dest = 'start', help = "From which date to start downloading data.")
    parser.add_argument('-verbose', dest = 'verbose', help = "Print process", action = "store_true")
    args = parser.parse_args()

    if not (args.broker and args.fiat and args.frequency):
        raise ValueError("All arguments must be filled.")

    start = args.start if args.start is not None else "1990-01-01"

    print("Flags: {} {} {} {} {}".format(
        args.broker, args.fiat, args.frequency, start, args.verbose
    ))

    from .func_brokers import historic_download
    historic_download(
        broker = args.broker, 
        fiat = args.fiat, 
        frequency = args.frequency, 
        start = start, 
        verbose = args.verbose
    )

def get_assets():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument( '-broker', dest = 'broker' )
    args = parser.parse_args()

    from .func_aux import get_assets
    assets = get_assets() if args.broker is None else get_assets()[args.broker.lower()]

    print( assets )

def add_assets():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument( '-broker', dest = 'broker' )
    parser.add_argument( '-json', dest = 'json', help='Path to Json file' )
    parser.add_argument( '-overwrite', dest = 'overwrite', action = "store_true" , help = "Flag for overwrite all Broker Assets")
    parser.add_argument('-overwrite-asset', dest = 'overwrite_asset', action = "store_true", help = 'Flag if wnat to overwrite only asset(s) data without disturbing the rest')
    parser.add_argument( '-augment', dest = 'augment', action = 'store_true', help = "Flag for adding features/characteristics to Broker Assets. If this flag is not set, and asset is duplicated, then, asset information will be overwritten.")
    args = parser.parse_args()

    if args.broker is None or args.json is None:
        raise ValueError("Broker name requiered")

    if args.overwrite and args.overwrite_asset:
        raise ValueError("Cannot overwerite all assets and specific assets.")

    if (args.overwrite or  args.overwrite_asset) and args.augment:
        raise ValueError("Can not overwrite files while augmenting the information.")

    import json
    try:
        with open(args.json, "r") as fp:
            data = json.load(fp)
    except Exception as e:
        raise ValueError("Could not load json file {}. Exception: {}".format(args.json, e) ) 

    from .func_aux import get_assets, get_pwd
    assets = get_assets()

    if args.overwrite:
        assets[ args.broker ] =  data

    elif args.augment:
        for i, v in data.items():
            assets[ args.broker ][ i ].update( v )
    
    else: # = elif args.overwrite_asset:
        assets[ args.broker ].update( data )


    with open( get_pwd("assets.json"), "w" ) as fp:
        json.dump( assets, fp )
    
    print("Done!")