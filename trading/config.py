# Configuration functions
from dateutil.parser import parse
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
    parser.add_argument('--name','-n',  dest = 'name', help = 'API name (Binance, Bitso, Alpha_Vantage). If more than one word, separate it with "_".')
    parser.add_argument('--apikey', '-k' , dest = 'apikey', help = 'Api key')
    parser.add_argument('--secretkey', '-s',  dest = 'secretkey', help = 'API Secret key')
    parser.add_argument('--commission', '-c', dest = 'commission', help = 'Brokers commission fees')
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
    parser.add_argument('--name', '-n', dest = 'name', help = 'API name (Binance, Bitso, Alpha_Vantage). If more than one word, separate it with "_".')
    parser.add_argument('--apikey', '-k', dest = 'apikey', help = 'Api key')
    parser.add_argument('--secretkey', '-s', dest = 'secretkey', help = 'API Secret key')
    args = parser.parse_args()

    if args.name is None:
        raise ValueError("API name must be filled")

    set_keys(args.name, args.apikey, args.secretkey)

@config
def get_api():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', '-n', dest = 'name', help = 'API name (Binance, Bitso, Alpha_Vantage). If more than one word, separate it with "_".')
    args = parser.parse_args()

    if args.name is None:
        raise ValueError("API name must be filled")
    
    print(get_api.data[args.name]  )

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
    parser.add_argument('--broker', '-b', dest = 'broker', help = 'Broker name')
    parser.add_argument('--fiat', '-f', dest = 'fiat', help = 'Fiat to download info (If not, defualt values from Instrumento are taken.)')
    parser.add_argument('--frequency', '-fr', dest = 'frequency', help = 'Data frequency')
    parser.add_argument('--start', '-s', dest = 'start', help = "From which date to start downloading data.")
    parser.add_argument('--from', dest = 'from_', help = "Datasource, Default = yahoo")
    parser.add_argument('--verbose', '-v', dest = 'verbose', help = "Print process", action = "store_true")
    args = parser.parse_args()

    if not (args.broker and args.fiat and args.frequency):
        raise ValueError("All arguments must be filled.")

    start = args.start if args.start is not None else "1990-01-01"

    print("Flags: {} {} {} {} {} {}".format(
        args.broker, args.fiat, args.frequency, start, args.from_, args.verbose
    ))

    from .func_brokers import historic_download
    historic_download(
        broker = args.broker, 
        fiat = args.fiat, 
        frequency = args.frequency, 
        start = start, 
        from_=args.from_,
        verbose = args.verbose
    )

def mev_download():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', '-m', dest = 'mode', help = 'MEV mode (check get_mevs)')
    parser.add_argument('--frequency', '-fr', dest = 'frequency', help = 'Data frequency')
    parser.add_argument('--verbose', '-v', dest = 'verbose', help = "Print process", action = "store_true")
    args = parser.parse_args()

    from .func_brokers import mev_download

    if args.mode is None: args.mode = "all"
    if args.frequency is None: args.frequency = "1m"

    mev_download(
        mode = args.mode,
        frequency = args.frequency,
        verbose = args.verbose
    )

def get_mevs():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument( '--mev', dest = 'mev' )
    parser.add_argument( '--mode', dest = 'mode' )
    parser.add_argument( '--modes', dest = 'modes', action = 'store_true' )
    args = parser.parse_args()

    from .func_aux import get
    mevs = get( "mev/mevs.json" )
    
    if args.modes or args.mode is not None:
        mevs = mevs[ "modes" ]

        if args.mode is not None:
            mevs = mevs[ args.mode ]

    else:
        mevs = mevs["mevs"]

        if args.mev is not None:
            mevs = mevs[args.mev]

    print( mevs )

def add_mevs():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument( '--mev', dest = 'mev' )
    parser.add_argument( '--mode', '-m', dest = 'mode' )
    parser.add_argument( '--source', '-s', dest = 'source' )
    parser.add_argument( '--id', '-i', dest = 'id' )
    parser.add_argument( '--json', '-j', dest = 'json', help='Path to Json file' )
    parser.add_argument( '--overwrite', '-o', dest = 'overwrite', action="store_true" )
    args = parser.parse_args()

    assert (args.mev or args.mode), "Input either mev or mode"

    assert ( args.json or ( args.source or args.id ) ), "Input either path to json file or info of source or id"

    mode = "modes" if args.mode else "mevs"
    var = args.mode if args.mode else args.mev

    import json
    if args.json:
        try:
            with open(args.json, "r") as fp:
                data = json.load(fp)
        except Exception as e:
            print("Could not load json file {}. Exception: {}".format(args.json, e) ) 
            data = {}
    else:
        if mode == "mevs":
            data = { args.source:args.id }
        else:
            data = { args.mev: args.source }

    from .func_aux import get, get_pwd
    mevs = get( "mev/mevs.json" )

    if args.overwrite or ( var not in mevs[mode] ):
        mevs[ mode ][ var ] = data
    else:
        for i, v in data.items():
            mevs[ mode ][ var ][i] = v

    with open( get_pwd( "mev/mevs.json" ), "w" ) as fp:
        json.dump( mevs, fp )
    
    print("Done!")

def get_brokers():
    from .func_aux import get_assets
    assets = list(get_assets().keys())

    print( assets )

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
    parser.add_argument( '--broker', '-b', dest = 'broker' )
    parser.add_argument( '--json', '-j', dest = 'json', help='Path to Json file' )
    parser.add_argument( '--overwrite', '-o', dest = 'overwrite', action = "store_true" , help = "Flag for overwrite all Broker Assets")
    parser.add_argument('--overwrite-asset', '-oa', dest = 'overwrite_asset', action = "store_true", help = 'Flag if wnat to overwrite only asset(s) data without disturbing the rest')
    parser.add_argument( '--augment', '-a', dest = 'augment', action = 'store_true', help = "Flag for adding features/characteristics to Broker Assets. If this flag is not set, and asset is duplicated, then, asset information will be overwritten.")
    parser.add_argument( '--full-overwrite', '-fo', dest = 'fo', action = 'store_true', help = "Flag: Overwrite full assets.json file.")
    # parser.add_argument( '--set', '-s' , dest = "set", action = "store_true", help = "Flag to install assets.json file in package.")
    args = parser.parse_args()

    # if args.set:
    #     from .func_aux import get
    #     data = get("assets.json")
        
    #     with open( get_pwd("assets.json"), "w" ) as fp:
    #         json.dump( data, fp )
        
    #     return

    if args.fo is None and args.broker is None or args.json is None:
        raise ValueError("Broker name or json file requiered")

    if args.overwrite and args.overwrite_asset:
        raise ValueError("Cannot overwerite all assets and specific assets.")

    if (args.overwrite or  args.overwrite_asset) and args.augment:
        raise ValueError("Can not overwrite files while augmenting the information.")

    if (args.overwrite or  args.overwrite_asset) and args.fo:
        raise ValueError("Can not overwrite with specificity and full file.")

    import json
    try:
        with open(args.json, "r") as fp:
            data = json.load(fp)
    except Exception as e:
        print("Could not load json file {}. Exception: {}".format(args.json, e) ) 
        data = {}

    from .func_aux import get_assets, get_pwd

    if args.fo:
        assets = data
    else:
        
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

def octetos():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("broker")
    parser.add_argument("--fiat", '-f', dest = "fiat")
    args = parser.parse_args()

    if args.broker is None and args.broker is None:
        raise ValueError("No broker input")

    from .func_brokers import octetos

    oct = octetos( args.broker, args.fiat )

    import json
    try:
        pwd = pkg_resources.resource_filename("trading", "{}/octetos.json".format(args.broker))

        with open(pwd, 'r') as fp:
            data = json.load(fp)
    except:
        print("octetos.json creation")
        data = {}

    data[ args.fiat ] = oct    

    from .func_aux import PWD

    with open( PWD("{}/octetos.json".format(args.broker)) , "w") as fp:
        json.dump(data, fp)
        
    print("Done!")
