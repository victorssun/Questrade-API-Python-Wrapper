"""
Adapted from account_daily.py -- for questrade.db instead of account_daily.py
"""
# TODO: configure account_index after

import sys
import os
import sqlite3
import datetime
import pickle
import pandas as pd
from shutil import copyfile


# if os.name == 'nt':
#     investment_directory = 'C:/Users/A/Documents/K/Ongoing Projects/Investments/Questrade_Wrapper/'
# elif os.name == 'posix':
#     investment_directory = '/mnt/a_drive/investments/Questrade_Wrapper/'
# sys.path.append('%ssrc/' % investment_directory)
# import accounts
# from accounts import AccountType, AccountQuestradeUtils
import src.accounts as accounts
from src.accounts import AccountType, AccountQuestradeUtils

ACCOUNT = AccountType.FHSA[0]

# set directories for pickle file and token
# direct_data = '%suses/questrade_db/' % investment_directory
# direct_token = '%ssrc/' % investment_directory
direct_data = 'uses/questrade_db/'
direct_token = 'src/'

# generate instance
token = accounts.QuestradeAccounts(direct_token, AccountType.FHSA[1])
token.check_access()
token.get_number()

# grab database
db_name = 'questrade_fhsa.db'
conn = sqlite3.connect('%s%s' % (direct_data, db_name))
cursor = conn.cursor()

# grab today's positions: add new dates, symbols, positions
new_positions = token.account_positions()
today_date = pd.to_datetime(new_positions.iloc[0]['date']).strftime('%Y-%m-%d')

AccountQuestradeUtils.add_unique_dates_to_db(conn, cursor, [today_date])
AccountQuestradeUtils.add_unique_symbs_to_db(conn, cursor, new_positions['symbol'])
AccountQuestradeUtils.add_new_positions_to_db(conn, cursor, ACCOUNT, new_positions)

# grab today's exchange rate
new_ex = token.ex_rate()
AccountQuestradeUtils.add_exchange_rate(conn, cursor, today_date, new_ex)

# run trades, transfers data collection every Friday
if datetime.datetime.today().weekday() == 4:
    # grab all trades since account creation + filter trades from last trade's date entry
    df_trades = token.account_trades()

    cursor.execute("SELECT MAX(dates.date) FROM trades \
    JOIN dates ON trades.date_id = dates.date_id \
    JOIN accounts ON trades.account_id = accounts.account_id \
    WHERE type = '{}'".format(ACCOUNT))
    last_date = cursor.fetchall()[0][0]
    new_trades = df_trades[df_trades['date'] > last_date]

    # grab past week's trades: add new dates, symbols, trades
    new_dates = [pd.to_datetime(date).strftime('%Y-%m-%d') for date in new_trades['date'].unique()]

    AccountQuestradeUtils.add_unique_dates_to_db(conn, cursor, new_dates)
    AccountQuestradeUtils.add_unique_symbs_to_db(conn, cursor, new_trades['symbol'])
    AccountQuestradeUtils.add_new_trades_to_db(conn, cursor, ACCOUNT, new_trades)

    # grab all deposits/withdrawals since account creation + filter transfers from last transfer's date entry
    df_transfers = token.account_transfers()

    cursor.execute("SELECT MAX(dates.date) FROM transfers \
    JOIN dates ON transfers.date_id = dates.date_id \
    JOIN accounts ON transfers.account_id = accounts.account_id \
    WHERE type = '{}'".format(ACCOUNT))
    last_date = cursor.fetchall()[0][0]
    new_transfers = df_transfers[df_transfers['date'] > last_date]

    # grab past week's transfers: add new dates, symbols, transfers
    new_dates = [pd.to_datetime(date).strftime('%Y-%m-%d') for date in new_transfers['date'].unique()]

    AccountQuestradeUtils.add_unique_dates_to_db(conn, cursor, new_dates)
    AccountQuestradeUtils.add_new_transfers_to_db(conn, cursor, ACCOUNT, new_transfers)

    # send success email: with summary information
    receiver = 'victorssun@hotmail.com'
    sender = 'kai.thaoieen@gmail.com'
    pickle_fn = 'uses/account_scripts/for_email.pickle'
    pickle_fn = pickle.load(open(pickle_fn, 'rb'), encoding='latin1')

    subject = "{}: {} - success".format(ACCOUNT, str(datetime.date.today()))
    message = "added {} trades, {} transfers \n".format(len(new_trades), len(new_transfers))

    cursor.execute("SELECT dates.date, sum(value) FROM positions JOIN dates ON positions.date_id = dates.date_id GROUP BY positions.date_id ORDER BY positions.date_id DESC LIMIT 7;")
    data = cursor.fetchall()

    for d in data:
        message += "{}: {}\n".format(d[0], round(d[1], 2))
    token.send_email(sender, receiver, subject, message, pickle_fn)

    # save another backup copy
    copyfile('{}{}'.format(direct_data, db_name), '{}{}{}'.format(direct_data, 'backups/'+today_date+'_', db_name))
