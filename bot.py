import time
from datetime import datetime
from threading import Thread

import pandas as pd
import pytz
import talib as ta

from broker_api import ByBitAPI


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
        currentPrice = df.close.iat[-1]
        ema = ta.func.EMA(df.close, self.CONFIG['ema_period'])
        macd, macdSignal, macdHist = ta.func.MACD(
            df.close,
            fastperiod=self.CONFIG['macd_fast_period'],
            slowperiod=self.CONFIG['macd_slow_period'],
            signalperiod=self.CONFIG['macd_signal_period']
        )

        # Checking for LONG ENTRY
        if currentPrice > ema.iat[-1]:
            print("Checking in uptrend")
            if all([
                (macd.iat[-1] > macdSignal.iat[-1]) and (macd.iat[-2] < macdSignal.iat[-2]),  # MACD Crossabove
                macdHist.iat[-1] > 0,  # Histogram is Green,
                macd.iat[-1] < 0,  # MACD is below zero line
            ]):
                return 'Buy'

        # Checking for LONG ENTRY
        elif currentPrice < ema.iat[-1]:
            print("Checking in downtrend")
            if all([
                (macd.iat[-1] < macdSignal.iat[-1]) and (macd.iat[-2] > macdSignal.iat[-2]),  # MACD Crossbelow
                macdHist.iat[-1] < 0,  # Histogram is Red,
                macd.iat[-1] > 0,  # MACD is above zero line
            ]):
                return 'Sell'

        return ''

    def exit_conditions(self, df, position: dict = None):
        print("Checking for Exit Condition")
        print(position['side'])
        if position['side'] == 'Buy':
            if df.low.iat[-1] <= position['stoploss']:
                return True, 'stoploss', True
            elif df.high.iat[-1] >= position['targetprofit']:
                return True, 'targetprofit', True
        elif position['side'] == 'Sell':
            if df.high.iat[-1] >= position['stoploss']:
                return True, 'stoploss', False
            elif df.low.iat[-1] <= position['targetprofit']:
                return True, 'targetprofit', False
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
                                print(entrySide)
                                if entrySide:
                                    print("inside Entry side")
                                    currentClose = df.low.iat[-1]
                                    if entrySide == "Buy":
                                        stop_loss = min(df.high[-12:])
                                        print("StopLoss Buy Side:- " + str(stop_loss))
                                        print("Current Close"+str(currentClose))
                                        take_profit = currentClose + (currentClose - stop_loss) * float(
                                            self.CONFIG['risk_reward_ratio'].split(':')[1])

                                        print("TargetProfit BuySide:- " + str(take_profit))

                                    if entrySide == "Sell":
                                        stop_loss = max(df.high[-12:])
                                        print("StopLoss Sell Side:- " + str(stop_loss))
                                        print("Current Close"+str(currentClose))
                                        take_profit = currentClose - abs((currentClose - stop_loss) * float(
                                            self.CONFIG['risk_reward_ratio'].split(':')[1]))

                                        print("TargetProfit SellSide:- " + str(take_profit))

                                    if get_percentage(currentClose, stop_loss, entrySide) <= 0.35:
                                        signal = {
                                            'symbol': symbol,
                                            'side': entrySide,
                                            'quantity': quantity,
                                            'stop_loss': stop_loss,
                                            'take_profit': take_profit
                                        }
                                        print("Signal:- " + str(signal))
                                        if entrySide == "Buy":
                                            if take_profit > stop_loss:
                                                self.API.place_order(symbol=symbol, side='Buy', quantity=quantity,
                                                                     stop_loss=stop_loss, take_profit=take_profit)
                                                print(f'OPEN {entrySide}')
                                                self._position[symbol] = signal.copy()
                                                print(self._position)
                                        if entrySide == "Sell":
                                            if take_profit < stop_loss:
                                                self.API.place_order(symbol=symbol, side='Sell', quantity=quantity,
                                                                     stop_loss=stop_loss, take_profit=take_profit)
                                                print(f'OPEN {entrySide}')
                                                self._position[symbol] = signal.copy()
                                                print(self._position)
                                else:
                                    print("inside else of entry")
                                    if self._position != {}:
                                        canExit, exitType, positionType = self.exit_conditions(df,
                                                                                               self._position[symbol])

                                        if canExit:
                                            if positionType:
                                                print('Exit Sell')
                                                self.API.place_order(symbol=self._position[symbol]['symbol'],
                                                                     side='Sell',
                                                                     quantity=self._position[symbol]['quantity'])
                                                print('Sell')
                                                print(exitType)
                                                del self._position[symbol]
                                            else:
                                                print('Exit Buy')
                                                self.API.place_order(symbol=self._position[symbol]['symbol'],
                                                                     side='Buy',
                                                                     quantity=self._position[symbol]['quantity'])
                                                print('Buy')
                                                print(exitType)
                                                del self._position[symbol]
                            print("Position:- " + str(self._position))
                        except Exception as e:
                            _ = f"inner loop {e}"
                            print(_)
                            continue
            except Exception as e:
                _ = f"outer loop {e}"
                print(_)
                continue
