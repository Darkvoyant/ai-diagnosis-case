import pandas as pd

class DataHandler():
    def __init__(self, data: pd.DataFrame):
        self.df = data.copy()
        self._fillna()
        self._add_time(25600)

    def _fillna(self):
        self.df = self.df.fillna(0)
        
    def _add_time(self, sampling_rate_hz=25600):
        self.df['time'] = self.df.index / sampling_rate_hz
    


