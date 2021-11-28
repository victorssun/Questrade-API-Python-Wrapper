# -*- coding: utf-8 -*-
"""
Created on Thu Apr 26 00:33:45 2018

@author: A

Additional methods to collect account data into pickle
"""

import datetime
import os
import pickle
import random
import smtplib
import sqlite3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import numpy as np
import pandas as pd

import questrade


class QuestradeAccounts(questrade.QuestradeToken):
    def __init__(self, token_directory, account_index=0):
        super().__init__(token_directory, account_index)

    def account_positions(self):
        """
        Grab today's positions data and append to existing data

        :return: df_positions_temp
        """

        # grab data required for analysis and collection
        ex = self.ex_rate()  # CAD/USD exchange rate
        today_date = pd.to_datetime(datetime.date.today())

        # grab today's/current positions: their symbols, current value, and current date and append to lists
        symbols = []
        currentValues = []
        dates = []
        for i in range(len(self.positions())):
            # for each current position, check if currentMarketValue is positive -- if shares of position is not sold
            if self.positions()[i]['currentMarketValue']:
                if self.positions()[i]['currentMarketValue'] >= 0:
                    # append date, symbol, and its current value to respective lists
                    dates.append(today_date)
                    symbol2 = str(self.positions()[i]['symbol'])
                    symbols.append(symbol2)
    
                    # currentMarketValue is in the stock's currency, therefore must convert USD stock value to CAD
                    if symbol2.find('.TO') != -1:
                        # symbols that contain .TO must not be -1/greater than -1
                        currentValues.append(self.positions()[i]['currentMarketValue'])
                    else:
                        currentValues.append(self.positions()[i]['currentMarketValue'] * ex)
                else:
                    print('%s skipped/sold.' % self.positions()[i]['symbol'])
            else:
                    print('%s skipped/sold.' % self.positions()[i]['symbol'])

        # grab current combined USD and CAD cash, evaluated in CAD
        dates.append(today_date)
        cash = self.balances()['cash']
        symbols.append('cash')
        currentValues.append(cash)

        # ensure format matches current columns
        df_positions_temp = pd.DataFrame({'date': dates, 'symbol': symbols, 'value': currentValues})

        return df_positions_temp

    def account_balances(self):
        """
        Grab today's balances data. Balances can be derived from df_positions. Or grab directly from QT API balances.

        :return: df_balances
        """
        # grab data required for analysis and collection
        ex = self.ex_rate()  # CAD/USD exchange rate
        today_date = pd.to_datetime(datetime.date.today())

        # grab today's/current balance data: date, exchange rate, cash, current stock value, total equity
        df_balances_temp = self.balances()
        df_balances_temp = [df_balances_temp.get(key) for key in ['cash', 'marketValue', 'totalEquity']]
        df_balances_temp.append(ex)
        df_balances_temp.append(today_date)
        
        # grab cumulative deposits/withdrawals
        df_transfers = self.account_transfers()        
        df_balances_temp.append(df_transfers['cumulative'].iloc[-1])
        
        df_balances_temp = pd.DataFrame(df_balances_temp).T
        df_balances_temp.columns = ['cash', 'marketValue', 'totalEquity', 'exchangeRate', 'date', 'cumulative']  # must match current data to be append

        return df_balances_temp

    def account_trades(self, start_day='', end_day=''):
        """
        Grab all account trades since beginning of account creation
        Data includes: trades: date, buy/sell, amount, value of trade in CAD
        Assumes and convers HMMJ.TO to HMLSF and DLR.TO to DLR.U.TO, but not vice-versa
        # unable to determine amount of fees used to pay all trades since activities don't provide fee info like executions

        :param start_day: start day to grab trades
        :param end_day: end day to grab trades
        :return: df_trades
        """
        # all activities since creation must be grabbed because we need all trades to take into account of share conversions
        list_daterange = self.daterange_all(start_day, end_day)
        list_activities = []
        print('grabbing activities data...')
        for i in range(len(list_daterange)):
            datestring = list_daterange[i][0] + ' to ' + list_daterange[i][1]
            try:
                list_activities.extend(self.activities(datestring))
                # print('%s success' % datestring)
            except:
                print('%s fail' % datestring)
                pass

        # categorize into trades, dividends (to be added converted to trades), and other (Norbert's Gamble converted)
        # ignore deposits, fx conversions, fees and rebates, and withdrawals
        other = []
        dividends = []
        trades = []
        for i in range(len(list_activities)):
            if list_activities[i]['type'] == 'Other':
                other.append(list_activities[i])
            elif list_activities[i]['type'] == 'Dividends':
                dividends.append(list_activities[i])
            elif list_activities[i]['type'] == 'Trades':
                trades.append(list_activities[i])

        # create trade dataframe: append trade activities to this df
        df_trades = pd.DataFrame()
        for each in trades:
            df_trades = pd.concat([df_trades, pd.DataFrame([each['symbol'], each['action'], each['netAmount'], each['quantity'], each['currency'], each['tradeDate']])], axis=1)
        df_trades = df_trades.T
        df_trades.columns = ['symbol', 'side', 'totalCost', 'quantity', 'currency', 'date']

        # append dividend activities to trade dataframe, but quantity is set to 0, signifying dividend and not a real trade
        df_dividends = pd.DataFrame()
        for each in dividends:
            df_dividends = pd.concat([df_dividends, pd.DataFrame([each['symbol'], 'Sell', each['netAmount'], 0, each['currency'], each['tradeDate']])], axis=1)
        df_dividends = df_dividends.T
        df_dividends.columns = ['symbol', 'side', 'totalCost', 'quantity', 'currency', 'date']

        df_trades = pd.concat([df_trades, df_dividends])

        # add other activities to trade df (parse out each HMMJ/HMLSF converison to appropriate format)

        # convert HMLSF trade to HMMJ (must take into account currency, exchange rate, and quantity)
        df_hmlsf = df_trades[df_trades['symbol'] == 'HMLSF']

        # count the amount of shares that HMMJ.TO/HMLSF were converted
        counter_usd = 0
        counter_cad = 0
        for each in other:
            if each['currency'] == 'USD' and each['symbol'] == 'HMLSF':
                counter_usd += each['quantity']
            elif each['currency'] == 'CAD' and each['symbol'] == 'HMMJ.TO':
                counter_cad += each['quantity']

        # ensure hmmj and hmlsf quantities match and ensure all shares of HMMJ converted to HMLSF are sold
        # this assumes no current holdings of hmlsf
        if (counter_usd + counter_cad == 0) and (counter_cad == df_hmlsf['quantity'].sum()):
            df_hmlsf['symbol'] = 'HMMJ.TO'
            df_hmlsf['currency'] = 'CAD'
        #    df_hmlsf['totalCost'] = df_hmlsf['totalCost'] * token.ex_rate()
            df_hmlsf['totalCost'] = df_hmlsf['totalCost'] * 1.25  # hardcode exchange rate to 1.23 instead of current (~1.33 as of 20200914)
            print('HMMJ/HMLSF match.. added')
        else:
            # if does not match, that means probably means HMMJ.TO have been converted to HMLSF, but HMLSF have not been sold
            # this will cause profit/loss of HMMJ to be too low while HMLSF will be too high
            if abs(counter_cad) < abs(df_hmlsf['quantity'].sum()):
                print('ERROR: DLR/DLR.U check does not match.. no conversion occured.')
            else:
                # assume more CAD shares than USD counterpart
                df_hmlsf['symbol'] = 'HMMJ.TO'
                df_hmlsf['currency'] = 'CAD'
                df_hmlsf['totalCost'] = df_hmlsf['totalCost'] * 1.25

                print('DLR/DLR.U check does not match.. part conversion occured.')
            print('HMMJ/HMLSF check does not match.. not added.')

        # remove HMLSF trades and replace with converted HMMJ.TO
        df_trades = df_trades[df_trades['symbol'] != 'HMLSF']
        df_trades = pd.concat([df_trades, df_hmlsf])

        # convert DLR.U.TO to DLR
        df_dlr = df_trades[df_trades['symbol'] == 'DLR.U.TO']

        # count the amount of shares that HMMJ.TO/HMLSF were converted
        counter_usd = 0
        counter_cad = 0
        for each in other:
            if each['currency'] == 'USD' and each['symbol'] == 'DLR.U.TO':
                counter_usd += each['quantity']
            elif each['currency'] == 'CAD' and each['symbol'] == 'DLR.TO':
                counter_cad += each['quantity']

        # ensure DLR and DLR.U quantities match and ensure all shares of DLR converted to DLR.U are sold
        # this assumes no current holdings of DLR.U
        if (counter_usd + counter_cad == 0) and (counter_cad == df_dlr['quantity'].sum()):
            df_dlr['symbol'] = 'DLR.TO'
            df_dlr['currency'] = 'CAD'
            df_dlr['totalCost'] = df_dlr['totalCost'] * 1.25
            print('DLR/DLR.U match.. added')
        else:
            # assume counters match but stock was not sold after being converted, therefore must do it manually
            if abs(counter_cad) < abs(df_dlr['quantity'].sum()):
                print('ERROR: DLR/DLR.U check does not match.. no conversion occured.')
            else:
                # assume more CAD shares than USD counterpart
                df_dlr['symbol'] = 'DLR.TO'
                df_dlr['currency'] = 'CAD'
                df_dlr['totalCost'] = df_dlr['totalCost'] * 1.25

                print('DLR/DLR.U check does not match.. part conversion occured.')

        # remove DLR.U trades and replace with converted DLR.TO
        df_trades = df_trades[df_trades['symbol'] != 'DLR.U.TO']
        df_trades = pd.concat([df_trades, df_dlr])

        # convert all USD trade's totalCost to CAD totalCost
        df_trades = df_trades.reset_index(drop=True)
        for i in range(len(df_trades)):
            if df_trades.iloc[i]['currency'] == 'USD':
                df_trades.iloc[i]['totalCost'] = df_trades.iloc[i]['totalCost'] * self.ex_rate()
                df_trades.iloc[i]['currency'] = 'CAD'

        # convert date isoformat to datetime
        df_trades['date'] = pd.to_datetime(df_trades['date'].str.split('T').str[0])

        # remove side and currency cols
        del df_trades['side']
        del df_trades['currency']

        return df_trades

    def account_returns(self, df_trades, endDay=''):
        """ Calculate returns (profit/loss) given dataframe of all trades

        :param token: QuestradeToken instance
        :param df_trades: dataframe of all trades
        :param endDay: Calculate returns on endDay date
        :return: df_returns
        """
        # optional: calculate total returns P/L on a given day
        if endDay != '':
            endDay_temp = endDay.split('-')
            endDay_temp = datetime.datetime(int(endDay_temp[0]), int(endDay_temp[1]), int(endDay_temp[2]), 0, 0)
            df_trades = df_trades[df_trades['date'] < endDay_temp]

        # calculate P/L for each unique symbol: create dataframe with data including -- symbol, P/L, quantity of stock, date
        recent_date = df_trades['date'].max() # TODO: fix
        symbs = pd.unique(df_trades['symbol'])
        df_returns = pd.DataFrame()
        for symb in symbs:
            df_trades_unique = df_trades[df_trades['symbol'] == symb]
            quant = df_trades_unique['quantity'].sum()

            # if quantity is zero, then no longer holding this stock, therefore just sum total cost for all trades to get P/L
            if quant == 0:
                df_returns = pd.concat([df_returns, pd.DataFrame([symb, df_trades_unique['totalCost'].sum(), np.NaN, recent_date])], axis=1)

            # if still holding the stock, sum all trades + current quantity * price of stock based on given day
            elif quant > 0:
                symb_info = self.symbs(symb)[0]
                if symb_info['currency'] == 'USD':
                    # ex = token.ex_rate()
                    ex = 1.25
                elif symb_info['currency'] == 'CAD':
                    ex = 1

                if endDay == '':
                    close_price = symb_info['prevDayClosePrice'] * ex
                elif endDay != '':
                    close_price = self.candles(symb, datestring='creation to ' + endDay)[-1]['close'] * ex

                total = quant * close_price + df_trades_unique['totalCost'].sum()
                df_returns = pd.concat([df_returns, pd.DataFrame([symb, total, quant, recent_date])], axis=1)

            # if have negative stock, assume share got split, therefore, amount of shares sold will be more than bought (quant will be <0)
            # assume all shares of split stock are sold, therefore just do a sum over all trades
            elif quant < 0:
                print('assume this stock has split: add %s to returns' % symb)
                df_returns = pd.concat([df_returns, pd.DataFrame([symb, df_trades_unique['totalCost'].sum(), np.NaN, recent_date])], axis=1)

        df_returns = df_returns.T
        df_returns.columns = ['symbol', 'netProfit', 'quantity', 'date']
        return df_returns

    def account_transfers(self):
        """ Grab all deposits and withdraw activities

        :return: df_transfers
        """
        # all activities grabbed
        list_daterange = self.daterange_all("", "")
        list_activities = []
        print('grabbing activities data...')
        for i in range(len(list_daterange)):
            datestring = list_daterange[i][0] + ' to ' + list_daterange[i][1]
            try:
                list_activities.extend(self.activities(datestring))
            except:
                print('%s fail' % datestring)
                pass

        # only get withdrawals and deposits
        transfers = []
        for i in range(len(list_activities)):
            if list_activities[i]['type'] == 'Withdrawals' or list_activities[i]['type'] == 'Deposits':
                transfers.append(list_activities[i])

        df_transfers = pd.DataFrame()
        for activity in transfers:
            df_transfers = pd.concat([df_transfers, pd.DataFrame(
                [activity['netAmount'], activity['tradeDate']])], axis=1)
        df_transfers = df_transfers.T
        df_transfers.columns = ['added', 'date']

        df_transfers = pd.concat([df_transfers, df_transfers['added'].cumsum()], axis=1)
        df_transfers.columns = ['added', 'date', 'cumulative']

        df_transfers['date'] = pd.to_datetime(df_transfers['date'].str.split('T').str[0])
        df_transfers = df_transfers.reset_index(drop=True)

        return df_transfers

    @staticmethod
    def save(data, filename, autosave=True):
        """
        Save data to pickled file

        :param data: data to be saved in pickle file
        :param filename: filename of pickle file
        :param autosave: If true, no confirmation input required to pickle data
        :return:
        """
        if autosave:
            pickle.dump(data, open(filename, 'wb'))
            print('%s. saved' % filename)
        elif input('save %s? (y/n): ' % filename) == 'y':
            pickle.dump(data, open(filename, 'wb'))
            print('%s. saved' % filename)
        else:
            print('not saved')

    @staticmethod
    def append_to_df(current_df, new_data):
        """ Append new df formatted data to current df. Must ensure both df have matching format

        :param current_df: old data
        :param new_data: new data
        :return: current_df
        """
        current_df = current_df.append(new_data, sort=True)
        current_df = current_df.reset_index(drop=True)

        return current_df

    @staticmethod
    def daterange_all(startDay_string='', presentDay_string='', delta=21):
        """
        Create list of startDay, endDay. Used to run Questrade.activates
        format: 'yyyy-mm-dd'

        :param startDay_string: start day of date range
        :param presentDay_string: end day of date range
        :param delta: days to skip
        :return: list of date ranges of start and end, spaced by delta
        """
        list_daterange = []

        # convert startDay_string to datetime
        if startDay_string == '':
            startDay = datetime.datetime(2018, 1, 2, 0, 0)
        else:
            startDay_string= startDay_string.split('-')
            startDay = datetime.datetime(int(startDay_string[0]), int(startDay_string[1]), int(startDay_string[2]), 0, 0)

        # convert presentDay_string to datetime
        if presentDay_string == '':
            tdate = datetime.datetime.now()
            presentDay = datetime.datetime(tdate.year, tdate.month, tdate.day, 0, 0)
        else:
            presentDay_string = presentDay_string.split('-')
            presentDay = datetime.datetime(int(presentDay_string[0]), int(presentDay_string[1]), int(presentDay_string[2]), 0, 0)

        # generate list of dateranges with start and end day spaced by given delta
        endDay = startDay + datetime.timedelta(days=delta)
        while endDay <= presentDay:
            endDay = startDay + datetime.timedelta(days=delta)
            startDay_temp = str(startDay).split()[0]
            endDay_temp = str(endDay).split()[0]
            list_daterange.append([startDay_temp, endDay_temp])
            startDay = endDay + datetime.timedelta(days=1)

        return list_daterange

    @staticmethod
    def send_email(sender, receiver, subject, message, pw):
        """ Send email with summary of data collection

        :param sender: sender's email
        :param receiver: receiver's email
        :param subject: email subject
        :param message: email message
        :param pw: pw of sender
        :return: None
        """

        msg = MIMEMultipart()
        msg['From'] = sender
        msg['To'] = receiver
        msg['Subject'] = subject

        msg.attach(MIMEText(message, 'plain'))
        text = msg.as_string()

        smtpObj = smtplib.SMTP(host='smtp.gmail.com', port=587)
        smtpObj.starttls()
        # email_info = pickle.load(open(pickle_filename, 'rb'), encoding='latin1')
        email_info = pw
        smtpObj.login('kai.thaoieen@gmail.com', email_info)
        smtpObj.sendmail(sender, receiver, text)
        smtpObj.quit()

        print('email sent')


class AccountsUtils:
    """ Utility functions for QuestradeAccounts: mostly just DF to SQL format conversions.
    TODO: Comparison of Timestamp with datetime.date is deprecated in order to match the standard library behavior
    """

    @staticmethod
    def randomize_dataframe(df):
        """ Scrubbing and randomizing nnumber data for public showcasing of methods

        :param df: dataframe
        :return: dataframe
        """
        df = df.copy()
        for col in df.columns:
            if col in ['date', 'quantity']:
                # skip dates
                continue

            if type(df[col][0]) == str:
                # skip cells that are just strings
                continue

            max_val = np.nanmax(df[col] / 100.0)
            for i in range(len(df[col])):
                # all number values are divided by 100, then scaled with a random 0-1 number
                # + a percent based on index/date with max baseline of 10%
                df[col][i] = df[col][i] * random.random() / 100.0 + (i / len(df[col]) * 0.20 * max_val)

        return df

    @staticmethod
    def sql_to_df(db_filename):
        """ Convert SQLite db to all four dataframes: positions, balances, trades, returns, transfers. For visualization.
        Note: datetime/pandas timestamp is string, float/int is numpy float/int... therefore do not save into pickle

        :param db_filename: filepath and filename of sqlite db
        :return: df_positions, df_balances, df_trades, df_returns, df_transfers
        """

        conn = sqlite3.connect(db_filename)
        cursor = conn.cursor()

        def get_table_headers(table_name):
            cursor.execute('PRAGMA table_info({})'.format(table_name))
            headers = [col[1] for col in cursor.fetchall()]

            return headers

        cursor.execute('SELECT * FROM df_balances')
        df_balances = pd.DataFrame(cursor.fetchall())
        df_balances.columns = get_table_headers('df_balances')

        cursor.execute('SELECT * FROM df_positions')
        df_positions = pd.DataFrame(cursor.fetchall())
        df_positions.columns = get_table_headers('df_positions')

        cursor.execute('SELECT * FROM df_trades')
        df_trades = pd.DataFrame(cursor.fetchall())
        df_trades.columns = get_table_headers('df_trades')

        cursor.execute('SELECT * FROM df_returns')
        df_returns = pd.DataFrame(cursor.fetchall())
        df_returns.columns = get_table_headers('df_returns')

        cursor.execute('SELECT * FROM df_transfers')
        df_transfers = pd.DataFrame(cursor.fetchall())
        df_transfers.columns = get_table_headers('df_transfers')

        conn.commit()
        conn.close()

        return df_positions, df_balances, df_trades, df_returns, df_transfers

    @staticmethod
    def maxDate(cursor, sql_statement):
        """ Find max date from given sql db

        :param cursor: sql object
        :param sql_statement: sql command
        :return: datetime
        """
        cursor.execute(sql_statement)
        output = pd.DataFrame(cursor.fetchall())
        max_date = datetime.datetime.strptime(output[0].max(), '%Y-%m-%d')
        max_date = max_date.date()
        return max_date

    @staticmethod
    def format_df_balances(df_balances, max_date=datetime.date(2000, 1, 1)):
        """ Convert df_balances df to formatted list to be fed into sql db

        :param df_balances: dataframe
        :param max_date: restrict dataframe based on max date
        :return: list
        """
        list_df_balances = []
        for i in range(len(df_balances)):
            if df_balances['date'].iloc[i] > pd.to_datetime(max_date):
                list_df_balances.append((
                    datetime.datetime.strftime(df_balances['date'].iloc[i], '%Y-%m-%d'),
                    df_balances['exchangeRate'].iloc[i],
                    df_balances['cumulative'].iloc[i],
                    df_balances['cash'].iloc[i],
                    df_balances['marketValue'].iloc[i],
                    df_balances['totalEquity'].iloc[i]
                ))
        return list_df_balances

    @staticmethod
    def format_df_positions(df_positions, max_date=datetime.date(2000, 1, 1)):
        """ Convert df_positions df to formatted list to be fed into sql db

        :param df_positions: dataframe
        :param max_date: restrict dataframe based on max date
        :return: list
        """
        list_df_positions= []
        for i in range(len(df_positions)):
            if df_positions['date'].iloc[i] > pd.to_datetime(max_date):
                list_df_positions.append((
                    datetime.datetime.strftime(df_positions['date'].iloc[i], '%Y-%m-%d'),
                    df_positions['symbol'].iloc[i],
                    df_positions['value'].iloc[i]
                ))
        return list_df_positions

    @staticmethod
    def format_df_trades(df_trades, max_date=datetime.date(2000, 1, 1)):
        """ Convert df_trades to formatted list to be fed into sql db

        :param df_trades: dataframe
        :param max_date: restrict dataframe based on max date
        :return: list
        """
        list_df_trades = []
        for i in range(len(df_trades)):
            if df_trades['date'].iloc[i] > pd.to_datetime(max_date):
                list_df_trades.append((
                    datetime.datetime.strftime(df_trades['date'].iloc[i], '%Y-%m-%d'),
                    df_trades['symbol'].iloc[i],
                    df_trades['quantity'].iloc[i],
                    df_trades['totalCost'].iloc[i]
                ))
        return list_df_trades

    @staticmethod
    def format_df_returns(df_returns, max_date=datetime.date(2000, 1, 1)):
        """ Convert df_returns to formatted list to be fed into sql db

        :param df_returns: dataframe
        :param max_date: restrict dataframe based on max date
        :return: list
        """
        list_df_returns = []
        for i in range(len(df_returns)):
            if df_returns['date'].iloc[i] > pd.to_datetime(max_date):
                list_df_returns.append((
                    datetime.datetime.strftime(df_returns['date'].iloc[i], '%Y-%m-%d'),
                    df_returns['symbol'].iloc[i],
                    df_returns['quantity'].iloc[i],
                    df_returns['netProfit'].iloc[i]
                ))
        return list_df_returns

    @staticmethod
    def format_df_transfers(df_transfers, max_date=datetime.date(2000, 1, 1)):
        """ Convert df_transfers to formatted list to be fed into sql db

        :param df_transfers: dataframe
        :param max_date: restrict dataframe based on max date
        :return: list
        """
        list_df_transfers = []
        for i in range(len(df_transfers)):
            if df_transfers['date'].iloc[i] > pd.to_datetime(max_date):
                list_df_transfers.append((
                    datetime.datetime.strftime(df_transfers['date'].iloc[i], '%Y-%m-%d'),
                    df_transfers['added'].iloc[i],
                    df_transfers['cumulative'].iloc[i]
                ))
        return list_df_transfers


class AccountType:
    # map account index to specific account
    TFSA = ('TFSA', 0)
    MARGIN = ('MARGIN', 1)


class AccountQuestradeUtils:
    """ Utility functions for questrade.db """
    @staticmethod
    def add_unique_dates_to_db(conn, cursor, list_dates):
        """ Add new dates to questrade's date table if it doesn't exist

        Args:
            conn:
            cursor:
            list_dates: list of 'YYYY-MM-DD'

        Returns:

        """
        for date in list_dates:
            cursor.execute("SELECT date FROM dates WHERE date = '{}'".format(date))
            list_dates = cursor.fetchall()
            if not list_dates:
                cursor.execute("INSERT INTO dates(date) VALUES (?)", (date,))
                print(date + ' added to date table')
                conn.commit()

    @staticmethod
    def add_unique_symbs_to_db(conn, cursor, list_symbols):
        """ Add new symbols to questrade's symbols table if it doesn't exist

        Args:
            conn:
            cursor:
            list_symbols: list of symbs

        Returns:

        """
        for symb in list_symbols:
            cursor.execute("SELECT symbol FROM symbols WHERE symbol = '{}'".format(symb))
            if not cursor.fetchone():
                cursor.execute("INSERT INTO symbols (symbol) VALUES (?)", (symb,))
                print(symb + ' added to symbols table')
                conn.commit()

    @staticmethod
    def add_exchange_rate(conn, cursor, date, cad_usd):
        """ Add CAD/USD exchange rate given the date

        Args:
            conn:
            cursor:
            date: 'YYYY-MM-DD'
            cad_usd: CAD/USD

        Returns:

        """
        cursor.execute("INSERT INTO exchange_rate(date_id, cad_usd) \
                       VALUES ((SELECT date_id from dates WHERE date=?), ?)", (date, cad_usd))
        conn.commit()

    @staticmethod
    def add_new_trades_to_db(conn, cursor, account_type, new_trades):
        """ Given a trades dataframe, add to questrade's trades table

        Args:
            conn:
            cursor:
            account_type:
            new_trades: df

        Returns:

        """
        list_trades = []
        for i in range(len(new_trades)):
            list_trades.append((account_type, new_trades.iloc[i]['symbol'],
                                pd.to_datetime(new_trades.iloc[i]['date']).strftime('%Y-%m-%d'),
                                new_trades.iloc[i]['quantity'], new_trades.iloc[i]['totalCost']))
        cursor.executemany("INSERT INTO trades(account_id, symbol_id, date_id, quantity, value) \
                           VALUES ((SELECT account_id from accounts WHERE type=?), \
                                   (SELECT symbol_id from symbols WHERE symbol=?), \
                                   (SELECT date_id from dates WHERE date=?), ?, ?)", list_trades)
        conn.commit()

    @staticmethod
    def add_new_transfers_to_db(conn, cursor, account_type, new_transfers):
        list_transfers = []
        for i in range(len(new_transfers)):
            list_transfers.append(
                (account_type, pd.to_datetime(new_transfers.iloc[i]['date']).strftime('%Y-%m-%d'),
                 new_transfers.iloc[i]['added']))
        cursor.executemany("INSERT INTO transfers(account_id, date_id, deposit) \
                           VALUES ((SELECT account_id from accounts WHERE type=?), (SELECT date_id from dates WHERE date=?), ?)", \
                           list_transfers)
        conn.commit()

    @staticmethod
    def add_new_positions_to_db(conn, cursor, account_type, new_positions):
        list_positions = []
        for i in range(len(new_positions)):
            list_positions.append((account_type, new_positions.iloc[i]['symbol'], pd.to_datetime(new_positions.iloc[i]['date']).strftime('%Y-%m-%d'), new_positions.iloc[i]['value']))

        cursor.executemany("INSERT INTO positions(account_id, symbol_id, date_id, value) \
                           VALUES ((SELECT account_id from accounts WHERE type=?), \
                                   (SELECT symbol_id from symbols WHERE symbol=?), \
                                   (SELECT date_id from dates WHERE date=?), ?)", list_positions)
        conn.commit()


#####################
##### MAIN CODE #####
#####################
if __name__ == "__main__":
    print('\naccounts.py ran directly')
    # example of using an instance of the class
    if os.name == 'nt':
        investment_directory = 'C:/Users/A/Documents/K/Ongoing Projects/Investments/Questrade_Wrapper/'  # need for pickle load
    elif os.name == 'posix':
        investment_directory = '/mnt/a_drive/investments/'
    direct_data = '%suses/account_scripts/' % investment_directory
    direct_token = '%ssrc/' % investment_directory

    token = QuestradeAccounts(direct_token)
    token.check_access()

    # grab old data
    df_positions, df_balances, df_trades, df_returns, df_transfers = pickle.load(open('%saccount_data.pickle' % direct_data, 'rb'), encoding='latin1')

    # grab new positions
    new_positions = token.account_positions()
    df_positions = token.append_to_df(df_positions, new_positions)

    # grab new balances
    new_balances = token.account_balances()
    df_balances = token.append_to_df(df_balances, new_balances)
    # print(df_balances.tail(7))

    test = AccountsUtils.randomize_dataframe(df_balances)
    print(test.tail(7))

    # grab trades
    # df_trades = token.account_trades()

    # grab returns from trades
    # new_returns = token.account_returns(df_trades, endDay='')  # summarize trades into net profits
    # df_returns = token.append_to_df(df_returns, new_returns)

    # token.save([df_positions, df_balances, df_trades, df_returns, df_transfers], '%saccount_data.pickle' %direct_data)

    # df_transfers = token.account_transfers()
#    print(df_transfers)

    # positions_converted, balances_converted, trades_converted, returns_converted, transfers_converted = AccountsUtils.sql_to_df(direct_data + 'account_data.db')

    print('windows ran. data not saved.')

else:
    print('accounts.py imported')
