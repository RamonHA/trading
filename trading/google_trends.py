
import pandas as pd

class GoogleTrend():
    def __init__(
            self,
            keywords = []
        ):

        self.keywords = keywords
    
    def month(self):
        df = pd.DataFrame()

        