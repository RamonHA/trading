from datetime import datetime, timedelta
import pandas as pd
import time
import warnings
import math

# Binance
from binance.client import Client
from binance.enums import *
from dccd.histo_dl import binance

from .base_asset import BaseAsset
from trading.func_aux import PWD, time_diff, get_config

class Binance(BaseAsset):
    def __init__(
        self, 
        symbol = "", 
        start = None, 
        end = datetime.today(), 
        frequency = "1d", 
        broker = "binance",
        fiat = "USDT", 
        source = "ext_api",
        **kwargs
    ):  
        """  

            account: spot/futures
        """
        
        super().__init__(
            symbol = symbol,
            start = start,
            end = end,
            frequency = frequency,
            source = source,
            broker = broker,
            fiat = fiat,
        )

        self.symbol_aux = self.symbol + self.fiat
        self.default_source = "ext_api"
        self.account = self.get_account(kwargs.get("account", "spot"))(
            symbol = symbol,
            fiat = fiat
        )

    def df_api(self):
        raise NotImplementedError

    def df_ext_api_aux(self, b):
        """ Auxuliar function for df_ext_api """

        def sum_time(start, frequency, t = 400):
            if frequency == "d":
                end = start + timedelta(days = t)
            elif frequency == "h":
                end = start + timedelta(seconds = t*3600)
            elif frequency == "min":
                end = start + timedelta(seconds = t*60)
            
            return end

        start = self.start
        df = pd.DataFrame()
        end = sum_time( start, self.interval )

        while True:
        
            try:
                dff = b.import_data(start = str(start).split(".")[0], end = str(end).split(".")[0]).get_data()
            except:
                dff = pd.DataFrame() 
            
            df = pd.concat( [ df, dff ], axis = 0 )

            tdiff = time_diff( end, self.end, self.interval ) 

            if tdiff == 0:
                break
            elif tdiff > 400:
                start = end
                end = sum_time( start, self.interval )
            else: 
                start = end
                end = self.end
            
            time.sleep(0.2)

        df.drop_duplicates(inplace = True)
    
        return df

    def df_ext_api(self):
        pwd = PWD("/binance/dccd")

        aux = {
            'min':'minutely',
            'h':'hourly',
            'd':'daily',
            'w':'weekly',
            'm':'monthly'
        }
        b = binance.FromBinance( pwd, crypto=self.symbol.upper(), span= aux[self.interval],fiat=self.fiat.upper())

        tdiff = time_diff( self.start, self.end, self.interval )

        if tdiff > 450:
            df = self.df_ext_api_aux( b )
        else:
            try:
                df = b.import_data(start = str(self.start).split(".")[0] , end = str(self.end).split(".")[0] ).get_data()
            except Exception as e:
                warnings.warn("Binance data importation Exception: {}".format(e))
                df = pd.DataFrame()    

        if len(df) == 0: return None

        df.drop(columns = ['date', 'TS', 'time'], inplace=True)
        df.columns = [i.lower() for i in df.columns]
        df.set_index('date', inplace = True)
        df.sort_index(inplace = True)

        return df

    # Bot Functions
    def get_account(self, account):
        if account == "spot":
            return BinanceSpot
        elif account == "futures":
            return BinanceFutures

    @property
    def client(self):
        if hasattr(self, "_client"):
            return self._client
        else:
            self.client = self.get_client()
            return self._client

    @client.setter
    def client(self, value):
        self._client = value

    def get_client(self):
        try:
            api = Client(get_config()[self.broker]["api_key"], get_config()[self.broker]["secret_key"])
        except:
            raise Exception("Problemas Cliente Binance")
        
        return api

    def trading_pairs(self):
        return self.account.trading_pairs(self.client)

    def wallet_balance(self, account = None):
        if account is not None:
            self.account = self.get_account(account)(
                symbol = self.symbol,
                fiat = self.fiat
            )
        
        return self.account.wallet_balance(self.client)

    def buy(self, qty, recursive = True, recursive_step = 1, **kwargs):
        return self.account.buy(self.client, qty, recursive = recursive, recursive_step = recursive_step, **kwargs)

    def wait(self, orderSell):
        return self.account.wait(orderSell)

    @property
    def leverage(self):
        return self.__leverage
    
    @leverage.setter
    def leverage(self, value):
        self.__leverage = self.account.set_leverage( self.client, value )

    @property
    def margin_type(self):
        return self.__margin_type
    
    @margin_type.setter
    def margin_type(self, value):
        self.__margin_type = self.account.set_margin_type( self.client, value )

    def order_complete(self, orders, api, wait = 5):
        
        for c in orders:
            oo = api.get_open_orders(symbol = c)

            while True:
                # Assume order is closed
                close = True

                # Open orders
                for o in oo:
                    if orders[c]['orderId'] == o['orderId']:
                        close = False
                        break

                if close:
                    print("Order for ", c, " IS closed.")
                    break
                else:
                    print("Order for ", c, " IS NOT cloased")
                    # wait 5 seconds for order completion
                    time.sleep( wait )

            # Avoid system overcharge
            time.sleep(1)

class BinanceSpot():
    def __init__(self, symbol, fiat):
        """ 
            Symbol to treat
        """
        self.symbol = symbol
        self.fiat = fiat

    def buy(self, positions, orders_closed = True, wait = 5):
        """ Positions to Buy 
        
            positions (dict): { asset:position }
        """

        api = self.get_client()

        orders = {}
        real_end_order = {}

        for i, v in positions.items():
            print("Buy order for {} for {} positions.".format( i, v ))  
            
            if self.fiat not in i: i = (i + self.fiat).upper()

            try:
                orders[i] = api.order_market_buy(
                    symbol = i,
                    quantity = v
                )
                real_end_order[i] = v
            except:
                orders[i] = api.order_market_buy(
                    symbol = i,
                    quantity = v-1
                )

                real_end_order[i] = v-1
                
            time.sleep(1)

        if orders_closed:
            self.order_complete( orders, api, wait=wait )

        return real_end_order

    def sell_warnings(self, api, asset, qty):

        asset_balance = float( api.get_asset_balance( asset = asset )["free"] )

        if asset_balance == 0: 
            print("No {} in account.".format(asset))
            return None

        elif asset_balance < ( qty*0.9 ):
            print( "Account with {}, lower than considered for sell.".format( asset ) )
            return None

        aux = {
            "BTC":0.0001,
            "USDT":1,                   # Este valor falta configurarlos correctamente (4/06/21)
        }

        if asset_balance*float(api.get_symbol_ticker(symbol = asset)['price']) < aux.get(self.fiat, 1):
            print("Value for {} in account is less than the minimum qty possible.".format( asset ) )
            return None
        
        ## Round position
        asset_info = api.get_symbol_info(symbol=asset)['filters']
        asset_info = [j for j in asset_info if j['filterType'] == 'LOT_SIZE'][0]
        decimals = float( asset_info['stepSize'] )

        if int(decimals) == 0:
            decimals = str(decimals)
            decimals = decimals[::-1].find('.')
            asset_balance = math.floor( asset_balance * pow(10, int(decimals)) ) / pow(10, int(decimals))
        elif int(decimals) != 0:
            asset_balance = math.floor(asset_balance)

        if asset_balance*float(api.get_symbol_ticker(symbol = asset)['price']) < aux.get(self.fiat, 1):
            print("Value for {} in account is less than the minimum qty possible.".format( asset ) )
            return None
        
        return asset_balance

    def sell(self, positions, orders_closed = True, wait = 5):
        """ Positions to Sell 
        
            positions (dict): { asset:position }
        """
        
        api = self.get_client()
        no_sell = []
        orders = {}

        for i, v in positions.items():
            print("Sell order for {} for {} positions.".format( i, v ))

            if self.fiat not in i: i = (i + self.fiat).upper()

            ## Warnings
            asset_balance = self.sell_warnings( api, i, v )
            
            if asset_balance is None:
                no_sell.append( i )
                continue

            ## Save order
            orders[i] = api.order_market_sell(
                symbol = i,
                quantity = asset_balance
            )

            print("Real qty sold for {} is {}.".format( i, asset_balance))

            ## Avoid system overcharge
            time.sleep(1)
        
        if orders_closed:
            self.order_complete( orders, api, wait=wait )
        
        return no_sell

    def value(self):
        """ Value of Portfolio """
        
        api = self.get_client()

        balances = api.get_account()["balances"]

        coins = { i["asset"]:i["free"] for i in balances if i["free"] > 0 }

        portfolio_value = 0
        for k, v in coins.items():
            if k == self.fiat:
                portfolio_value += float(v)
            else:
                try:
                    aux = float(v)*float(api.get_symbol_ticker( symbol = k + self.fiat )['price'])
                    portfolio_value += aux
                except:
                    continue

            time.sleep(0.2)
        
        return portfolio_value

class BinanceFutures():
    def __init__(self, symbol, fiat):
        """ 
            Symbol to treat
        """
        self.symbol = symbol
        self.fiat = fiat

    def trading_pairs(self, client):
        futures_exchange_info = client.futures_exchange_info()  # request info on all futures symbols
        trading_pairs = [info['symbol'] for info in futures_exchange_info['symbols']]
        trading_pairs = [ ( t[:-4], t[-4:] ) for t in trading_pairs if t[-4:] == self.fiat]

        return trading_pairs

    def wallet_balance(self, client):
        return float([ i["balance"] for i in client.futures_account_balance() if i["asset"] == self.fiat][0])

    def set_leverage(self, client, leverage):
        max_leverage = [i for i in client.futures_leverage_bracket() if self.symbol in i["symbol"]][0]["brackets"][0]["initialLeverage"]
        leverage = leverage if max_leverage >= leverage else max_leverage

        try:
            client.futures_change_leverage(symbol=self.symbol, leverage=leverage)
        except Exception as e:
            print(f"Exception : {e}")
            print(e.__dict__)
            print(max_leverage)
            return None

        return leverage
    
    def set_margin_type(self, client, margin_type):
        try:
            client.futures_change_margin_type(symbol=self.symbol, marginType='ISOLATED')
        except Exception as e:
            print(f"Exception : {e}")
            print(e.__dict__)
        
        return margin_type

    def buy(self, client, qty, recursive = True, recursive_step = 1, **kwargs):

        ticker_info = client.get_symbol_info(self.symbol)

        qty_rouding = len(str(float([i["stepSize"] for i in ticker_info["filters"] if i["filterType"] == "LOT_SIZE"][0])).split(".")[-1])

        def set_buy_order(symbol, qty, qty_rouding):
            try:
                qty = round( qty, qty_rouding   )

                orderBuy = client.futures_create_order(
                    symbol = symbol,
                    type = "MARKET",
                    # timeInForce ="GTC",
                    side = "BUY",
                    quantity = qty,
                )
            except Exception as e:
                if e.code == -1111:
                    print("Redo buy order")
                    print(f"Quantity rounding: {qty_rouding}", end = "\t")
                    qty_rouding -= 1
                    print(f"New Quantity rounding: {qty_rouding}")
                    if qty_rouding < 0:
                        return None
                    return set_buy_order(symbol, qty, qty_rouding)
                else:
                    print( f"No order for {symbol}. Exception: {e}")
                    print(type(e), e, e.__dict__)
                    if hasattr(e, "code"):
                        print(e.code)
                    return None

            return orderBuy

        orderBuy = set_buy_order(self.symbol, qty, qty_rouding)

        return orderBuy

    def wait(self, orderSell):
        
        df_trades = pd.DataFrame(self.client.futures_account_trades())

        df_trades = df_trades[ df_trades["orderId"] == orderSell["orderId"] ]

        if len(df_trades) > 0:
            return True
            
        return False