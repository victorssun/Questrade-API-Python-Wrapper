# -*- coding: utf-8 -*-
"""
Created on Wed Jun 24 00:21:23 2020

@author: A

convert .pickle to SQLite database
"""

import pickle, datetime, sqlite3, os, sys
import pandas as pd

if os.name == 'nt':
    investment_directory = 'C:/Users/A/Documents/K/Ongoing Projects/Investments/Questrade_Wrapper/'
    direct_data = 'C:/Users/A/Documents/K/Ongoing Projects/Investments/Questrade_Wrapper/uses/'
elif os.name == 'posix':
    investment_directory = '/mnt/a_drive/investments/Questrade_Wrapper/'
    direct_data = '/mnt/a_drive/investments/Questrade_Wrapper/uses/'
sys.path.append('%ssrc/' % investment_directory)
from accounts import AccountsUtils
# from src.accounts import AccountsUtils


# set db filename
db_name = 'account_data.db'

# grab .pickle files
positions_daily, balances_daily, df_trades, df_returns = pickle.load(open('%saccount_data.pickle' % direct_data, 'rb'), encoding='latin1')

# format .pkl data for sql db, if db already exists, ensure do not add duplicate data
if os.path.isfile('%s%s' % (direct_data, db_name)):
    conn = sqlite3.connect('%s%s' % (direct_data, db_name))
    cursor = conn.cursor()

    list_balances_daily = AccountsUtils.format_balances_daily(balances_daily, AccountsUtils.maxDate(cursor, 'SELECT date FROM balances_daily'))
    list_positions_daily = AccountsUtils.format_positions_daily(positions_daily, AccountsUtils.maxDate(cursor, 'SELECT date FROM positions_daily'))
    list_df_trades = AccountsUtils.format_df_trades(df_trades, AccountsUtils.maxDate(cursor, 'SELECT date FROM df_trades'))
    list_df_returns = AccountsUtils.format_df_returns(df_returns, AccountsUtils.maxDate(cursor, 'SELECT date FROM df_returns'))

else:
    list_balances_daily = AccountsUtils.format_balances_daily(balances_daily)
    list_positions_daily = AccountsUtils.format_positions_daily(positions_daily)
    list_df_trades = AccountsUtils.format_df_trades(df_trades)
    list_df_returns = AccountsUtils.format_df_returns(df_returns)
print('%d balances, %d positions, %d trades, %d returns to be added.' %(len(list_balances_daily), len(list_positions_daily), len(list_df_trades), len(list_df_returns)))

# create new db if doesn't exist
if not os.path.isfile('%s%s' %(direct_data, db_name)):
    print('creating new db.')
    conn = sqlite3.connect('%s%s' % (direct_data, db_name))
    cursor = conn.cursor()

    cursor.execute('CREATE TABLE "balances_daily" ("date" DATE NOT NULL, "exchangeRate" NUMERIC, "cash" NUMERIC, "marketValue" NUMERIC, "totalEquity" NUMERIC NOT NULL)')
    cursor.execute('CREATE TABLE "positions_daily" ("date" DATE NOT NULL, "symbol" TEXT NOT NULL, "value" NUMERIC NOT NULL)')
    cursor.execute('CREATE TABLE "df_trades" ("date" DATE NOT NULL, "symbol" TEXT NOT NULL, "currency" TEXT NOT NULL, "side" TEXT NOT NULL, "quantity" NUMERICAL NOT NULL, "totalCost" NUMERIC NOT NULL)')
    cursor.execute('CREATE TABLE "df_returns" ("date" DATE NOT NULL, "symbol" TEXT NOT NULL, "quantity" NUMERIC, "netProfit" NUMERIC NOT NULL)')

# set and execute sql statements for insertion
sql_balances_daily = 'INSERT INTO balances_daily (date, exchangeRate, cash, marketValue, totalEquity) VALUES (?, ?, ?, ?, ?)'
cursor.executemany(sql_balances_daily, list_balances_daily)

sql_positions_daily = 'INSERT INTO positions_daily (date, symbol, value) VALUES (?, ?, ?)'
cursor.executemany(sql_positions_daily, list_positions_daily)

sql_df_trades = 'INSERT INTO df_trades (date, symbol, currency, side, quantity, totalCost) VALUES (?, ?, ?, ?, ?, ?)'
cursor.executemany(sql_df_trades, list_df_trades)

sql_df_returns = 'INSERT INTO df_returns (date, symbol, quantity, netProfit) VALUES (?, ?, ?, ?)'
cursor.executemany(sql_df_returns, list_df_returns)

# read rows
#cursor.execute('SELECT * FROM positions_daily')

# delete all rows from both tables
#cursor.execute('DELETE from positions_daily')

# output = cursor.fetchall()
#print(output)

conn.commit()
conn.close()
