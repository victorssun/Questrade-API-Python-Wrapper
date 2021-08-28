# -*- coding: utf-8 -*-
"""
Created on Mon Apr 30 22:49:27 2018

@author: A
Plot daily balances, positions, profits data
"""
import sys
import os
import datetime
import pickle
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import dateutil

if os.name == 'nt':
    direct_token = 'C:/Users/A/Documents/K/Ongoing Projects/Investments/Questrade_Wrapper/src/'
    direct_data = 'C:/Users/A/Documents/K/Ongoing Projects/Investments/Questrade_Wrapper/uses/'
elif os.name == 'posix':
    direct_token = '/mnt/a_drive/investments/Questrade_Wrapper/src/'
    direct_data = '/mnt/a_drive/investments/Questrade_Wrapper/uses/'
sys.path.append(direct_token)
import accounts
# import src.accounts as accounts

def calculate_expected_return(df_transfers, expected_rate, series_name=None):
    """ Calculate expected returns based on expected rate and cumulative equity

    :param df_transfers: cumulative equity with date
    :param expected_rate: annual rate of expected return
    :param series_name: column name of series
    :return: pd series, no date
    """
    if series_name:
        expected_f = pd.Series(name=series_name, dtype=float)
    else:
        expected_f = pd.Series()

    # for each deposit/withdrawal, calculate expected return of cumulative equity from day of deposit to next deposit
    for i in range(len(df_transfers) - 1):
        date_diff = df_transfers.loc[i + 1, 'date'] - df_transfers.loc[i, 'date']

        # (annual rate)/(days in year)*(date difference)*(value of assets) = rough expected expected value based on the annual rate
        expected_return = float(expected_rate) / 365 * date_diff.days * df_transfers.loc[i, 'cumulative']
        expected_f.loc[i + 1] = expected_return

    expected_f = expected_f.cumsum()  # convert to cumulative sum
    # df_transfers = pd.concat([df_transfers, expected_f], axis=1)  # concat the expected data to the df

    return expected_f


def calculate_market_return(token, df_transfers):
    # select parameters for the bundled theoretical market return
    datestring = '2018-01-01 to today'
    interval = 'OneDay'
    
    # select theoretical stocks: tsx, russell2000, sp500, nasdaq and get average return
    tsx = candles2df(token, 'tsx.in', datestring, interval)
    sp500 = candles2df(token, 'spx.in', datestring, interval)
    nasdaq = candles2df(token, 'comp.in', datestring, interval)
    
    bundle = pd.DataFrame([tsx['start'], (tsx['diff'] + sp500['diff'] + nasdaq['diff'])/3]).T
    bundle = bundle[~bundle['start'].isnull()]
    
    #  match df_deposits to respective 'diff'
    df_transfers = df_transfers.copy() # create copy not overwrite original
    df_transfers['date'] = df_transfers['date'].dt.date
    bundle2 = pd.merge(bundle, df_transfers, how='left', left_on='start', right_on='date')
    bundle2 = bundle2[['start', 'diff', 'added']]
    
    # convert weighted bundle to theoretical returns
    for i in range(1, len(df_transfers)-1):
        # current % / initial % * added cash * starting on the date of added cash
        bundle2 = pd.concat([bundle2, bundle['diff']/ bundle['diff'][bundle['start'] == df_transfers['date'][i]].iloc[0] * (bundle2['start'] >= df_transfers['date'][i]) * (df_transfers['added'][i])], axis=1) #  * (df_deposits[1][i])
    bundle2['init'] = bundle2['added'].fillna(0).cumsum() # cumsum of added cash
    
    # two deposits in one day fix
    bundle2['init'] = bundle2['init'].mask(bundle2['start'] == datetime.date(2018, 1, 23), 5500)
    
    # sum all individual added cash return since each column of 0 is only accounting for the added cash
    bundle2['market'] = bundle2[0].sum(axis=1) - bundle2['init']
    bundle2 = bundle2[['start', 'init', 'diff', 'market']]
    bundle2['market'].iloc[-1] = bundle2['market'].iloc[-2] # remove nan to plot
    
    return bundle2


def calculate_real_returns(df_transfers, df_balances):
    """ Get actual real returns

    :param df_transfers: deposits and withdrawls from df_transfers
    :param df_balances: balances df
    :return: df_actual
    """
    # for each expected date, ensure df_balances data are after the addition/withdrawal of assets
    df_actual = df_balances[['date', 'totalEquity']]
    df_temp = pd.DataFrame()
    for i in range(len(df_expected) - 1):
        # at each expected data, generate new bool column where df_balances only exist greater than the date of each expected date
        check = df_actual['date'] >= df_expected.loc[i, 'date']
        check = check.rename(i)
        df_temp = pd.concat([df_temp, check], axis=1)

    # count all cells in the row: sum all True statements where actual return data is after the expected data, this is equivalent to the cumulative amount of assets held
    sums = df_temp.sum(axis=1) - 1  # to be used as index of df_expected to get actual returns instead of total equity
    for i in range(len(sums)):
        df_actual.loc[i, 'totalEquity'] = df_actual.loc[i, 'totalEquity'] - df_transfers.loc[sums.iloc[i], 'cumulative']
    df_actual.columns = ['date', 'actual']

    return df_actual


def plot_returns(df_expected, df_market, df_actual):
    """ Plot expected and actual returns over time

    :param df_expected: expected returns dataframe
    :param df_market: market returns dataframe
    :param df_actual: actual returns dataframe
    :return:
    """
    fig = plt.figure(figsize=(8, 8))
    ax1 = fig.add_subplot(211)

    for col in df_expected.columns:
        if col != 'date':
            ax1.plot(df_expected['date'], df_expected[col], label=col)

    ax1.plot(df_actual['date'], df_actual['actual'], linestyle='None', marker='.', markersize=1, label='actual')
    ax1.plot(df_market['start'], df_market['market'], label='market')

    ax1.set_title('%s Returns: %.2f actual, %.2f market' % (df_balances['date'].max(),
                                                           df_actual.iloc[-1]['actual'] / max(df_transfers['cumulative']),
                                                           df_market['market'].iloc[-1] / df_market['init'].iloc[-1]))

    ax1.set_xlim(left=datetime.date(2018, 1, 1))
    ax1.grid(axis='y', linestyle='--')
    ax1.legend(loc=2)
    
    # plot total equity, cash, and market value of all assets held
    ax2 = fig.add_subplot(212)
    ax2.plot(df_balances['date'], df_balances['totalEquity'], linestyle='-', alpha=0.5, linewidth=1, label='total')
    ax2.plot(df_balances['date'], df_balances['cash'], linestyle=':', alpha=0.5, linewidth=2, label='cash')
    ax2.plot(df_balances['date'], df_balances['marketValue'], linestyle=':', alpha=0.5, linewidth=2, label='held')

    ax2.set_yticklabels([])
    fig.autofmt_xdate()

    return fig


def plot_portfolio(df_positions, date='None', fig='', figposition=111):
    """ Plot current portfolio pie graph based on given date

    :param df_positions:
    :param date:
    :param fig:
    :param figposition:
    :return:
    """
    # create figure if a subplot position is not given
    if figposition == 111:
        fig = plt.figure(figsize=(8, 8))
        ax1 = fig.add_subplot(111)
    else:
        ax1 = fig.add_subplot(figposition)
    ax1.axis('equal')
    # select date
    if date == 'None':
        date = df_positions['date'].max()
    # plot
    pie = df_positions[df_positions['date']==date]
    pie = pie.sort_values(by=['symbol'])
    ax1.pie(pie['value'], labels=pie['symbol'], autopct='%1.1f%%', startangle=0)
    ax1.set_title('%s Portfolio' %date)

    return fig


def plot_profits(df_returns, fig='', figposition=111):
    """ Plot net profit/loss bar graph per stock

    :param df_returns:
    :param fig:
    :param figposition:
    :return:
    """
    if figposition == 111:
        fig = plt.figure(figsize=(8, 8))
        ax1 = fig.add_subplot(111)
    else:
        ax1 = fig.add_subplot(figposition)

    date = df_returns['date'].iloc[0].date()
    returns_sorted = df_returns.sort_values('netProfit', ascending=False)
    symbs = returns_sorted['symbol'].values.tolist()
    netProfit = returns_sorted['netProfit'].values.tolist()
    netProfit_now = returns_sorted['netProfit'] * returns_sorted['quantity'] / returns_sorted['quantity']
    nticks = np.arange(len(returns_sorted['symbol']))

    width = 0.35
    ax1.set_xticks(nticks+width)
    ax1.bar(nticks, netProfit, width=width, align='center', tick_label=symbs)
    ax1.bar(nticks+width, netProfit_now, width=width, align='center')
    ax1.set_yticks(np.arange(-1000, 1001, 500))
    ax1.grid(axis='y', linestyle='--', markersize=50)
    ax1.set_xticklabels(ax1.get_xticklabels(), rotation=90)
    ax1.set_title('%s Profits' %date)
    return fig


def candles2df(token, name, datestring, interval):
    """ Calculate relative percent change of a given stock from start of datestring

    :param token:
    :param name:
    :param datestring:
    :param interval:
    :return:
    """
    data = token.candles(name, datestring, interval)
    df = pd.DataFrame(data)
    counter = 0
    # convert isoformat to datetime
    for ea in df['start']:
        ea = dateutil.parser.parse(ea, ignoretz=True)
        df.loc[counter, 'start'] = ea.date()
        counter = counter + 1
    # select columns + % change
    df = df[['start', 'close']]
    diff = df['close'] / df['close'].iloc[0]
    df = pd.concat([df, diff], axis=1)
    df.columns = ['start', 'close', 'diff']
    return df

############
### MAIN ###
############
df_positions, df_balances, df_trades, df_returns, df_transfers = pickle.load(open('%saccount_data.pickle' % direct_data, 'rb'))

# mask data for public
if False:
    df_positions = accounts.AccountsUtils.randomize_dataframe(df_positions)
    df_balances = accounts.AccountsUtils.randomize_dataframe(df_balances)
    df_trades = accounts.AccountsUtils.randomize_dataframe(df_trades)
    df_returns = accounts.AccountsUtils.randomize_dataframe(df_returns)

# generate instance of accounts
token = accounts.QuestradeAccounts(direct_token)

# grab cumulative equity
# df_transfers = token.account_transfers()
df_transfers = df_transfers.append({'added': 0, 'date': pd.Timestamp.today(), 'cumulative': max(df_transfers['cumulative'])}, ignore_index=True)

# generate expected, market, and actual returns data
df_expected = pd.concat([df_transfers['date']], axis=1)
df_expected = pd.concat([df_expected, calculate_expected_return(df_transfers, 0.02, 'savings')], axis=1)

df_market = calculate_market_return(token, df_transfers)

df_actual = calculate_real_returns(df_transfers, df_balances)

fig1 = plot_returns(df_expected, df_market, df_actual)
fig2 = plot_portfolio(df_positions)
fig3 = plot_profits(df_returns)

fig1.savefig(direct_data + 'returns.png', format='png')
fig2.savefig(direct_data + 'portfolio.png', format='png')
fig3.savefig(direct_data + 'profits.png', format='png')
