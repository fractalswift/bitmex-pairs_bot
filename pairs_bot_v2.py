import numpy as np
import csv
import datetime as dt
from datetime import timezone
import bitmex
import requests
import json
import time

import pandas as pd
pd.set_option("display.precision", 9)


record_dict = {
    "A time of script exec": str(dt.datetime.now()),
    "B open positions": 0,
    "C Trade direction": 0,
    "D current PnL": 0,
    "E X ask": 0,
    "F X bid": 0,
    "G Y ask": 0,
    "H Y bid": 0,
    "I Ratio for Shorting R": 0,
    "J Ratio for Longing R": 0,
    "K Signal": 0,
    "L Current action": "",
    "M status": 0,
    "P Time of script completion": 0,
    "N Diff short": 0,
    "O Diff long": 0,
    "Q Current ratio sma": 0
}


# Define the client

client = bitmex.bitmex(
    test=False,
    api_key="YOUR KEY HERE",
    api_secret="YOUR SECRET HERE"
)


# Settings //

X = 'LTCZ19'

Y = 'ADAZ19'

size_multiplier = 24

TP_pct = 2.5  # take profit %

stop_pct = 20  # stop % for individual sides - this is to save on liquidation cost

ratio_lookBack = 350

open_trigger = 3  # pct divergence from mean to open a ratio trade


# Convert settings into the right format for bitmex

stop_dec_long = (100 - stop_pct) / 100
stop_dec_short = (100 + stop_pct) / 100

short_trigger = 1 + (open_trigger / 100)
long_trigger = 1 - (open_trigger / 100)


# Get the asks and bids for both sides of the pair and work out the current ratios

active_instruments = client.Instrument.Instrument_getActive().result()[0]

X_ask = 0
X_bid = 0
Y_ask = 0
Y_ask = 0

for row in active_instruments:

    if row.get('symbol') == X:

        X_ask = row.get('askPrice')
        X_bid = row.get('bidPrice')

    if row.get('symbol') == Y:

        Y_ask = row.get('askPrice')
        Y_bid = row.get('bidPrice')

    else:
        pass


ratio_for_shorting_ratio = X_bid/Y_ask
ratio_for_longing_ratio = X_ask/Y_bid


# Get recent data so we can see what the current SMA(lookBack) of the ratio is


X_parameters = {"binSize": '5m', "partial": False, 'symbol':  X,
                'count': 750, 'reverse': 'true'}

X_hist = requests.get(
    "https://www.bitmex.com/api/v1/trade/bucketed", params=X_parameters)

Y_parameters = {"binSize": '5m', "partial": False, 'symbol': Y,
                'count': 750, 'reverse': 'true'}

Y_hist = requests.get(
    "https://www.bitmex.com/api/v1/trade/bucketed", params=Y_parameters)

X_hist_df = pd.read_json(X_hist.content)

X_hist_df = X_hist_df[['timestamp', 'close']]

Y_hist_df = pd.read_json(Y_hist.content)

Y_hist_df = Y_hist_df[['timestamp', 'close']]


# The dfs are the wrong way up because of bitmex format, so flip them:

X_hist_df = X_hist_df.reindex(index=X_hist_df.index[::-1])
X_hist_df.reset_index(inplace=True, drop=True)

Y_hist_df = Y_hist_df.reindex(index=Y_hist_df.index[::-1])
Y_hist_df.reset_index(inplace=True, drop=True)

ratio_df = X_hist_df.merge(Y_hist_df, how='inner', on='timestamp')

ratio_df['ratio'] = ratio_df.close_x / ratio_df.close_y

ratio_df['ratio_sma'] = ratio_df.ratio.rolling(ratio_lookBack).mean()


# What is the current ratio sma and at what value should positions be opened/closed?

current_ratio_sma = ratio_df.ratio_sma.iloc[-1]

record_dict['Q Current ratio sma'] = current_ratio_sma

open_short_above = (current_ratio_sma * short_trigger)
open_long_below = (current_ratio_sma * long_trigger)

# This is for closing when you are longing the ratio
close_positions_upper = current_ratio_sma * 1.005
# This is for closing when you are shorting the ratio
close_positions_lower = current_ratio_sma * 0.995


# Calculate order sizes for each side of the trade, based on ratio

current_ratio = (ratio_for_longing_ratio + ratio_for_shorting_ratio) / 2

X_size = 1 * size_multiplier
Y_size = round(current_ratio) * size_multiplier


# Get my current positions and direction

positions_dict = client.Position.Position_get().result()[0]

open_positions = 0
X_direction = 'No position'
Y_direction = 'No position'
trade_direction = 'No position'

for row in positions_dict:
    if row.get('isOpen') == True:
        open_positions += 1

        if row.get('symbol') == X:
            position_X_entry_price = row.get('avgEntryPrice')
            if row.get('currentQty') < 0:
                X_direction = 'Short'
            elif row.get('currentQty') > 0:
                X_direction = 'Long'

        if row.get('symbol') == Y:
            position_Y_entry_price = format(row.get('avgEntryPrice'), '.8f')
            if row.get('currentQty') < 0:
                Y_direction = 'Short'
            elif row.get('currentQty') > 0:
                Y_direction = 'Long'


if X_direction == 'Short' and Y_direction == 'Long':
    trade_direction = 'Shorting the ratio'


elif X_direction == 'Long' and Y_direction == 'Short':
    trade_direction = 'Longing the ratio'

else:
    trade_direction = 'No open trade'


record_dict['B open positions'] = str(open_positions)

record_dict['C Trade direction'] = str(trade_direction)


# Functions for bot logic go here ///

def market_close_both_positions():

    # Note this is depricated - but can re-use the TP close code (at bottom of this section) if I want

    client.Order.Order_closePosition(symbol=X).result()
    client.Order.Order_closePosition(symbol=Y).result()


def long_the_ratio_trade():

    # Long the ratio means to buy X and sell Y

    # Set the prices

    stop_x = round((X_bid * stop_dec_long) * 2, 5) / 2
    stop_y = round((Y_ask * stop_dec_short), 8)

    # Sell Y

    response8 = client.Order.Order_new(
        symbol=Y,
        side="Sell",
        orderQty=-(Y_size),
        ordType='Market',
        # price=limit_to_sell
    ).result()

    # Buy X

    response8 = client.Order.Order_new(
        symbol=X,
        side="Buy",
        orderQty=X_size,
        ordType='Market',
        # price=limit_to_buy
    ).result()

    # Set a stop for Y

    response7 = client.Order.Order_new(
        symbol=Y,
        side="Buy",
        ordType='Stop',
        stopPx=stop_y,
        execInst="Close"

    ).result()

    # Set a stop for X

    response7 = client.Order.Order_new(
        symbol=X,
        side="Sell",
        ordType='Stop',
        stopPx=stop_x,
        execInst="Close"

    ).result()

    record_dict['L Current action'] = 'Placed long the ratio trade'


def short_the_ratio_trade():

    # Short the ratio means to sell X and buy Y

    # Set the prices

    stop_x = round((X_ask * stop_dec_short) * 2, 5) / 2
    stop_y = round((Y_bid * stop_dec_long), 8)

    # Sell X

    response8 = client.Order.Order_new(
        symbol=X,
        side="Sell",
        orderQty=-(X_size),
        ordType='Market',
    ).result()

    # Buy Y

    response9 = client.Order.Order_new(
        symbol=Y,
        side="Buy",
        orderQty=Y_size,
        ordType='Market',
    ).result()

    # Set a stop for X

    response7 = client.Order.Order_new(
        symbol=X,
        side="Buy",
        ordType='Stop',
        stopPx=stop_x,
        execInst="Close"

    ).result()

    # Set a stop for Y

    response10 = client.Order.Order_new(
        symbol=Y,
        side="Sell",
        ordType='Stop',
        stopPx=stop_y,
        execInst="Close"

    ).result()

    record_dict['L Current action'] = 'Placed short the ratio trade'


def get_pnl_pct():

    X_pnl = 0
    Y_pnl = 0

    if trade_direction == 'Longing the ratio':

        X_pnl = ((X_bid - position_X_entry_price) /
                 position_X_entry_price) * 100
        Y_pnl = ((float(position_Y_entry_price) - Y_ask) /
                 float(position_Y_entry_price)) * 100

    elif trade_direction == 'Shorting the ratio':

        Y_pnl = ((Y_bid - float(position_Y_entry_price)) /
                 float(position_Y_entry_price)) * 100
        X_pnl = ((float(position_X_entry_price) - X_ask) /
                 float(position_X_entry_price)) * 100

    return Y_pnl + X_pnl


current_diff_short = ratio_for_shorting_ratio / current_ratio_sma
current_diff_long = ratio_for_longing_ratio / current_ratio_sma


# Main bot logic starts here ///


# Generate the signal

signal = 0

if ratio_for_shorting_ratio > open_short_above:
    signal = -1

if ratio_for_longing_ratio < open_long_below:
    signal = 1


# Record everything

record_dict['E X ask'] = X_ask
record_dict['F X bid'] = X_bid
record_dict['G Y ask'] = Y_ask
record_dict['H Y bid'] = Y_bid
record_dict['I Ratio for Shorting R'] = ratio_for_shorting_ratio
record_dict['J Ratio for Longing R'] = ratio_for_longing_ratio
record_dict['K Signal'] = signal

# Execute the strategy

if open_positions == 2:

    try:

        pnl_pct = get_pnl_pct()
        record_dict['D current PnL'] = pnl_pct

        if trade_direction == 'Longing the ratio':
            # If has returned to mean, close the trade whether in profit or not

            if ratio_for_shorting_ratio > close_positions_upper:
                record_dict['L Current action'] = 'returned to mean, closing'
                market_close_both_positions()

            # If is past tp target, close the trade in profit

            if pnl_pct > TP_pct:
                record_dict['L Current action'] = 'Tp triggered, closing'
                market_close_both_positions()

            else:
                record_dict['M status'] = 'Longing the ratio, waiting'

        elif trade_direction == 'Shorting the ratio':
            # If has returned to mean, close the trade whether in profit or not
            if ratio_for_longing_ratio < close_positions_lower:
                record_dict['L Current action'] = 'returned to mean, closing'
                market_close_both_positions()

            # If is past tp target, close the trade in profit

            if pnl_pct > TP_pct:
                record_dict['L Current action'] = 'Tp triggered, closing'
                market_close_both_positions()

            else:
                record_dict['M status'] = 'Shorting the ratio, waiting'

    except Exception:
        record_dict['M status'] = 'Have 2 positions, but something is wrong'


if open_positions == 0:

    # This should nuke any old stops hanging around

    client.Order.Order_cancelAll().result()

    if signal == 1:
        record_dict['L Current action'] = 'opening long'
        long_the_ratio_trade()

    if signal == -1:
        record_dict['L Current action'] = 'opening short'
        short_the_ratio_trade()

    if signal == 0:
        record_dict['L Current action'] = 'signal is 0, doing nothing'


if open_positions == 1:
    record_dict['M status'] = 'I have just one position open so I must have got stopped out. Market closing the other now'
    record_dict['L Current action'] = 'error, market closing both positions'
    market_close_both_positions()


current_diff_short = ratio_for_shorting_ratio / current_ratio_sma
current_diff_long = ratio_for_longing_ratio / current_ratio_sma


record_dict['N Diff short'] = current_diff_short
record_dict['O Diff long'] = current_diff_long

time_of_finish = str(dt.datetime.now())
record_dict['P Time of script completion'] = time_of_finish


record = [
    record_dict.get('A time of script exec'),
    record_dict.get('B open positions'),
    record_dict.get('C Trade direction'),
    record_dict.get('D current PnL'),
    record_dict.get('E X ask'),
    record_dict.get('F X bid'),
    record_dict.get('G Y ask'),
    record_dict.get('H Y bid'),
    record_dict.get('I Ratio for Shorting R'),
    record_dict.get('J Ratio for Longing R'),
    record_dict.get('Q Current ratio sma'),
    record_dict.get('K Signal'),
    record_dict.get('L Current action'),
    record_dict.get('M status'),
    record_dict.get('N Diff short'),
    record_dict.get('O Diff long'),
    record_dict.get('P Time of script completion')
]


with open(r'pairs_bot_log.csv', 'a') as f:
    writer = csv.writer(f)
    writer.writerow(record)
