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
        
        print("Updated correctly!")
    
    wrapped.data = data

    return wrapped

@config
def set_keys_f(name, api_key, secret_key):
    set_keys_f.data[name.lower()] = {
        "api_key" : api_key,
        "secret_key" : secret_key 
    }

def set_keys():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', dest = 'name', help ='API name (Binance, Bitso, Alpha_Vantage). If more than one word, separate it with "_".')
    parser.add_argument('--apikey', dest = 'apikey', help='Api key')
    parser.add_argument('--secretkey', dest = 'secretkey', help = 'API Secret key')
    args = parser.parse_args()

    if args.name is None or  args.apikey is None:
        raise ValueError("All keys must be filled,")

    set_keys_f(args.name, args.apikey, args.secretkey)

def set_pwd_f(pwd):
    import json
    from .func_aux import folder_creation
    folder_creation(pwd)
    
    try:
        pwd = pkg_resources.resource_filename("trading", "config.json")

        with open(pwd, 'r') as fp:
            data = json.load(fp)
    except:
        print("Config.json creation")
        data = {}
    
    data["pwd"] = pwd


def set_pwd():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--pwd", det = "pwd", help = "Folder destination where asset historic data, simulation and results are to be safe. If does not exist, it will create it.")

    args = parser.parse_args()

    if args.pwd is None:
        raise ValueError("No pwd added")
    
    set_pwd_f(args.pwd)

