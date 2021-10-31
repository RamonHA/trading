
from sklearn.preprocessing import MinMaxScaler

class NN():
    def __init__(
            self,
            stationarity = True,
            ensure_stationarity = False,
            **kwargs
        ):
        """  
            stationarity (bool): Si transformar la data a estacionaria con una PRIMERA diferencia
                Default: True

            ensure_stationarity (bool): Hacer las transformaciones necesarias para ASEGURAR
                                        estacionariedad
                Defualt: False

        """

    def scale(self, train, test, scaler = MinMaxScaler(feature_range=(-1, 1)) ):
        
        assert callable(scaler), "scaler tiene que ser una funcion callable, se entego {}".format(type(scaler))

        scaler = scaler.fit(train)
        train_scaled = scaler.transform(train)
        test_scaled = scaler.transform(test)

        self.scaler = scaler

        return train_scaled, test_scaled


    def fit(self):
        raise NotImplementedError
    
    def predict(self):
        raise NotImplementedError
    
    def run(self):
        raise NotImplementedError


class LSTM(NN):
    def __init__(
            self
        ):
        raise NotImplementedError