from setuptools import find_packages
from setuptools import setup

setup(
    name="trading",
    version="1.0.0",
    description="Trading environment for research, simulation, and bot setting.",
    author="Ramon Hinojosa Alejandro",
    url="https://github.com/RamonHA/trading",
    install_requieres=[],
    packages=find_packages(),
    # entry_points = {  # Later on set descarga_historica
    #     "console_scripts":[
    #         "historic_download = trading.descarga_historica"
    #     ]
    # }
)