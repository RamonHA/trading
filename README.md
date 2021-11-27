# Trading Environment for research, simulations, and bot setting.

At the moment, this library can work with:
- Stocks obtained from Yahoo Finance:
  - Tested out for Mexican and USA stocks.
- Cryptocurrency APIs:
  - Binance
  - Bitso

Work in progress to integrate more.

## Installation
Recommend use of Virtual Environment

You can clone repository:
- git clone https://github.com/RamonHA/trading.git
- cd trading
- pip install .
- cat requirements.txt | 

Requierements file may take time.

### Configuration
The system, for each broker is already initualize with certain assets.
If in desired to change or expand such universe of assets follow:
1. Set APIs keys: 
  - set_keys --name <name of api (Binance, Bitso)> --apikey <APIKEY> --secretkey <SECRETKEY>

2. Set working folder path. This folder will allow us to save historic data, simulation results, and transactions.
  - set_pwd --pwd <path/to/folder>

If in desired to use for Bot configuration, see "Bot setting" section.

## Simulations
See examples folder.

## Bot setting
If want direct contact with one of the APIs follow this steps:

1.  ..... (Add instructions)


## References
This library has been used for the simulations carried out in:
- Hinojosa Alejandro, R., Trejo, L. A., Hervert-Escobar, L., Hernández-Gress, N., & González N, E. (2021, October). Mexican Stock Return Prediction with Differential Evolution for Hyperparameter Tuning. In Mexican International Conference on Artificial Intelligence (pp. 355-368). Springer, Cham.