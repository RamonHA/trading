from scipy import stats, integrate
import numpy as np
import pandas as pd

class ValueStrategy():
    def __init__(self, df, cols = ["target", "data"], **kwargs):
        """  
            Value the application of a strategy
        """
        self.error = None
        self.cols = cols
        self.target = self.cols[0]
        self.data = self.cols[1]

        for i, v in kwargs.items(): self.__dict__[i] = v

        self.df = df

    @property
    def df(self):
        return self.__df

    @df.setter
    def df(self, value):
        assert isinstance(value, pd.DataFrame)
        assert all([ True for c in self.cols if c in value.columns ])
        self.__df = value

    def get_pdf(self, values, method = "gaussian_kde", **kwargs):
        """ 
            Computes the probability density function 
        
            method:
                gaussian_kde: Works for uni-variate and multi-variate data.
        """
        values = values.replace( [np.inf, -np.inf], np.nan ).dropna()

        if len(values) == 0:
            self.error = "No data for pdf"
            # print(self.error)
            return
                
        try:
            self.pdf = stats.gaussian_kde( values )
        except Exception as e:
            self.error = str(e)
            return

    def get_auc(self, **kwargs):
        """ Get area under the curve """
        xmin, xmax = kwargs.get("limits", (0.0, 0.15))
        integral, err = integrate.quad( self.pdf, xmin, xmax)

        return integral

    def get_dist(self, **kwargs):
        """ Get distribution list """
        x = np.linspace( *kwargs.get("limits", (-0.1, 0.1, 100)) )
        return self.pdf(x).tolist() 

    def distribution_similarity(self, **kwargs):
        """  
            Kolmogorov–Smirnov test.
                Null hypothesis says that both distribution are similar.
                    p-values below 5% reject this null hypothesis saying that the distribution are NOT similar.
        """
        unique_values = self.df[ self.target ].unique()

        dist = []
        for i in unique_values:
            self.get_pdf( self.df[ self.df[self.target] == i ][ self.data ] , **kwargs)
            if self.error is not None:
                if "No data" in self.error:
                    self.error += f" with target '{self.target}' = '{i}'"

                # print(self.error)
                return

            dist.append( self.get_dist( **kwargs ) )
        
        if len(dist) == 0: return 

        kst = stats.kstest( *tuple( dist ) )

        return kst.pvalue

    def value(self, method = "distribution_similarity"):
        return {
            "distribution_similarity": self.distribution_similarity
        }[ method ]()
