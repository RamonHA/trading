# Clases

# Librerias generales
from copy import copy
from math import e
from typing import ValuesView
import pandas as pd
import numpy as np
import re   # Esta libreria permite dividir el str de frecuencia para 
            # dinamicamente obtener '10min' -> 'm'
from datetime import timedelta, datetime, date
from dateutil import parser
import time
import yfinance as yf

# Instrumento
import ta

# Binance
from binance.client import Client
from binance.enums import *
from dccd.histo_dl import binance

# Bitso
from alpha_vantage.cryptocurrencies import CryptoCurrencies

# Google Trends
from pytrends import dailydata
from pytrends.request import TrendReq

from .instrumentos import *

# Py de llaves secretas para APIs
from .tokens import *

from .func_aux import *

def remuestreo(df, intervalo, frecuencia):

    if not isinstance(df, pd.DataFrame):
        print( "Df no es tipo DataFrame, es {}".format( type(df) ) )
        return None

    aux = df.copy()

    aux.reset_index(inplace = True)

    # Nos aseguramos que haya la columna DF
    if 'Date' not in aux.columns :
        aux.reset_index(inplace = True)
        if 'Date' not in aux.columns:
            raise Exception("No hay columna date en df")
        
    aux.set_index("Date", inplace = True)

    # Nos aseguramos que el indice se datetime
    if aux.index.dtype != np.dtype('<M8[ns]'):
        aux.index = pd.to_datetime( aux.index )

    # Tabla de frecuencias
    fr = {
        's': "S",
        'min': "min",
        'h': "H",
        'd': "D",
        'w': "W",
        'm': "M",
        'sm': "MS",
    }

    aux.reset_index(inplace = True)
    aux = aux.resample( 
        "{}{}".format(intervalo, fr.get(frecuencia, frecuencia) ), 
        on = "Date" 
        ).agg( 
            {"Open":"first", "Close":"last", "High":"max", "Low":"min", "Volume":"sum"} 
        )

    # # Disminuir granularidad, Dia a Mes
    # if aux[self.intervalo] < aux[intervalo]:  
    #     df = df.resample( 'W', on = "Date" ).agg( {"Open":"first", "Close":"last", "High":"max", "Low":"min", "Volume":"sum"} )

    # # Aumentar granularidad, Mes a Dia
    # elif aux[self.intervalo] > aux[intervalo]:
    #     # Primero creamos nuevo index "alargado"
    #     df = df.reindex(pd.date_range(df.head(1).index.item(), df.tail(1).index.item(), freq = intervalo.upper() ), fill_value="NaN")

    #     # Selecciona columnas que no sean tipo float
    #     aux = df.select_dtypes(exclude=['float']).columns
        
    #     # Transforma columnas no float a float
    #     df[aux] = df[aux].apply(pd.to_numeric, downcast='float', errors='coerce')

    #     # Rellenamos NaN con interpolacion (Buscar metodos de Imputation)
    #     df = df.interpolate(method = 'linear')

    return aux


class TimeSeries():
    """ Clase Time Series 
        Esta clase permite definir aquellas variables que sean TimeSeries, y las dota
        de caracteristicas estadisticas, etc.
    """
    def __init__(self):
        self.target = "Close" if type(self) == Instrumento else "Data"
    
    def __repr__(self):
        return '{}: {}'.format(type(self).__name__,  self.simbolo )

    # Propiedades de yahoo finanzas
    @property
    def yf(self):
        if hasattr( self, "_yf" ):
            return self._yf
        else:
            self.yf = yf.Ticker( self.simbolo )
            return self._yf
    
    @yf.setter
    def yf(self, value):
        self._yf = value
    
    # Trend TA

    @property
    def target(self):
        return self._target
    
    @target.setter
    def target(self, value):
        if hasattr(self, "df"):
            assert value in self.df.columns, "No hay {} en Dataframe".format( value )
        else:
            self._target = value

    def dema(self, length, target = None):
        """ Regresa un SERIE de una Doble EMA 

            Se genera una EMA con una largo LENGTH sobre TARGET
            Luego otra ema con el mismo LENGTH, pero sobre la primera EMA.
            La primera multiplicada por 2 (un valor aparentemente aleatorio)
            menos la segunda ema.

            Go long: Target > DEMA
            Go short: Target < DEMA
        """
        self.target = self.target if target is None else target

        self.df['dema1'] = self.ema(length=length, target=target)
        self.df['dema2'] = self.ema(length=length, target='dema1')
        return 2*self.df['dema1'] - self.df['dema2']

    def ema(self, length, target = None):
        """ Regresa una SERIe de Exponential Moving Average """
        self.target = self.target if target is None else target

        return self.df[target].ewm(span = length).mean()
   
    def wma(self, length, target = None):
        """ Regresa una SERIE de Weighted Moving Average """
        self.target = self.target if target is None else target
        weights = np.arange(1, length+1)
        return self.df[target].rolling(length).apply(lambda prices: np.dot(prices, weights)/weights.sum(), raw=True)

class Instrumento(TimeSeries):
    """ Esta clase permite definir un Instrumento Financiero: accion, criptomoneda """
    def __init__(self, 
            simbolo = None, 
            inicio = None, 
            fin = datetime.today(), 
            frecuencia = None,
            broker = None,
            fiat = None,
            desde_api = True,
            sentimiento = False,
            social_media = None,
            **kwargs
            ):
        """  
            frecuencia: https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#timeseries-offset-aliases
                s: segundo
                min: minuto
                h: hora
                d: dia
                b: dia laboral
                w: semana
                m: mes
                sm: semi-mes, (15 y final de mes)
                qs: inicio de trimestre
                q: final de trimestre (trimestre default)
                a: fin de año (año default)
                as: inicio de año

                Todavia no se prepara para que la primera parte sea diferente de 1
            
            fiat (str): BTC, USDT, MXN

            desde_api (boolean): Si se desea descargar desde la api correspondiente o desde el archivo

            sentimiento (boolean): Si es True, y hay una MySQL, entonces se decargara la info de las tablas

            social_media (list): Lista de las REDES SOCIALES a considerar
                                Default = ["Twitter", "Reddit", "Google"], Donde se consideran a TODAS
        
        """

        super().__init__()

        # Inicializacion de variables
        # self.df = pd.DataFrame()
        self.broker = broker

        self.sector = None
        self.name = simbolo             # Lo mismo que la variable simbolo, pero solo se guarda para no tener el Ticker como tal, asuntos de Tesis, eventualmente se eliminara
        self.simbolo = simbolo
        self.fiat = fiat                # fiat no puede ser None
        
        self.sentimiento = sentimiento
        self.desde_api = desde_api

        self.frecuencia = frecuencia # Lower y Upper cases en est ecaso si importan
        self.periodo, self.intervalo = re.findall(r'(\d+)(\w+)', self.frecuencia)[0] if frecuencia is not None else (None, None)
        self.periodo = int(self.periodo) if self.periodo is not None else None

        self.inicio = inicio
        self.fin = fin

    @property
    def inicio(self):
        return self._inicio
    
    @inicio.setter
    def inicio(self, value):
        if value is None:
            self._inicio = None
        elif type(value) == datetime:
            self._inicio = value
        elif type(value) == date:
            self._inicio = datetime.combine(value, datetime.min.time())
        elif type(value) == str:
            self._inicio = parser.parse(value)
        else:
            raise ValueError("Inicio debe ser tipo date, datetime o str con formato valido, sin embargo se entrego {}.".format(type(value)))

    @property
    def fin(self):
        return self._fin

    @fin.setter
    def fin(self, value):
        if value is None:
            self._fin = None
        elif type(value) == datetime:
            self._fin = value
        elif type(value) == date:
            self._fin = datetime.combine(value, datetime.min.time())
        elif type(value) == str:
            self._fin = parser.parse(value)
        else:
            raise ValueError("Inicio debe ser tipo date, datetime o str con formato valido, sin embargo se entrego {}.".format(type(value)))

    @property
    def simbolo(self):
        return self._simbolo

    @simbolo.setter
    def simbolo(self, value):
        if self.broker in ["Bitso", "Binance"]:
            self._simbolo = value  
        elif self.broker == "GBM":
            self._simbolo = GBM[value]["ticker"] if value in GBM else value
            self.sector = GBM[value]["sector"] if value in GBM else value
        elif self.broker == "Tesis":
            if value in Tesis and "ticker" in Tesis[value]:
                self._simbolo = Tesis[value]["ticker"]
                self.sector = Tesis[value]["sector"]
            else:
                self._simbolo = None
        
        # Solo entrara en el ultimo caso
        elif value is None:
            self._simbolo = value

    @property
    def fiat(self):
        return self._fiat
    
    @fiat.setter
    def fiat(self, value):
        if value is None:
            if self.broker in ["Tesis", "GBM", "Bitso"]:
                self._fiat = "MXN"
            elif self.broker in ["Binance"]:
                self._fiat = "USDT"

        else:
            self._fiat = value

    # Data download
    @property
    def df(self):
        if hasattr(self, "_df"):#and self._df is not None:
            return self._df
        elif all( [ self.simbolo, self.inicio, self.broker, self.fiat ] ):
            self.df = {
                "Binance":self.df_binance,
                "Bitso":self.df_bitso,
                "GBM":self.df_gbm,
                "Tesis":self.df_gbm
            }[self.broker]()
            
            if self.periodo != 1:
                self.df = remuestreo( self.df, self.periodo, self.intervalo )

            return self._df

    @df.setter
    def df(self, value):
        if isinstance(value, pd.DataFrame):
            self._df = value
        elif value is None:
            self._df = value
        else:
            raise ValueError("No es tipo DataFrame")

    #     if self.df is not None and len(self.df) > 0:
    #         # La info esta "adelantada" unas 5 horas, 
    #         # esto porque para Binannce y Bitso, el dia termina a las 7pm

    #         # if self.intervalo == "h":
    #         #     self.df.index += timedelta(hours = 5)   

    #         if self.periodo != 1:
    #             self.df = self._remuestreo( self.df, self.frecuencia )

    #         if sentimiento:
    #             self.df = pd.concat([ self.df, self._sentimiento(social_media = social_media) ], axis = 1).dropna()    

    def df_binance(self):
        return self.df_binance_api() if self.desde_api else self.df_binance_archivo()

    def df_binance_api(self):
        # Este path es usado solo para rellenar el parametro de la api de binance
        pwd = PWD("/Binance/dccd")

        aux = {
            'm':'minutely',
            'h':'hourly',
            'd':'daily',
            'w':'weekly'
        }

        b = binance.FromBinance( pwd, crypto=self.simbolo, span= aux[self.intervalo],fiat=self.fiat)

        # Informacion total o informacion de un periodo
        # Este IF tambien pudiera ser un OR, pues se pudiera pedir la informacion de:
        #   lo ultimo a cierto dia
        #   de cierto dia hasta ahora (aunque esto se soluciona con el default de FIN)
        if self.inicio == "last" and self.fin == "now":
            df = self.df_binance_api_historica(b)
        else:
            df = self.df_binance_api_periodo(b)
        
        if df is None:
            return None

        # Formateo
        df.drop(columns = ['date', 'TS', 'time'], inplace=True)
        df.columns = [i.capitalize() for i in df.columns]
        df.set_index('Date', inplace = True)
        df.sort_index(inplace = True)

        return df

    def df_binance_api_historica(self, b):
        """ b = binance object """

        try:
            df =  b.import_data(start = "last", end =  "now" ).get_data()
        except:
            print("Error en la descarga historica de {}".format( self.simbolo + self.fiat ))
            return None

        if self.intervalo == "d":
            end = str(df.iloc[-1]['date'])
            end = datetime.strptime(end, "%Y-%m-%d")
        elif self.intervalo == "h":
            end = str(df.iloc[-1]['Date'])
            end = datetime.strptime(end, "%Y-%m-%d %H:%M:%S")

        while end <= datetime.today():
            
            start = end

            end += (timedelta(days = 500) if self.intervalo == "d" else timedelta(seconds = 500*3600*self.periodo )   )
 
            try:
                aux = b.import_data(start = str(start), end =  str(end) ).get_data()
            except:
                aux = pd.DataFrame()

            df = pd.concat([ df, aux ], axis = 0)

            time.sleep(0.1)

        df.drop_duplicates(inplace = True)
        df.sort_index(inplace = True, ascending=True)

        if len(df) == 0:
            print("Error en la descarga historica de {}".format( self.simbolo + self.fiat ))
            return None

        return df

    def df_binance_api_periodo(self, b):

        # fin = datetime.combine(fin, datetime.min.time())
        # inicio = dateime.combine(inicio, datetime.min.time())

        if self.intervalo == "d":
            days = (self.fin - self.inicio).days
        elif self.intervalo == "h":
            days = ( self.fin - self.inicio ).total_seconds() / 3600

        fin = self.fin

        aux = {
            "h":400,
            "d":450
        }

        if days >= aux[self.intervalo]:
            
            df = pd.DataFrame()
            days_aux = aux[self.intervalo]

            while True:
                
                if self.intervalo == "d":
                    aux_start = fin - timedelta(days = days_aux)
                elif self.intervalo == "h":
                    aux_start = fin - timedelta( seconds = days_aux*3600 )

                try:
                    df_aux = b.import_data(start = str(aux_start), end = str(fin)).get_data()
                except:
                    df_aux = pd.DataFrame()

                df = pd.concat([df, df_aux], axis = 0)

                if self.intervalo == "d":
                    days_aux = (aux_start - self.inicio).days
                elif self.intervalo == "h":
                    days_aux = (aux_start - self.inicio).total_seconds() / 3600

                if days_aux == 0:
                    break

                elif days_aux >= aux[self.intervalo]:
                    days_aux = aux[self.intervalo]
            
                elif len(df_aux) == 0:
                    # Ya se termino
                    break

                fin = aux_start

                time.sleep(0.2)

            df.drop_duplicates(inplace = True)
            df.sort_index(inplace = True, ascending=True)

        else:
            try:
                df = b.import_data(start = str(self.inicio), end = str(fin)).get_data()
                
            except:
                df = pd.DataFrame()    

        if len(df) == 0:
            print("Error en la descarga de {} en el periodo {} al {}".format( self.simbolo, str(self.inicio), str(fin) ))
            return None

        return df

    def df_binance_archivo(self):
        aux = {
            'h':'Hora',
            'd':'Diario',
            'w':'Semanal',
            'm':'Mensual'
        }

        try:
            df = pd.read_csv(PWD("/Binance/Mercado/{}/{}.csv".format(aux[ self.intervalo ], self.simbolo + self.fiat )))
        except:
            print(
                "CSV de {} no existe en intervalo {} en el path {}.".format(
                    self.simbolo + self.fiat, 
                    aux[self.intervalo],
                    PWD("/Binance/Mercado/{}/{}.csv".format(aux[ self.intervalo ], self.simbolo + self.fiat ))
                )
            )
            return None

        col = ["Open","High","Low","Close","Volume","Quotevolume"]

        df.set_index('Date', inplace = True)

        df.index = pd.to_datetime( df.index )

        df = df.loc[ str(self.inicio):str(self.fin) ]

        return df

    def df_bitso(self):
        return self.df_bitso_api() if self.desde_api else self.df_bitso_archivo()

    def df_bitso_api_historica(self):
        cr = CryptoCurrencies(BITSO_AV_KEY, output_format='pandas')
        data, meta_data = cr.get_digital_currency_daily(self.simbolo, self.fiat)

        data.drop(columns = [i for i in data.columns if 'USD' in i], inplace = True)

        data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

        data.sort_index(ascending=True, inplace=True)

        if self.intervalo == "w":
            data = remuestreo(data, self.intervalo)

        return data

    def df_bitso_api(self):

        data = self._df_bitso_api_historica()
        return data.loc[self.inicio:self.fin]

    def df_bitso_archivo(self):
        aux = {
            'h':'Hora',
            'd':'Diario',
            'w':'Semanal',
            'm':'Mensual'
        }

        df = pd.read_csv( PWD("/Bitso/Mercado/{}/{}.csv".format(aux[ self.intervalo ] , self.simbolo + self.fiat) ) )
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace = True)
        
        return df.loc[self.inicio:self.fin]

    def df_gbm(self):
        return self.df_gbm_api() if self.desde_api else self.df_gbm_archivo()

    def df_gbm_api(self):
        aux = { # 1m,2m,5m,15m,30m,60m,90m,1h, 1d (Default),5d,1wk,1mo,3mo
            'min':'1m',
            'h':'1h',
            'd':'1d',
            'w':'1wk',
            'm':'1mo',
            'q':'3mo'
        }

        # if self.intervalo == "w":
        #     df = yf.download(self.simbolo, start = inicio, end = fin, interval='1d' ,progress=False)
        # else:
        if (self.intervalo != "min"):
            df = yf.download(self.simbolo, start = self.inicio, end = self.fin, interval= aux[self.intervalo] ,progress=False)
        else:
            inicio = datetime.combine(self.inicio, datetime.min.time())
            fin = datetime.combine(self.fin, datetime.min.time())

            if (fin - inicio).days <= 7:
                df = yf.download(self.simbolo, start = inicio, end = fin, interval= aux[self.intervalo] ,progress=False)
            else:    

                df = pd.DataFrame()
                fin_aux = fin
                while True:
                    inicio_aux = fin_aux - timedelta(days = 7)

                    if (inicio_aux - inicio).days < 0 :
                        inicio_aux = inicio

                    try:
                        df_aux = yf.download(self.simbolo, start = inicio_aux, end = fin_aux, interval= aux[self.intervalo] ,progress=False)
                    except:
                        df_aux = pd.DataFrame()

                    df = pd.concat([
                                    df, 
                                    df_aux
                                    ], 
                                    axis = 0
                                )

                    # Concat

                    fin_aux = inicio_aux

                    if (fin_aux - inicio).days <= 0:
                        break

                    time.sleep(2)

        # Assertions of data
        if self.intervalo == "m":
            df.reset_index(inplace = True)
            df = df[ df["Date"].astype(str).str.endswith("01") ]
            df.set_index("Date", inplace = True)
        elif self.intervalo == "w" and self.broker == "Tesis":
            df.index = df.index.map( lambda x: x - timedelta(days = 1) )
            df = df.reindex( pd.date_range( df.index[0], df.index[-1], freq = "1W" ), fill_values = "NaN" )
            
            for j in df.columns: df[j] = pd.to_numeric( df[j], errors = "coerce" )

            df.ffill( inplace = True )

        return df

    def df_gbm_archivo(self):
        pwd = PWD("/{}/Mercado/{}/{}.csv")
        
        aux = {
            'min':'Minutos',
            'h':'Hora',
            'd':'Diario',
            'w':'Semanal',
            'm':'Mensual'
        }

        try:
            df = pd.read_csv(pwd.format( self.broker, aux[ self.intervalo ], self.simbolo.replace(".", "") ))
        except:
            return None

        df.rename(columns = {"Unnamed: 0":"Date"}, inplace = True)
        df['Date'] = pd.to_datetime(df['Date'])

        if self.intervalo == "w":
            df = remuestreo(df, intervalo = self.intervalo)
        else:
            df.set_index("Date", inplace = True)

        return df.loc[self.inicio:self.fin]

    def update(self, df = True):
        self.desde_api = True
        
        if df: self.update_df()
    
    def update_df(self):
        aux = {
            'min':'Minutos',
            'h':'Hora',
            'd':'Diario',
            'w':'Semanal',
            'm':'Mensual'
        }

        simbolo = self.simbolo.replace(".", "") if self.broker in ["Tesis", "GBM"] else self.simbolo + self.fiat

        self.df.to_csv( 
            PWD( 
                "/{}/Mercado/{}/{}.csv".format( 
                    self.broker, 
                    aux[ self.intervalo ],  
                    simbolo
                ) 
            ) 
        )

    # Sentiment
    
    def sentimiento(self, social_media = ["Twitter", "Reddit", "Google"], desde_api = False, update = True, keywords = [], dropna = True):
        """  
            social_media (list): Lista de las redes sociales usadas para la descarga de informacion.
                                Default: ["Twitter", "Reddit", "Google"]
            desde_api (bool): Si la informacion sera obtenida de las carpetas ya destinadas a guardar esta informacin
                            o directamente de los API requests.
                            Default: False
            update (bool): Si despues de la carga con desde_api = True se actualizaran las carpetas con la informacion
                            actualizada.
                            Default: True
            keywords (list): Palabras claves a usar cuando se hagan los API Requests
                            Principalmente se dara uso para las descargas de Google Trends.
                            Default: Uso de listas en carpeta ...
            dropna (bool): Debido a la granularidad de la data, y los busquedas realizadas, NaN son freucentes.
                            Defualt: True

        """
        if desde_api:
            pass
        else:
            df = pd.DataFrame()
            for i in social_media:
                try:
                    aux = pd.read_csv(PWD("/{}/Sentimiento/{}/{}.csv".format( self.broker, i, self.simbolo ) ))
                except:
                    continue

                if "Unnamed: 0" in aux.columns: aux.rename(columns ={"Unnamed: 0":"date"}, inplace = True)

                # if "date" in aux.columns:
                aux.set_index("date", inplace = True)
                
                aux.index = pd.to_datetime(aux.index)

                aux.columns += "_{}".format(i)

                df = pd.concat([ df, aux ], axis = 1)

        if dropna:
            df.dropna(inplace = True)

        df.sort_index(inplace = True)

        return df

    def google_trends(self, actualizar = False):
        df = self.google_trends_api if self.desde_api else self.google_trends_archivo
        
        if actualizar: df.to_csv( PWD( "{}/Sentimientos/GoogleTrends/{}/{}.csv".format( self.broker, self.frecuencia, self.simblo ) ) )

        return df
    
    def google_trends_api(self):
        assert Bitso[ self.simbolo ].get("google_trends", False), "No hay ´keywords´ en instrumentos.py de Bitso para la busqueda en Google Trends"

        if self.frecuencia != "1m":
            df = pd.DataFrame()
            for i in Bitso[ self.simbolo ][ "google_trends" ]:
                data = dailydata.get_daily_data(i, 
                                            self.inicio.year, 
                                            self.inicio.month, 
                                            self.fin.year, 
                                            self.fin.month, 
                                            geo = "",
                                            verbose = False,
                                            wait_time = 20
                                )
                
                df = pd.concat([df, data[i]], axis = 1)

                time.sleep(2)
        else:
            
            df = pd.DataFrame()
            for i in Bitso[ self.simbolo ][ "google_trends" ]:
                pytrends = TrendReq(hl = 'en-US', tz = 360)
                pytrends.build_payload(
                    i,
                    cat = 0, # 0 -> All categories, 7 -> Finance 
                    timeframe = "all"
                )

                data = pytrends.interest_over_time()

                if "isPartial" in data.columns: data.drop(columns = ["isPartial"], inplace = True)

                df = pd.concat([df, data[i]], axis = 1)

                time.sleep(1)

        return df

    def google_trends_archivo(self):
        df = pd.read_csv( PWD( "{}/Sentimientos/GoogleTrends/{}/{}.csv".format( self.broker, self.frecuencia, self.simblo ) ) )

        return df

    # # Fundamental Analyzers

    # def _beta(self):
    #     pwd = PWD("/{}/Mercado/Informacion Fundamental/{}.json")

    #     with open( pwd.format(self.broker, self.simbolo) , "r") as fp:
    #         data = json.load(fp)

    #     return float(data["Beta (5Y Monthly)"])

    # def _price_earnings(self):
    #     """ Regresa el Price/Earnings ratio 
        
    #         NOTA: Una compañia que tiene ganancias negativas 
    #         no tiene P/E ratio, por ende, al ejectuar esta funcion
    #         y encontrar ganancias negativas, levantara un error.
    #     """
    #     return (self.df.iloc[-1]['Close'] / self._earnings_per_share()) if self._earnings_per_share() > 0 else 0

    # def _earnings_per_share(self):
    #     """ Regresa el trailing EPS ratio 
        
    #         Earnings per share ratio que es la cantidad 
    #         de ganancias por accion.
    #         La porcion de las ganancias netas que son 
    #         ganadas "por cada accion".
            
    #     """
    #     if not hasattr(self, "ticker"):
    #         self.ticker = yf.Ticker(self.simbolo)
        
    #     return self.ticker.info['trailingEps']

    # def _g_score(self):
    #     raise NotImplementedError

    # def _book_to_market(self, quarterly = True):
    #     """ 
    #         Book to Markt Ratio = Book Value of Equity / Market Value of Equity
    #     """
    #     return self._book_value(quarterly=quarterly)  / self._market_value()

    # def _book_value(self, quarterly = True):
    #     """ 
    #         Regresa una seria del Book Value 
        
    #         De acuerdo a investopedia, book value puede ser calculado:
    #         Book value = Total assets - Total liabilites
    #     """

    #     df = self.ticker.quarterly_balance_sheet.T if quarterly else self.ticker.balance_sheet.T
    #     return pd.DataFrame( df['Total Assets'] - df['Total Liab'] )
    
    # def _market_value(self):
    #     """  
    #         Market Value or Market Capitalization
    #     """
    #     raise NotImplementedError

    # Technical analyzers
        
    def adx(self, length, high = 'High', low = 'Low', close = 'Close'):
        """ Regresa tres SERIES de Average Directional Movement Index 
                                ADX, DI+, DI-

            Mide la fuerza de una tendencia, independiente de su direccion

            Go Long:
            Go Short:
        """
        adx_object = ta.trend.ADXIndicator(high=self.df[high], low=self.df[low], \
            close=self.df[close], window = length)
        
        return adx_object.adx(), adx_object.adx_pos(), adx_object.adx_neg()

    def aroon(self, length, target='Close'):
        """ Regresa tres SERIES de Aroon Indicator 
            arron indicator, aroon_up, aroon_down

            Indica cuando una tendecias es más capaz de cambiar
            de direccion
            aroon_up (uptrend)
            aroon_down (downtrend)
        """
        aroon_object = ta.trend.AroonIndicator(close=self.df[target], \
            window=length)

        return aroon_object.aroon_indicator(), aroon_object.aroon_up(),\
            aroon_object.aroon_down()

    def aroon_down(self, length, target = 'Close'):
        """ Regresa una SERIE de Aroon Indicator 

            Indica cuando una tendencia es más capaz de cambiar de direccion
            (downtrend)
        """
        return ta.trend.arron_down(close=self.df[target], window=length)

    def aroon_up(self, length, target = 'Close'):
        """ Regresa una SERIE de Aroon Indicator 

            Indica cuando una tendencia es más capaz de cambiar de direccion
            (uptrend)
        """
        return ta.trend.arron_up(close=self.df[target], window=length)

    def bollinger_bands(self, length=20, std=2, close='Close'):
        """ Regrea tres SERIES de Bollinger Bands
            High, Medium y Low Band.

            Cuando la banda media es cruzada por el Close
            se considera una señal de compra.
            Y cuando el Close supera a la banda alta,
            se vende.
            * Desconozco que uso puede tener la banda baja.

            Defaults por: https://school.stockcharts.com/doku.php?id=technical_indicators:bollinger_bands
            std (int): Factor para la desviacion estandar
        """

        bb_obj = ta.volatility.BollingerBands(close=self.df[close], \
            window=length, ndev=std)

        return bb_obj.bollinger_hband(), bb_obj.bollinger_mavg(), bb_obj.bollinger_lband()

    def cci(self, length, constant = 0.015, close = 'Close', high = 'High', low = 'Low'):
        """ Regresa una SERIE de Commodity Channel Index 
            
            CCI mide la diferencia entre al cambio en el precio, y su cambio promedio.
            Lecturas positivas indican que el precio esta arriba de su promedio, 
            lo cual significa fuerza.
            Lecturas negaticas indican que el precio esta debajo de su promedio,
            lo cual significa debilidad.
        """
        return ta.trend.CCIIndicator(high=self.df[high], low=self.df[low], close=self.df[close], \
            window=length, constant = constant ).cci()
    
    def dpo(self, length, target = 'Close'):
        """ Regresa una SERIE de Detrended Price Oscillator
            
            Es un indicador que permite remover las tendencias del target
            haciendo capaz, observar sus ciclos.
        """
        return ta.trend.DPOIndicator(close=self.df[target], window=length).dpo()

    def easy_of_movement(self, length, high='High', low='Low', volume='Volume'):
        """ Regresa una SERIE de Easy of Movement 
        
            Hace la relacion entre el cambio de precio contra su volumen.
            Es importante para observar la fuerza de una tendencia.
        """
        return ta.volume.EaseOfMovementIndicator(high=self.df[high], low=self.df[low], \
            volume=self.df[volume], window=length).easy_of_movement()

    def easy_of_movement_signal(self, length, high='High', low='Low', volume='Volume'):
        """ Regresa una SERIE la señal de Easy of Movement
        
            Hace la relacion entre el cambio de precio contra su volumen.
            Es importante para observar la fuerza de una tendencia.
        """
        return ta.volume.EaseOfMovementIndicator(high=self.df[high], low=self.df[low], \
            volume=self.df[volume], window=length).sma_easy_of_movement()
    
    def engulfing(self):
        df = copy(self.df)
        df["o"] = self.df["Open"].diff().apply(lambda x : -1 if x > 0 else 1)
        df["c"] = self.df["Close"].diff().apply(lambda x : 1 if x > 0 else -1)
        return df["o"] + df["c"]

    def force_index(self, length, close='Close', volume='Volume'):
        """ Regresa una SERIe del Force Index 
        
            Ilustra que tan fuerte es la presion para comprar o vender.
            ALtos positivos significa que es fuerte la tendencia a la alza.
            Valores bajos, signica que es fuerte la tendencia a la baja.
        """
        return ta.volume.ForceIndexIndicator(close=self.df[close], volume=self.df[volume], \
            window=length).force_index()

    def hull_ema(self, length, target='Close'):
        """ Regresa una SERIE de Hull Exponential Moving Average 
        
            Obtenido de TradingView
            De acuerdo a tradingview, si mi valor ahorita
            es mayor que el obtenido en t-2, se manda una señal
            de compra, si es menor, de venta.
        """
        self.df['hull_src'] = 2*self.ema(length//2) - self.ema(length)
        return self.ema(int( np.sqrt(length) ), target='hull_src' )

    def hull_twma(self, length, target='Close'):
        """ Regresa una SERIE de Hull Triple Weighted Moving Average 
        
            Obtenido de TradingView
            De acuerdo a tradingview, si mi valor ahorita
            es mayor que el obtenido en t-2, se manda una señal
            de compra, si es menor, de venta.
        """
        self.df['hull_src'] = 3*self.wma(length//3) - self.wma(length//2) - self.wma(length)
        return self.wma(length , target='hull_src' )

    def hull_wma(self, length, target='Close'):
        """ Regresa una SERIE de Hull Weighted Moving Average 
        
            Obtenido de TradingView
            De acuerdo a tradingview, si mi valor ahorita
            es mayor que el obtenido en t-2, se manda una señal
            de compra, si es menor, de venta.
        """
        self.df['hull_src'] = 2*self.wma(length//2) - self.wma(length)
        return self.wma(int( np.sqrt(length) ), target='hull_src' )

    def kama(self, length=10, fast_ema=2, slow_ema=30, close='Close'):
        """ Regresa una SERIE de Kaufman's Adaptative Moving Average 
        
            Una media movil diseñada para reporta la volatilidad del mercado.
            KAMA seguira los precios cuando haya swings pequeños.
            Se ajustara cuando los swings sean más grandes y seguira los
            precios desde una mayor distancia

            Es como una media movil, cuando el precio de cierre
            supere al de KAMA, se mandara una señal de compra ...

            length (int): Periodo para el Efficiency Ratio
            Defaults basados en: https://school.stockcharts.com/doku.php?id=technical_indicators:kaufman_s_adaptive_moving_average
        """
        return ta.momentum.KAMAIndicator(close=self.df[close], \
            window=length, pow1=fast_ema, pow2=slow_ema).kama()

    def macd(self, fast, slow, sign, target = 'Close'):
        """ Regresa una SERIE de Moving Average Convergence-Divergence """

        macd_object = ta.trend.MACD(close=self.df[target], window_fast = fast, \
            window_slow = slow, window_sign = sign)

        return macd_object.macd(), macd_object.macd_signal()
    
    def macd_hist(self, fast, slow, sign, target = 'Close'):
        """ Regresa una SERIE de Moving Average Convergence-Divergence Histograma"""
        return ta.trend.MACD(close=self.df[target], n_fast = fast, \
            n_slow = slow, n_sign = sign).macd_diff()

    def macd_signal(self, fast, slow, sign, target = 'Close'):
        """ Regresa una SERIE de Moving Average Convergence-Divergence Signal"""
        return ta.trend.MACD(closE=self.df[target], n_fast = fast, \
            n_slow = slow, n_sign = sign).macd_signal()

    def mass_index(self, low, high=9, low_target = 'Low', high_target = 'High'):
        """ Regresa una SERIE del Mass Index

            Usa el rango High-Low para identificar reversiones en la tendencia
            basandos en la expancion de dicho rango.
            Indentifica protuberancias en los rangos, para identificar reversiones
        """
        return ta.trend.MassIndex(high=self.df[high_target], low=self.df[low_target], \
            window_slow = high, window_fast = low).mass_index()
    
    def momentum(self, periodos, target = "Close"):
        return self.df[target].pct_change(periods = periodos) + 1

    def roc(self, length, target = 'Close'):
        """ Regresa una SERIE de Rate of Change

            Mide el cambio porcentual del target de un periodo al siguiente.
            Compara el precio de este periodo con el del "length" periodos atras
        """
        return ta.momentum.ROCIndicator(close=self.df[target], window=length).roc()
    
    def rsi(self, length, target = 'Close'):
        """ Regresa una SERIE del Relative Strength Index 
            
            Compara la magnitud de ganancias y perdidas en un periodo de tiempo,
            para medir la velocidad y movimientos de cambios de precio de un instrumento.
            Es usado principalmente para indentificar zonas de
            sobrevendido o sobrecomprado.
        """
        return ta.momentum.RSIIndicator(close=self.df[target], window=length).rsi()

    def sma(self, length, target = 'Close'):
        """ Regresa una SERIE de Moving Average """
        return self.df[target].rolling(length).mean()

    def stoch(self, length, sma, close = 'Close', high = 'High', low = 'Low'):
        """ Regresa dos SERIES del Stochastic Oscillator
            La primera es la señal stochastica, y la segunda
            es la misma pero con un smooth.
        """

        stoch_object = ta.momentum.StochasticOscillator(high=self.df[high], low=self.df[low], \
            close=self.df[close], window=length, smooth_window=sma)

        return stoch_object.stoch(), stoch_object.stoch_signal()
    
    def support_resistance(self, length, support = 'High', resistance = "Low"):
        """ Regrea dos series indicando los MAXIMOS y 
            MINIMOS de una seria un periodo LENGTH 
            
            Go long: 
                - Si llega a la zona de soporte, y la rompe.
                - Si llega a la zona de resistencia, y sube. 
            Go short:
                - Si llega a la zona de soporte, y baja.
                - Si llega a la zona de resistencia y la rompe. 
            """
        return self.df[support].rolling(length).max(), self.df[resistance].rolling(length).min()

    def tema(self, length, target = 'Close'):
        """ Regresa un SERIE de una Triple EMA 

            Se genera una EMA con una largo LENGTH sobre TARGET
            Luego otra EMA con el mismo LENGTH, pero sobre la primera EMA.
            Se repite el proceso con la segunda EMA
            La primera menos la segunda, por 3 (un valor aparentemente aleatorio)
            mas la ultima

            Go long: Target > TEMA
            Go short: Target < TEMA
        """
        self.df['tema1'] = self.ema(length=length, target=target)
        self.df['tema2'] = self.ema(length=length, target='tema1')
        self.df['tema3'] = self.ema(length=length, target='tema2')
        return 3*(self.df['tema1'] - self.df['tema2']) + self.df['tema3']

    def trix(self, length, close = 'Close'):
        """ Regresa una SERIE de TRIX 
        
            Muestra el cambio porcentual de una trple media movil
            exponencial.
        """
        return ta.trend.TRIXIndicator(close = self.df[close], window=length).trix()

    def tsi(self, high, low, target = 'Close'):
        """ Regresa una SERIE de True Strength Index 
            
            Demuestra la direccion de tendencias, así como condiciones
            de sobrecompra o sobreventa.
        """
        return ta.momentum.TSIIndicator(close=self.df[target], r=high, s=low).tsi()
    
    def uo(self, short, medium, long, wshort, wmedium, wlong, high='High', low='Low', close='Close'):
        """ Regresa una Serie de Ultimate Oscillator 

            Oscilador de momentum que busca capturar el momentum a traves de 
            tres diferentes timeframes.

            short, medium, long (int)
            wshort, wmedium, wlong (float)
        """
        return ta.momentum.UltimateOscillator(high=self.df[high], low=self.df[low], \
            close=self.df[close], s=short, m=medium, len=long, ws=wshort, wm=wmedium, wl=wlong).uo()

    def vwap(self, length, high = 'High', low = 'Low', close = 'Close', volume = 'Volume'):

        return ta.volume.VolumeWeightedAveragePrice(high = self.df[high], low=self.df[low], \
            close=self.df[close], volume=self.df[volume], window = length).volume_weighted_average_price()
    
    def vpt(self, close = 'Close', volume = 'Volume'):

        return ta.volume.VolumePriceTrendIndicator( close = self.df[close], \
            volume = self.df[volume] ).volume_price_trend()

    def vortex_indicator(self, length, high='High', low='Low', close='Close'):
        """ Regresa dos SERIES de dos osciladores que captura
            tendencias a la alza y a la baja.
         """
        vi = ta.trend.VortexIndicator(high=self.df[high], low=self.df[low], \
            close=self.df[close], window=length)

        return vi.vortex_indicator_pos(), vi.vortex_indicator_neg()

    def william(self, lookback_p, high='High', low='Low', close='Close'):
        """ Regresa una Serie del Williams %R 
        
            Lecturas de entre 0, -20 se considera como sobrecomprado.
            Lecturas de -80, -100 se considera sobrevendido.
        """
        return ta.momentum.WilliamsRIndicator(high=self.df[high], low=self.df[low], close=self.df[close], \
            lbp=lookback_p).wr()

  

