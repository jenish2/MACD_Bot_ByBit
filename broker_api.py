# Author : Jenish Dholariya

from datetime import datetime, timedelta
import pandas as pd
import pytz
from pybit.usdt_perpetual import HTTP


class ByBitAPI:
    TIMEZONE = "UTC"
    LIVE_ENDPOINT = "https://api.bybit.com"
    TESTNET_ENDPOINT = "https://api-testnet.bybit.com"

    def __init__(self, credentials):
        self.API_KEY = credentials['api_key']
        self.API_SECRET = credentials['api_secret']
        self.TESTNET = credentials.get('testnet', False)

    def connect(self) -> None:
        endpoint = self.TESTNET_ENDPOINT if self.TESTNET else self.LIVE_ENDPOINT
        self.client = HTTP(endpoint=endpoint, api_key=self.API_KEY, api_secret=self.API_SECRET)
        print("API Connected successfully")
        print(self.client)

    def get_candle_data(self, symbol: str, timeframe: str) -> pd.DataFrame:
        fromTS = int(
            (datetime.now(pytz.timezone(self.TIMEZONE)) - timedelta(minutes=int(timeframe[:-1]) * 201)).timestamp())
        params = {
            "symbol": symbol,
            "interval": timeframe[:-1],
            "from": fromTS
        }
        data = self.client.query_kline(**params)['result']
        df = pd.DataFrame(data)
        df.set_index('open_time', inplace=True)
        df.index.name = 'datetime'
        df.index = [datetime.fromtimestamp(x, tz=pytz.timezone(self.TIMEZONE)) for x in df.index]
        df = df[['open', 'high', 'low', 'close', 'volume']]
        print("data fetched by api")
        # print(df)
        return df

    def place_order(self, symbol: str, side: str, quantity: float, stop_loss: float = None, take_profit: float = None,
                    order_type: str = "Market"):
        order = self.client.place_active_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            qty=quantity,
            time_in_force="GoodTillCancel",
            reduce_only=False,
            close_on_trigger=False,
            stop_loss=stop_loss,
            take_profit=take_profit
        )
        print(order)

    def get_account_balance(self) -> float:
        """
        Gets realtime free account balance of asset\n
        """
        balance = self.client.get_wallet_balance()
        print(balance)

    def set_leverage(self, symbol, buy_leverage, sell_leverage):
        leverage = self.client.set_leverage(symbol=symbol, buy_leverage=buy_leverage, sell_leverage=sell_leverage)
        print(leverage)

    def get_active_order(self, symbol):
        active_order = self.client.get_active_order(symbol=symbol)
        print(active_order)

    def my_position(self, symbol):
        my_position = self.client.my_position(symbol=symbol)
        print(my_position)

    def close_position(self, symbol):
        close_position = self.client.close_position(symbol=symbol)
        print(close_position)

    def get_ema_long_time(self, symbol: str, timeframe: str,ema_period : int):
        xy=datetime.now(pytz.timezone(self.TIMEZONE))
        fromTS = int(
            (xy - timedelta(minutes=int(timeframe[:-1]) * 201)*2).timestamp())
        params = {
            "symbol": symbol,
            "interval": timeframe[:-1],
            "from": fromTS
        }
        data = self.client.query_kline(**params)['result']
        df = pd.DataFrame(data)

        fromTS = int(
            (xy - timedelta(minutes=int(timeframe[:-1]) * 201)).timestamp())
        params = {
            "symbol": symbol,
            "interval": timeframe[:-1],
            "from": fromTS
        }
        data = self.client.query_kline(**params)['result']
        tf = pd.DataFrame(data)

        df = pd.concat([df,tf])

        df.set_index('open_time', inplace=True)
        df.index.name = 'datetime'
        df.index = [datetime.fromtimestamp(x, tz=pytz.timezone(self.TIMEZONE)) for x in df.index]
        df = df[['open', 'high', 'low', 'close', 'volume']]

        return df.close.ewm(span=ema_period, adjust=False).mean().iat[-1]
