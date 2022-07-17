import pandas as pd
from pybit.usdt_perpetual import HTTP
from datetime import datetime, timedelta
import pytz

class ByBitAPI:
    
    TIMEZONE = "UTC"
    LIVE_ENDPOINT = "https://api.bybit.com"
    TESTNET_ENDPOINT = "https://api-testnet.bybit.com"
 
    def __init__(self,credentials):
        self.API_KEY = credentials['api_key']
        self.API_SECRET = credentials['api_secret']
        self.TESTNET = credentials.get('testnet' , False)
        
    def connect(self) -> None:
        endpoint = self.TESTNET_ENDPOINT if self.TESTNET else self.LIVE_ENDPOINT
        self.client = HTTP(endpoint = endpoint , api_key=self.API_KEY , api_secret= self.API_SECRET)
    
    def get_candle_data(self , symbol : str , timeframe : str) -> pd.DataFrame:
        fromTS = int((datetime.now(pytz.timezone(self.TIMEZONE)) - timedelta(days=0.5)).timestamp())
        params = {
			"symbol":symbol,
			"interval":timeframe[:-1],
			"from":fromTS
		}
        data = self.client.query_kline(**params)['result']
        df = pd.DataFrame(data)
        df.set_index('open_time',inplace=True)
        df.index.name = 'datetime'
        df.index = [datetime.fromtimestamp(x, tz=pytz.timezone(self.TIMEZONE)) for x in df.index]
        df = df[['open','high','low','close','volume']]
        return df


    def place_order(self, symbol:str, side:str, quantity:float, orderType:str="MARKET",limitPrice:float=None):
		
        params = {
			"symbol":symbol,
			"side":side.title(),
			"qty":quantity,
			"order_type":orderType.title(),
			"time_in_force":"GoodTillCancel",
			"close_on_trigger":False,
			"reduce_only":False,
		}
        order = self.client.place_active_order(**params)
        print(order)

        
if __name__ == "__main__":
    creds = {
		"api_key":"LvUwGxYmzJ3AztscpZ",
		"api_secret":"l2oPwTAC5adMuuwmPBHEC6zZdgl3TlIk9uR9",
		"testnet":True
	}
    api = ByBitAPI(credentials=creds)
    api.connect()

    symbol = "BTCUSDT"
    timeframe = "5m"
    df = api.get_candle_data(symbol=symbol,timeframe=timeframe)
    # print(df)

    symbol = "BTCUSDT"
    side = "buy"
    quantity = 0.001
    api.place_order(symbol=symbol, side=side, quantity=quantity)

