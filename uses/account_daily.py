# -*- coding: utf-8 -*-
"""
Created on Thu Apr 26 00:33:45 2018

@author: A
Grab daily positions and balances data (not necessary as balances derived from positions) daily
Save to pickle file: positions_daily, balances_daily

Grabbing trades and returns not really necessary because we can grab them whenever we want and calculate them based on any day if we filter
Save to pickle file: df_trades, df_returns
"""

import sys
import os
import pickle, datetime, pandas as pd
import numpy as np
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

if os.name == 'nt':
    investment_directory = 'C:/Users/A/Documents/K/Ongoing Projects/Investments/Questrade_Wrapper/'
elif os.name == 'posix':
    investment_directory = '/mnt/a_drive/investments/Questrade_Wrapper/'
sys.path.append('%ssrc/' % investment_directory)
import accounts
# import src.accounts as accounts


# set directories for pickle file and token
direct_data = '%suses/' % investment_directory
direct_token = '%ssrc/' % investment_directory

# generate instance
token = accounts.QuestradeAccounts(direct_token)
token.check_access()

# set email config
receiver = 'victorssun@hotmail.com'
sender = 'kai.thaoieen@gmail.com'
pickle_fn = '{}for_email.pickle'.format(direct_data)
pickle_fn = pickle.load(open(pickle_fn, 'rb'), encoding='latin1')

# save daily data to pickle if running on linux, email is sent every friday
if os.name == 'posix':
    positions_daily, balances_daily, df_trades, df_returns = pickle.load(open('%saccount_data.pickle' % direct_data, 'rb'), encoding='latin1')

    # grab today's positions and append to old data
    new_positions = token.account_positions()
    positions_daily = token.append_to_df(positions_daily, new_positions)

    # grab today's balances and append to old data
    new_balances = token.account_balances()
    balances_daily = token.append_to_df(balances_daily, new_balances)

    # run trades and net profit data collection every Friday
    if datetime.datetime.today().weekday() == 4:
        # grab all trades since account creation
        df_trades = token.account_trades()

        # calculate today's P/L returns from trades, if want to calculate P/L from different day, filter df_trades
        df_returns = token.account_returns(df_trades, endDay='')  # summarize trades into net profits

        # send success email
        subject = str(datetime.date.today()) + "'s weekly success"
        message = str(balances_daily.tail(7))
        token.send_email(sender, receiver, subject, message, pickle_fn)

    # pickle data
    token.save([positions_daily, balances_daily, df_trades, df_returns], filename='%sdaily pickles/account_data_%s.pickle' %(direct_data, datetime.date.today()))
    token.save([positions_daily, balances_daily, df_trades, df_returns], '%saccount_data.pickle' %direct_data)
    print('save data')

else:
    # positions and balances
    positions_daily, balances_daily, df_trades, df_returns = pickle.load(open('%saccount_data.pickle' %direct_data, 'rb'), encoding='latin1') # load  data

    new_positions = token.account_positions()
    positions_daily2 = token.append_to_df(positions_daily, new_positions)

    new_balances = token.account_balances()
    balances_daily2 = token.append_to_df(balances_daily, new_balances)

    print(balances_daily2.tail(7))  # print last 7 days

    # trades and returns
    df_trades = token.account_trades()
    df_returns = token.account_returns(df_trades, endDay='')

    print('windows ran. data not saved.')
