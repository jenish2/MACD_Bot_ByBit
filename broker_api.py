import pandas as pd
from pybit.usdt_perpetual import HTTP
from datetime import datetime, timedelta
import pytz
import talib as ta

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
        fromTS = int((datetime.now(pytz.timezone(self.TIMEZONE)) - timedelta(minutes=int(timeframe[:-1])*201)).timestamp())
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
        print(df)
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

    def set_leverage(self,symbol,buy_leverage,sell_leverage):
        leverage =  self.client.set_leverage(symbol=symbol,buy_leverage=buy_leverage,sell_leverage=sell_leverage)
        print(leverage)


# if __name__ == "__main__":
#     creds = {
#         "api_key": "LvUwGxYmzJ3AztscpZ",
#         "api_secret": "l2oPwTAC5adMuuwmPBHEC6zZdgl3TlIk9uR9",
#         "testnet": True
#     }
#
#     # creds = {
#     #     "api_key": "nTgDS9ouK898eoUDB2",
#     #     "api_secret": "8bGUPn353bhfvaKiFEeNSHWlkvoyGNwz96A4",
#     #     "testnet": False
#     # }
#
#     api = ByBitAPI(credentials=creds)
#     api.connect()
#
# # Get wallet balance
# # api.get_account_balance()
# #
# # # Get candle data
# symbol = "BTCUSDT"
# timeframe = "15m"
# # df = api.get_candle_data_200(symbol=symbol)
# # print(df)
# # ema = ta.func.EMA(df.close, 200)
# # print(ema)
# #
# # macd, macdSignal, macdHist = ta.func.MACD(
# #             df.close,
# #             fastperiod=12,
# #             slowperiod=26,
# #             signalperiod=9
# #         )
# #
# # print(macd)
# # print()
# # print(macdSignal)
# # print()
# # print(macdHist)
# #
# # print("\n\n")
# # print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@2")
# # # print("\n\n")
#
# df = api.get_candle_data(symbol=symbol,timeframe=timeframe)
# print(df)
# ema = ta.func.EMA(df.close,200)
# print(ema)
# ema_panda = df.close.ewm(span=200, adjust=False).mean()
# print(ema_panda)
# #
# #
# # macd, macdSignal, macdHist = ta.func.MACD(
# #             df.close,
# #             fastperiod=12,
# #             slowperiod=26,
# #             signalperiod=9
# #         )
# #
# # print(macd)
# # print()
# # print(macdSignal)
# # print()
# # print(macdHist)
# #
# # Place order
# # symbol = "BTCUSDT"
# # side = "Buy"
# # quantity = 0.001
# # api.place_order(symbol=symbol, side=side, quantity=quantity, stop_loss=22119.0, take_profit=23876.5)
