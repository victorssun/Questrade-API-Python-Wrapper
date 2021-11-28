# -*- coding: utf-8 -*-
"""
Created on Wed Jun 24 00:21:23 2020

@author: A

convert .pickle to SQLite database
"""

import pickle
import sqlite3
import os
import sys

if os.name == 'nt':
    investment_directory = 'C:/Users/A/Documents/K/Ongoing Projects/Investments/Questrade_Wrapper/'
    direct_data = 'C:/Users/A/Documents/K/Ongoing Projects/Investments/Questrade_Wrapper/uses/account_scripts/'
elif os.name == 'posix':
    investment_directory = '/mnt/a_drive/investments/Questrade_Wrapper/'
    direct_data = '/mnt/a_drive/investments/Questrade_Wrapper/uses/account_scripts/'
sys.path.append('%ssrc/' % investment_directory)
from accounts import AccountsUtils
# from src.accounts import AccountsUtils


# set db filename
db_name = 'account_data.db'

# grab .pickle files
df_positions, df_balances, df_trades, df_returns, df_transfers = pickle.load(open('%saccount_data.pickle' % direct_data, 'rb'), encoding='latin1')

# create db if doesn't exist, format .pkl data for sql db
if os.path.isfile('%s%s' % (direct_data, db_name)):
    # connect to db
    conn = sqlite3.connect('%s%s' % (direct_data, db_name))
    cursor = conn.cursor()
    
    # ensure do not add duplicate data
    list_df_positions = AccountsUtils.format_df_positions(df_positions, AccountsUtils.maxDate(cursor, 'SELECT date FROM df_positions'))
    list_df_balances = AccountsUtils.format_df_balances(df_balances, AccountsUtils.maxDate(cursor, 'SELECT date FROM df_balances'))
    list_df_trades = AccountsUtils.format_df_trades(df_trades, AccountsUtils.maxDate(cursor, 'SELECT date FROM df_trades'))
    list_df_returns = AccountsUtils.format_df_returns(df_returns, AccountsUtils.maxDate(cursor, 'SELECT date FROM df_returns'))
    list_df_transfers = AccountsUtils.format_df_transfers(df_transfers, AccountsUtils.maxDate(cursor, 'SELECT date FROM df_transfers'))

else:
    print('creating new db.')
    conn = sqlite3.connect('%s%s' % (direct_data, db_name))
    cursor = conn.cursor()
    
    cursor.execute('CREATE TABLE "df_positions" ("date" DATE NOT NULL, "symbol" TEXT NOT NULL, "value" NUMERIC NOT NULL)')
    cursor.execute('CREATE TABLE "df_balances" ("date" DATE NOT NULL, "exchangeRate" NUMERIC, "cumulative" NUMERIC, "cash" NUMERIC, "marketValue" NUMERIC, "totalEquity" NUMERIC NOT NULL)')
    cursor.execute('CREATE TABLE "df_trades" ("date" DATE NOT NULL, "symbol" TEXT NOT NULL, "quantity" NUMERICAL NOT NULL, "totalCost" NUMERIC NOT NULL)')
    cursor.execute('CREATE TABLE "df_returns" ("date" DATE NOT NULL, "symbol" TEXT NOT NULL, "quantity" NUMERIC, "netProfit" NUMERIC NOT NULL)')
    cursor.execute('CREATE TABLE "df_transfers" ("date" DATE NOT NULL, "added" NUMERIC, "cumulative" NUMERIC NOT NULL)')

    list_df_positions = AccountsUtils.format_df_positions(df_positions)
    list_df_balances = AccountsUtils.format_df_balances(df_balances)
    list_df_trades = AccountsUtils.format_df_trades(df_trades)
    list_df_returns = AccountsUtils.format_df_returns(df_returns)
    list_df_transfers = AccountsUtils.format_df_transfers(df_transfers)

print('%d positions, %d balances, %d trades, %d returns, %d transfers to be added.' %
      (len(list_df_positions), len(list_df_balances), len(list_df_trades), len(list_df_returns), len(list_df_transfers)))

# set and execute sql statements for insertion
sql_df_positions = 'INSERT INTO df_positions (date, symbol, value) VALUES (?, ?, ?)'
cursor.executemany(sql_df_positions, list_df_positions)

sql_df_balances = 'INSERT INTO df_balances (date, exchangeRate, cumulative, cash, marketValue, totalEquity) VALUES (?, ?, ?, ?, ?, ?)'
cursor.executemany(sql_df_balances, list_df_balances)

sql_df_trades = 'INSERT INTO df_trades (date, symbol, quantity, totalCost) VALUES (?, ?, ?, ?)'
cursor.executemany(sql_df_trades, list_df_trades)

sql_df_returns = 'INSERT INTO df_returns (date, symbol, quantity, netProfit) VALUES (?, ?, ?, ?)'
cursor.executemany(sql_df_returns, list_df_returns)

sql_df_transfers = 'INSERT INTO df_transfers (date, added, cumulative) VALUES (?, ?, ?)'
cursor.executemany(sql_df_transfers, list_df_transfers)

# read rows
#cursor.execute('SELECT * FROM df_positions')
# output = cursor.fetchall()
#print(output)

conn.commit()
conn.close()
