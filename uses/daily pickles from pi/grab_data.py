# -*- coding: utf-8 -*-
"""
Created on Sun Aug 22 00:00:52 2021

@author: A
"""
import pickle, datetime, sqlite3, os, sys
import pandas as pd

if os.name == 'nt':
    investment_directory = 'C:/Users/A/Documents/K/Ongoing Projects/Investments/Questrade_Wrapper'
#    direct_data = 'C:/Users/A/Documents/K/Ongoing Projects/Investments/Questrade_Wrapper/uses/'
    direct_data = 'C:/Users/A/Documents/K/Ongoing Projects/Investments/Questrade_Wrapper/uses/daily pickles from pi/daily pickles/'
sys.path.append('%ssrc/' % investment_directory)
from accounts import AccountsUtils
# from src.accounts import AccountsUtils


# look at current data
positions_sql, balances_sql, trades_sql, returns_sql = AccountsUtils.sql_to_df(investment_directory + 'uses/account_data.db')
positions, balances, trades, returns = pickle.load(open('%suses/account_data.pickle' % investment_directory, 'rb'))

""" create returns df with complete data from old data """
#positions_daily, balances_daily = pickle.load(open('%saccount_daily_2020-09-22.pickle' % direct_data, 'rb'), encoding='latin1')

df_trades, df_returns = pickle.load(open('%saccount_profits_2021-08-20.pickle' % direct_data, 'rb'), encoding='latin1')

# old is probably python2: up to 2019-06-28
df_trades, df_returns = pickle.load(open('%sold/account_profits_2018-05-16.pickle' % direct_data, 'rb'))


datetime.datetime.today()
returns['date'].iloc[-1]
returns['date'].iloc[-1]
 