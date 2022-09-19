# Author : Jenish Dholariya

import time
from datetime import datetime
from datetime import timezone
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
        self.API = []
        for credential in self.CREDENTIALS:
            self.API.append(ByBitAPI(credential))
        for api in self.API:
            api.connect()

    # Helper methods
    @staticmethod
    def _tick_on_timeframe(timeframe: str = '1m'):
        cT = datetime.now(pytz.timezone('UTC'))
        if timeframe[-1] == 'm':
            return (cT.second == 0) and (cT.minute % int(timeframe[:-1])) == 0

    @staticmethod
    def nearest_number(number) -> float:
        string_number = str(number)
        i = 0

        for element_index in range(string_number.find(".") + 1, len(string_number)):
            if string_number[element_index] != "0":
                i = element_index
                break

        string_number = string_number[:i + 1]
        return float(string_number)

    def entry_conditions(self, df: pd.DataFrame, symbol: str, timeframe: str):
        current_price = df.close.iat[-1]

        ema = self.API[0].get_ema_long_time(symbol=symbol, timeframe=timeframe, ema_period=self.CONFIG['ema_period'])
        macd, macd_signal, macd_hist = ta.func.MACD(
            df.close,
            fastperiod=self.CONFIG['macd_fast_period'],
            slowperiod=self.CONFIG['macd_slow_period'],
            signalperiod=self.CONFIG['macd_signal_period']
        )

        if self.CONFIG['use_2nd_ema']:
            ema2 = ta.func.EMA(df.close, self.CONFIG['ema_period_2'])
            # Checking for LONG ENTRY
            if ema < ema2.iat[-1] < current_price:
                print("Checking in uptrend + using 2 ema")
                if all([
                    (macd.iat[-1] > macd_signal.iat[-1]) and (macd.iat[-2] < macd_signal.iat[-2]),  # MACD Crossabove
                    macd_hist.iat[-1] > 0,  # Histogram is Green,
                    macd.iat[-1] < 0,  # MACD is below zero line
                ]):
                    return 'Buy'

            # Checking for LONG ENTRY
            elif ema > ema2.iat[-1] > current_price:
                print("Checking in downtrend + using 2 ema")
                if all([
                    (macd.iat[-1] < macd_signal.iat[-1]) and (macd.iat[-2] > macd_signal.iat[-2]),  # MACD Crossbelow
                    macd_hist.iat[-1] < 0,  # Histogram is Red,
                    macd.iat[-1] > 0,  # MACD is above zero line
                ]):
                    return 'Sell'
        else:
            # Checking for LONG ENTRY
            if current_price > ema:
                print("Checking in uptrend")
                if all([
                    (macd.iat[-1] > macd_signal.iat[-1]) and (macd.iat[-2] < macd_signal.iat[-2]),  # MACD Crossabove
                    macd_hist.iat[-1] > 0,  # Histogram is Green,
                    macd.iat[-1] < 0,  # MACD is below zero line
                ]):
                    return 'Buy'

            # Checking for LONG ENTRY
            elif current_price < ema:
                print("Checking in downtrend")
                if all([
                    (macd.iat[-1] < macd_signal.iat[-1]) and (macd.iat[-2] > macd_signal.iat[-2]),  # MACD Crossbelow
                    macd_hist.iat[-1] < 0,  # Histogram is Red,
                    macd.iat[-1] > 0,  # MACD is above zero line
                ]):
                    return 'Sell'
        return ''

    def exit_conditions(self, df, position: dict = None):
        print("Checking for Exit Condition")
        if position['side'] == 'Buy':
            if df.low.iat[-1] <= position['stop_loss']:
                return True, 'stop_loss', True
            elif df.high.iat[-1] >= position['take_profit']:
                return True, 'take_profit', True
        elif position['side'] == 'Sell':
            if df.high.iat[-1] >= position['stop_loss']:
                return True, 'stop_loss', False
            elif df.low.iat[-1] <= position['take_profit']:
                return True, 'take_profit', False
        return False, '', False

    def run(self):
        print("bot started")
        get_percentage = lambda ref, point, side: round((point - ref) * (1 if side == 'buy' else -1) / ref * 100, 3)

        for watch in self.CONFIG["watchlist"]:
            print(watch)
            for api in self.API:
                try:
                    api.set_leverage(symbol=watch['symbol'], buy_leverage=self.CONFIG['leverage'],
                                     sell_leverage=self.CONFIG['leverage'], leverage_only=True)
                except Exception as e:
                    print("Leverage is Previous")
                    print(e)

        print("Leverage Set")
        while True:
            try:
                if self._tick_on_timeframe(timeframe=self.CONFIG["timeframe"]):
                    time.sleep(2)
                    for watch in self.CONFIG["watchlist"]:
                        try:
                            symbol = watch['symbol']
                            timeframe = self.CONFIG['timeframe']
                            df = self.API[0].get_candle_data(symbol=symbol, timeframe=timeframe)
                            if symbol not in self._position:
                                print(f"Checking entry for {symbol}")
                                entry_side = self.entry_conditions(df, symbol=symbol, timeframe=timeframe)
                                print(entry_side)
                                if entry_side:
                                    print("inside Entry side")
                                    current_close = df.close.iat[-1]
                                    if entry_side == "Buy":
                                        stop_loss = min(df.low[-12:])
                                        print("StopLoss Buy Side:- " + str(stop_loss))
                                        print("Current Close" + str(current_close))
                                        take_profit = current_close + abs((current_close - stop_loss) * float(
                                            self.CONFIG['risk_reward_ratio'].split(':')[1]))

                                        print("TargetProfit BuySide:- " + str(take_profit))

                                    if entry_side == "Sell":
                                        stop_loss = max(df.high[-12:])
                                        print("StopLoss Sell Side:- " + str(stop_loss))
                                        print("Current Close" + str(current_close))
                                        take_profit = current_close - abs((current_close - stop_loss) * float(
                                            self.CONFIG['risk_reward_ratio'].split(':')[1]))

                                        print("TargetProfit SellSide:- " + str(take_profit))

                                    if get_percentage(current_close, stop_loss, entry_side) <= 1.5:
                                        quantity_1 = ((self.API[0].get_account_balance() * self.CONFIG[
                                            'leverage']) / self.API[0].get_current_price(symbol=symbol,
                                                                                         timeframe=timeframe))
                                        qtc_string = str(quantity_1)
                                        dot_position = qtc_string.find(".")
                                        if dot_position != -1:
                                            if (len(qtc_string) - (dot_position + 1)) > 4:
                                                quantity = float(qtc_string[:dot_position + 5])
                                            else:
                                                quantity = round(quantity_1, 4)
                                        else:
                                            quantity = round(quantity_1, 4)
                                        # if round(quantity) > 0:
                                        #     quantity = round(quantity)
                                        # else:
                                        #     quantity_1 = round(quantity, 4)
                                        #     quantity = Bot.nearest_number(quantity_1)

                                        signal = {
                                            'symbol': symbol,
                                            'side': entry_side,
                                            'quantity': quantity,
                                            'stop_loss': stop_loss,
                                            'take_profit': take_profit
                                        }
                                        print("Signal:- " + str(signal))
                                        if entry_side == "Buy":
                                            if take_profit > stop_loss:
                                                print("\n\n\n\n")
                                                order_status = []
                                                for api in self.API:
                                                    try:
                                                        order_status.append(api.place_order(symbol=symbol, side='Buy',
                                                                                            quantity=quantity,
                                                                                            stop_loss=stop_loss,
                                                                                            take_profit=take_profit))
                                                    except Exception as e:
                                                        print(e)
                                                if order_status.count(True) > 0:
                                                    print(f'OPEN {entry_side}')
                                                    self._position[symbol] = signal.copy()
                                                    print(self._position)

                                                    dt = datetime.now(timezone.utc)
                                                    utc_time = dt.replace(tzinfo=timezone.utc)
                                                    print(utc_time)

                                                    print("\n\n\n\n")

                                        if entry_side == "Sell":
                                            if take_profit < stop_loss:
                                                print("\n\n\n\n")
                                                order_status = []
                                                for api in self.API:
                                                    try:
                                                        order_status.append(api.place_order(symbol=symbol, side='Sell',
                                                                                            quantity=quantity,
                                                                                            stop_loss=stop_loss,
                                                                                            take_profit=take_profit))
                                                    except Exception as e:
                                                        print(e)

                                                if order_status.count(True) > 0:
                                                    print(f'OPEN {entry_side}')
                                                    self._position[symbol] = signal.copy()
                                                    print(self._position)

                                                    dt = datetime.now(timezone.utc)
                                                    utc_time = dt.replace(tzinfo=timezone.utc)
                                                    print(utc_time)

                                                    print("\n\n\n\n")
                            else:
                                print("inside else of entry")
                                if self._position != {}:
                                    can_exit, exit_type, position_type = self.exit_conditions(df,
                                                                                              self._position[symbol])
                                    print("_________")
                                    print(can_exit)
                                    print(exit_type)
                                    print(position_type)
                                    if can_exit:
                                        if position_type:
                                            print("\n\n\n\n")
                                            print('Exit Sell')

                                            for api in self.API:
                                                try:
                                                    api.close_position(symbol=symbol)
                                                except Exception as e:
                                                    print(e)

                                            print('Sell')
                                            print(exit_type)
                                            print(symbol + "    Position Square Off  ")
                                            del self._position[symbol]

                                            dt = datetime.now(timezone.utc)
                                            utc_time = dt.replace(tzinfo=timezone.utc)
                                            print(utc_time)

                                            print("\n\n\n\n")
                                        else:
                                            print("\n\n\n\n")
                                            print('Exit Buy')

                                            for api in self.API:
                                                try:
                                                    api.close_position(symbol=symbol)
                                                except Exception as e:
                                                    print(e)

                                            print('Buy')
                                            print(exit_type)
                                            print(symbol + "    Position Square Off  ")
                                            del self._position[symbol]

                                            dt = datetime.now(timezone.utc)
                                            utc_time = dt.replace(tzinfo=timezone.utc)
                                            print(utc_time)

                                            print("\n\n\n\n")
                            print("Position:- " + str(self._position))
                        except Exception as e:
                            _ = f"inner loop {e}"
                            print(_)
                            continue
            except Exception as e:
                _ = f"outer loop {e}"
                print(_)
                continue
