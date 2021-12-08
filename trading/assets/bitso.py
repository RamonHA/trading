from alpha_vantage.cryptocurrencies import CryptoCurrencies

    # def df_bitso(self):
    #     return self.df_bitso_api() if self.desde_api else self.df_bitso_archivo()

    # def df_bitso_api_historica(self):
    #     cr = CryptoCurrencies(DATA["alpha_vantage"]["api_key"], output_format='pandas')
    #     data, meta_data = cr.get_digital_currency_daily(self.symbol, self.fiat)

    #     data.drop(columns = [i for i in data.columns if 'USD' in i], inplace = True)

    #     data.columns = ['Open', 'High', 'Low', 'Close', 'Volume']

    #     data.sort_index(ascending=True, inplace=True)

    #     if self.intervalo == "w":
    #         data = remuestreo(data, self.intervalo)

    #     return data

    # def df_bitso_api(self):

    #     data = self.df_bitso_api_historica()
    #     return data.loc[self.inicio:self.fin]

    # def df_bitso_archivo(self):
    #     aux = {
    #         'h':'Hora',
    #         'd':'Diario',
    #         'w':'Semanal',
    #         'm':'Mensual'
    #     }

    #     df = pd.read_csv( PWD("/Bitso/Mercado/{}/{}.csv".format(aux[ self.intervalo ] , self.symbol + self.fiat) ) )
    #     df['Date'] = pd.to_datetime(df['Date'])
    #     df.set_index('Date', inplace = True)
        
    #     return df.loc[self.inicio:self.fin]
