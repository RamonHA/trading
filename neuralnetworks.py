
import pandas as pd

from sklearn.preprocessing import MinMaxScaler

from keras.models import Sequential
from keras.layers import Dense
from keras.layers import LSTM

def lstm(X = None, y=None, **kwargs):

    model = Sequential()
    model.add(LSTM(kwargs.get("neurons", 1), batch_input_shape=(kwargs.get("batch_size", 1), X.shape[1], X.shape[2]), stateful=True))
    model.add(Dense(1))
    model.compile(loss='mean_squared_error', optimizer='adam')
    model.fit(X, y, epochs=kwargs.get("nb_epoch", 1), batch_size=kwargs.get("batch_size", 1), verbose=0, shuffle=False)

    return model


class NN():
    def __init__(
            self,
            nn = lstm,
            stationarity = True,
            ensure_stationarity = False,
            **kwargs
        ):
        """  
            nn (callable): Inputs (X, y, **kwargs)

            stationarity (bool): Si transformar la data a estacionaria con una PRIMERA diferencia
                Default: True

            ensure_stationarity (bool): Hacer las transformaciones necesarias para ASEGURAR
                                        estacionariedad
                Defualt: False

        """
        self.nn = lstm

    @property
    def nn(self):
        return self._nn
    
    @nn.setter
    def nn(self, value):
        if callable(value):
            self._nn = value
        else:
            raise ValueError("La red NN tiene que ser una funcion callable pero se entrego {}".format(type(value)))

    def scale(self, train, test, scaler = MinMaxScaler(feature_range=(-1, 1)) ):
        
        # assert callable(scaler), "scaler tiene que ser una funcion callable, se entego {}".format(type(scaler))

        scaler = scaler.fit(train)
        train_scaled = scaler.transform(train)
        test_scaled = scaler.transform(test)

        self.scaler = scaler

        return train_scaled, test_scaled


    def fit(self, train = None, X = None, y=None, **kwargs):

        if X is None:
            if isinstance( train, pd.DataFrame ):
                train = train.values

            X, y = train[:, 0:-1], train[:, -1]
        
        X = X.reshape(X.shape[0], 1, X.shape[1])

        self.model = self.nn( X, y, **kwargs )
    
    def predict(self, test = None, X = None, inverse_transform = True, batch_size = 1):
        if X is None:
            if isinstance( test, pd.DataFrame ):
                test = test.values

            X = test[:, 0:-1]
    
        X = X.reshape(X.shape[0], 1, X.shape[1])

        yhat =  self.model.predict(X, batch_size=batch_size)

        if inverse_transform:
            X = X.reshape((X.shape[0], X.shape[2]))
            array = pd.concat( [ pd.DataFrame(X), pd.DataFrame(yhat)], axis = 1).values
            inverted = self.scaler.inverse_transform(array)

            yhat = inverted[:, -1]
        
        return yhat

    def run(self):
        raise NotImplementedError

