
class Setter():
    def __init__(
            self,
            broker = "yahoo_asset",
            fiat = None,
            commission = None,
            assets = None,
            **kwargs
        ):
        self.broker = broker.lower()
        self.commission = commission if commission is not None else get_config()[ self.broker ][ "commission" ]
        self.fiat = fiat if fiat is not None else self.set_fiat()
        self.assets = assets if assets is not None else self.get_assets()

        self.verbose = kwargs.get("verbose", 0)

    def print_func(self, value):
        print( "\n\n", "#"*20, value, "#"*20 )
    
    def print_0(self, value):
        print("- ", value)

    @property
    def assets(self):
        if hasattr(self, "_assets"):
            return self._assets
        else:
            self.assets = self.get_assets()
            return self._assets
    
    @assets.setter
    def assets(self, value):
        if value is not None:
            assert type(value) in [list, dict], "Asset must be a list or dictionary"
            self._assets = value
        else:
            warnings.warn("Asset list is empty")
            self._assets = {}

    def get_assets(self):
        from trading.func_aux import get_assets
        return get_assets().get( self.broker.lower(), None )

    def set_fiat(self):
        # Defaults values
        return {
            "gbm":"mx",
            "bitso":"mx",
            "binance":"usdt"
        }.get(self.broker, None)