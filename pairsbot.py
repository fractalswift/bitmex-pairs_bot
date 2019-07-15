import csv
import datetime as dt
from datetime import timezone
import bitmex
import requests
import json
import time




record_row = []

time_of_script_execution = str(dt.datetime.now())

record_row.append(time_of_script_execution)


# Settings //

# Choose the pair, and their static ratio mean

X = 'XBTUSD'

Y = 'XBTH19'

static_mean = 1.02447


# Choose % deviation for opening short_the_ratio trade

open_short_above = 1.02959343885 
open_long_below =1.01934872802
close_positions_upper =  1.02549555452 
close_positions_lower = 1.02344661235

# Choose order size and leverage

order_size_buy = 3
order_size_sell = -3

# Choose stop loss percents

stop_distance_long = 0.12

stop_distance_short = 0.12

stop_percent = 0.12


limit_for_buy = 1.5      #(in dollars, not %)
limit_for_sell = 1.5


# Define the client

client = bitmex.bitmex(
    test=False,
    api_key="YOUR API KEY",
    api_secret="YOUR API SECRET"
)


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
    
# long the ratio = is buy X and sell Y, short the ratio = long X and buy Y

ratio_X_ask_Y_bid = X_ask/Y_bid   
ratio_X_bid_Y_ask = X_bid/Y_ask 


ratio_for_shorting_ratio = X_bid/Y_ask
ratio_for_longing_ratio = X_ask/Y_bid

signal = 0 

if  ratio_X_ask_Y_bid > open_short_above:  
    signal = -1
    
if ratio_X_bid_Y_ask < open_long_below:
    signal = 1
    


record_row.append('X ask: ' +str(X_ask))
record_row.append('X bid: ' +str(X_bid))
record_row.append('Y ask: ' +str(Y_ask))
record_row.append('Y bid: ' +str(Y_bid))

record_row.append('Ratio for Shorting ratio: ' +str(ratio_X_bid_Y_ask))
record_row.append('Ratio for Longing ratio: ' +str(ratio_X_ask_Y_bid))

record_row.append('Signal: ' + str(signal))

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
            if row.get('currentQty') < 0:
                X_direction = 'Short'
            elif row.get('currentQty') > 0:
                X_direction = 'Long'
        
        if row.get('symbol') == Y:
            if row.get('currentQty') < 0:
                Y_direction = 'Short'
            elif row.get('currentQty') > 0:
                Y_direction = 'Long'
                

if X_direction == 'Short' and Y_direction == 'Long':  
    trade_direction = 'Shorting the ratio'

    
elif X_direction == 'Long' and Y_direction == 'Short':   
    trade_direction = 'Longing the ratio'

else:
    trade_direction = 'I do not have a trade, or I have half of one, or something has gone wrong'

    
record_row.append('open positions: '+str(open_positions))

record_row.append('Trade direction: ' +str(trade_direction))


# Functions for bot logic go here ///

def market_close_both_positions():
    record_row.append('market close both positions')
   
    
    client.Order.Order_closePosition(symbol=X).result()
    client.Order.Order_closePosition(symbol=Y).result()


        

def long_the_ratio_trade():
    
    # Long the ratio means to buy X and sell Y   
    
       # Set the prices
        
        stop_distance = round((X_ask * stop_percent) * 2.0)/ 2.0

        limit_to_buy = round((X_ask + limit_for_buy) * 2.0)/ 2.0
        limit_to_sell = round((Y_bid - limit_for_sell) * 2.0)/ 2.0

        stop_price_for_stop_sell = limit_to_buy - stop_distance   
        stop_price_for_stop_buy = limit_to_sell + stop_distance

        # Sell Y

        response8 = client.Order.Order_new(
            symbol=Y,
            side="Sell",
            orderQty=order_size_sell,
            ordType='Limit',   
            price=limit_to_sell
        ).result()
        
        # Buy X

        response8 = client.Order.Order_new(
            symbol=X,
            side="Buy",
            orderQty=order_size_buy,
            ordType='Limit',   
            price=limit_to_buy
        ).result()

        # Set a stop for Y
        
        response7 = client.Order.Order_new(
            symbol=Y,
            side="Buy",
            orderQty=order_size_buy,
            ordType='Stop',
            stopPx=stop_price_for_stop_buy,

        ).result()
        
        # Set a stop for X
        
        response7 = client.Order.Order_new(
            symbol=X,
            side="Sell",
            orderQty=order_size_buy,
            ordType='Stop',
            stopPx=stop_price_for_stop_sell,

        ).result()
        
    
        
    
    
        record_row.append('Long the ratio trade USE BULK')
    
def short_the_ratio_trade():
    
    # Short the ratio means to sell X and buy Y
    
        # Set the prices
        
        stop_distance = round((X_ask * stop_percent) * 2.0)/ 2.0
    
        limit_to_buy = round((Y_ask + limit_for_buy) * 2.0)/ 2.0
        limit_to_sell = round((X_bid - limit_for_sell) * 2.0)/ 2.0
        
        stop_price_for_stop_sell = limit_to_buy + stop_distance   
        stop_price_for_stop_buy = limit_to_sell - stop_distance
        
        # Sell X
        
        response8 = client.Order.Order_new(
            symbol=X,
            side="Sell",
            orderQty=order_size_sell,
            ordType='Limit',   
            price=limit_to_sell
        ).result()
    
        # Buy Y
        
        response9 = client.Order.Order_new(
            symbol=Y,
            side="Buy",
            orderQty=order_size_buy,
            ordType='Limit',
            price=limit_to_buy
        ).result()
        
        # Set a stop for X
        
        response7 = client.Order.Order_new(
            symbol=X,
            side="Buy",
            orderQty=order_size_buy,
            ordType='Stop',
            stopPx=stop_price_for_stop_sell,
            
        ).result()
       
        # Set a stop for Y
        
        response10 = client.Order.Order_new(
            symbol=Y,
            side="Sell",
            orderQty=order_size_sell,
            ordType='Stop',
            stopPx=stop_price_for_stop_buy,
            
        ).result()
      

        record_row.append('Short the ratio trade USE BULK')

    
    
# Main bot logic starts here ///

if open_positions == 2:
    try:
        if trade_direction == 'Longing the ratio':       
            if ratio_for_shorting_ratio > close_positions_lower:
                market_close_both_positions()
            else:
                record_row.append('Longing the ratio, waiting')

        elif trade_direction == 'Shorting the ratio':        
            if ratio_for_longing_ratio < close_positions_upper:
                record_row.append('Should be closing cos ratio_for_longing_ratio < close_positions_upper ')
                market_close_both_positions()
            else:
                record_row.append('Shorting the ratio, waiting')   
        
    
    except Exception:
        record_row.append('Have 2 positions, but something is wrong')
        

if open_positions == 0:
    
    # This should nuke any old stops hanging around
    
    client.Order.Order_cancelAll().result()

    if signal == 1:
        long_the_ratio_trade()
    
    if signal == -1:
        short_the_ratio_trade()
    
    
if open_positions == 1:
    record_row.append('I have just one position open so I must have got stopped out. Market closing the other now')
    market_close_both_positions()
    
    
time_of_finish = str(dt.datetime.now())
record_row.append(time_of_finish)



with open(r'pairs_bot_log.csv', 'a') as f:
    writer = csv.writer(f)
    writer.writerow(record_row)
    


