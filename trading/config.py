# Configuration functions
import pkg_resources

def set_keys_f(name, api_key, secret_key):
    import json 

    try:
        pwd = pkg_resources.resource_filename("trading", "tokens.json")

        with open(pwd, 'r') as fp:
            data = json.load(fp)
    except:
        print("Tokens.json creation")
        data = {}
    
    data[name] = {
        "api_key" : api_key,
        "secret_key" : secret_key 
    }

    with open(pwd, "w") as fp:
        json.dump( data, fp )

    print("{}'s tokens updated correctly!")


def set_keys():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', dest = 'name', help ='API name (Binance, Bitso)')
    parser.add_argument('--apikey', dest = 'apikey', help='Api key')
    parser.add_argument('--secretkey', dest = 'secretkey', help = 'API Secret key')
    args = parser.parse_args()

    set_keys_f(args.name, args.apikey, args.secretkey)