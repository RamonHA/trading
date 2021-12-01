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

@config
def create_config():
    pass

def historic_download():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-broker', dest = 'broker', help = 'Broker name')
    parser.add_argument('-fiat', dest = 'fiat', help = 'Fiat to download info (If not, defualt values from Instrumento are taken.)')
    parser.add_argument('-frequency', dest = 'frequency', help = 'Data frequency')
    parser.add_argument('start', dest = 'start', help = "From which date to start downloading data.")
    args = parser.parse_args()

    if not (args.broker and args.fiat and args.frequency):
        raise ValueError("All arguments must be filled.")
    
    from .func_brokers import historic_download
    historic_download(args.broker, args.fiat, args.frequency, args.start)
