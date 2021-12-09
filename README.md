# Trading Environment for research, simulations, and bot setting.

At the moment, this library can work with:
- Stocks obtained from Yahoo Finance:
  - Tested out for Mexican and USA stocks.
- Cryptocurrency APIs:
  - Binance
  - Bitso

Work in progress to integrate more.

## Installation

1. Git clone project
```
$ git clone https://github.com/RamonHA/trading.git
```

2. Inside folder repository create virtual env and activate

'''
$ cd trading
$ python3 -m venv venv_name
$ source venv_name/bin/activate
'''

3. Install repository and dependecies

'''
$ pip3 install .
$ pip3 install -r requirements.txt
'''

### Configuration
1. If no further configuration of the project is requiered, only run on terminal
'''
$ create_config
'''

This will create config file. File that will save the requiered information about paths, tokens, etc.

2. Path (of folder) where historic data, simulation results, and transactions are going to be safe
'''
$ set_pwd -pwd <path/to/folder> 
'''

3. The system, for each broker is already initualize with certain assets. If in desired to change or expand such universe of assets follow (see --help):
'''
$ add_assets
'''

For the case of Binance and Bitso data, and bot creation, followed:
4. Set Brokers APIs keys: 
'''
$ set_keys -name <name of api (Binance, Bitso)> -apikey <APIKEY> -secretkey <SECRETKEY>
'''

5. Set keys for other APIS in use (same function as brokes apis can be used):
'''
$ set_api -name <name of API> -apikey <APIKEY> -secretkey <SECRETEKEY (if needed, not requiered)> 
'''


## Simulations
See examples folder.

## Bot setting
If want direct contact with one of the APIs follow this steps:

1.  ..... (Add instructions)


## References
This library has been used for the simulations carried out in:
- Hinojosa Alejandro, R., Trejo, L. A., Hervert-Escobar, L., Hernández-Gress, N., & González N, E. (2021, October). Mexican Stock Return Prediction with Differential Evolution for Hyperparameter Tuning. In Mexican International Conference on Artificial Intelligence (pp. 355-368). Springer, Cham.