# -*- coding: utf-8 -*-
"""
Created on Thu Apr 26 00:33:45 2018

@author: A
- Grab daily positions and balances data (not necessary as balances derived from positions) 
- Grab weekly trades and returns (not necessary because we can grab them whenever)
Save to pickle file: df_positions, df_balances, df_trades, df_returns, df_transfers
"""

import sys
import os
import pickle
import datetime

if os.name == 'nt':
    investment_directory = 'C:/Users/A/Documents/K/Ongoing Projects/Investments/Questrade_Wrapper/'
elif os.name == 'posix':
    investment_directory = '/mnt/a_drive/investments/Questrade_Wrapper/'
sys.path.append('%ssrc/' % investment_directory)
import accounts
# import src.accounts as accounts


# set directories for pickle file and token
direct_data = '%suses/account_scripts/' % investment_directory
direct_token = '%ssrc/' % investment_directory

# generate instance
token = accounts.QuestradeAccounts(direct_token)
token.check_access()

# set email config
receiver = 'victorssun@hotmail.com'
sender = 'kai.thaoieen@gmail.com'
pickle_fn = '{}for_email.pickle'.format(direct_data)
pickle_fn = pickle.load(open(pickle_fn, 'rb'), encoding='latin1')


# generate data
df_positions, df_balances, df_trades, df_returns, df_transfers = pickle.load(open('%saccount_data.pickle' % direct_data, 'rb'), encoding='latin1')

# grab today's positions and append to old data
new_positions = token.account_positions()
df_positions = token.append_to_df(df_positions, new_positions)

# grab today's balances and append to old data
new_balances = token.account_balances()
df_balances = token.append_to_df(df_balances, new_balances)


# save daily data to pickle if running on linux, email is sent every friday
if os.name == 'posix':
    # run trades and net profit data collection every Friday
    if datetime.datetime.today().weekday() == 4:
        # grab all trades since account creation
        df_trades = token.account_trades()

        # calculate today's P/L returns from trades, if want to calculate P/L from different day, filter df_trades
        df_returns = token.account_returns(df_trades, endDay='')  # summarize trades into net profits

        # grab all deposits/withdrawals since account creation
        df_transfers = token.account_transfers()

        # send success email
        subject = str(datetime.date.today()) + "'s weekly success"
        message = str(df_balances.tail(7))
        token.send_email(sender, receiver, subject, message, pickle_fn)

        # pickle back up data
        token.save([df_positions, df_balances, df_trades, df_returns, df_transfers], filename='%sdaily pickles/account_data_%s.pickle' % (direct_data, datetime.date.today()))

    # pickle data
    token.save([df_positions, df_balances, df_trades, df_returns, df_transfers], '%saccount_data.pickle' % direct_data)
    print('save data')

else:
    # positions and balances
    print(df_balances.tail(7))  # print last 7 days

    # trades and returns and transfers
#    df_trades = token.account_trades()
    
#    df_returns = token.account_returns(df_trades, endDay='')

    # df_transfers = token.account_transfers()

    print('windows ran. data not saved.')
