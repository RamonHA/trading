from setuptools import find_packages
from setuptools import setup

setup(
    name="trading",
    version="1.0.0",
    description="Trading environment for research, simulation, and bot setting.",
    author="Ramon Hinojosa Alejandro",
    url="https://github.com/RamonHA/trading",
    packages=find_packages(),
    package_data= { "": ["settings.json", "assets.json"], } ,
    include_package_data = True,
    entry_points = {  # Later on set descarga_historica
        "console_scripts":[
            "set_broker = trading.config:set_broker",
            "set_pwd = trading.config:set_pwd",
            "get_config = trading.config:get_config",
            "create_config = trading.config:create_config",
            "set_api = trading.config:set_api",
            "historic_download = trading.config:historic_download",
            "mev_download = trading.config:mev_download",
            "add_assets = trading.config:add_assets",
            "get_assets = trading.config:get_assets",
            "get_brokers = trading.config:get_brokers"
        ]
    }
)