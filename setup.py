from setuptools import find_packages
from setuptools import setup

setup(
    name="trading",
    version="1.0.0",
    description="Trading environment for research, simulation, and bot setting.",
    author="Ramon Hinojosa Alejandro",
    url="https://github.com/RamonHA/trading",
    packages=find_packages(),
    package_data= { "": ["settings.json", "mev/mevs.json", "assets.json"], } ,
    include_package_data = True,
    entry_points = {  # Later on set descarga_historica
        "console_scripts":[
            "set_broker = trading.config:set_broker",
            "set_pwd = trading.config:set_pwd",
            "get_config = trading.config:get_config",
            "create_config = trading.config:create_config",
            "set_api = trading.config:set_api",
            "get_api = trading.config:get_api",
            "historic_download = trading.config:historic_download",
            "mev_download = trading.config:mev_download",
            "gt_download = trading.config:gt_download",
            "add_assets = trading.config:add_assets",
            "get_assets = trading.config:get_assets",
            "get_brokers = trading.config:get_brokers",
            "octetos = trading.config:octetos",
            "get_mevs = trading.config:get_mevs",
            "add_mevs = trading.config:add_mevs"
        ]
    }
)