from threading import Thread
from warnings import catch_warnings

from numpy import single
from broker_api import ByBitAPI
from datetime import datetime
import time, pytz
import pandas as pd
import talib as ta


class Bot(Thread):
    _position = {}

    def __init__(self, credentials: dict, config: dict) -> None:
        Thread.__init__(self, daemon=False)
        self.CREDENTIALS = credentials
        self.CONFIG = config
        self.API = ByBitAPI(credentials)
        self.API.connect()

    # Helper methods
    @staticmethod
    def _tick_on_timeframe(timeframe: str = '1m'):
        cT = datetime.now(pytz.timezone('UTC'))
        if timeframe[-1] == 'm':
            return (cT.second == 0) and (cT.minute % int(timeframe[:-1])) == 0

    def entry_conditions(self, df: pd.DataFrame):
        current_price = df.close.iat[-1]
        ema = ta.func.EMA(df.close, self.CONFIG["ema_period"])
        macd, macdSignal, macdHist = ta.func.MACD(
            df.close,
            fastperiod=self.CONFIG['macd_fast_period'],
            slowperiod=self.CONFIG['macd_slow_period'],
            signalperiod=self.CONFIG['macd_signal_period']
        )
        if current_price > ema.iat[-1]:
            print("checking in uptrend")
            if all([macdHist.iat[-1] > 0, macd.iat[-1] < 0,
                    (macd.iat[-1] > macdSignal.iat[-1]) and (macd.iat[-2] < macdSignal.iat[-2])]):
                return "Buy"
        elif current_price < ema.iat[-1]:
            print("checking in downtrend")
            if all([macdHist.iat[-1] < 0, macd.iat[-1] > 0,
                    (macd.iat[-1] < macdSignal.iat[-1]) and (macd.iat[-2] > macdSignal.iat[-2])]):
                return "Sell"
        return ''

    def exit_conditions(self, df, position: dict = None):
        if position['side'] == 'buy':
            if df.low.iat[-1] <= position['stoploss']:
                return True, 'stoploss'
            elif df.high.iat[-1] >= position['targetprofit']:
                return True, 'targetprofit'
        elif position['side'] == 'sell':
            if df.high.iat[-1] >= position['stoploss']:
                return True, 'stoploss'

            elif df.low.iat[-1] <= position['targetprofit']:
                return True, 'targetprofit'

        return False, ''

    def run(self):
        print("bot started")
        get_percentage = lambda ref, point, side: round((point - ref) * (1 if side == 'buy' else -1) / ref * 100, 3)

        while True:
            try:
                if self._tick_on_timeframe(timeframe=self.CONFIG["timeframe"]):
                    time.sleep(2)
                    for watch in self.CONFIG["watchlist"]:
                        try:
                            symbol = watch['symbol']
                            timeframe = self.CONFIG['timeframe']
                            quantity = watch['quantity']
                            df = self.API.get_candle_data(symbol=symbol, timeframe=timeframe)

                            if symbol not in self._position:
                                print(f"Checking entry for {symbol}")
                                entrySide = self.entry_conditions(df)

                                if entrySide:
                                    currentClose = df.low.iat[-1]
                                    if entrySide == "Buy":
                                        stoploss = min(df.high[-12:])
                                        targetprofit = currentClose + (currentClose - stoploss) * float(
                                            self.CONFIG['risk_reward_ratio'].split(':')[1])
                                    if entrySide == "Sell":
                                        stoploss = min(df.high[-12:])
                                        targetprofit = currentClose - (currentClose - stoploss) * float(
                                            self.CONFIG['risk_reward_ratio'].split(':')[1])

                            else:
                                canExit, exitType = self.exit_conditions(df)
                                if canExit:
                                    del self._position[symbol]

                        except Exception as e:
                            print(e)
            except Exception as e:
                print(e)