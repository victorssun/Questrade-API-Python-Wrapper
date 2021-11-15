"""
Test accounts.py class methods

`python -m pytest ./tests`
"""

import pytest
import pandas as pd
# from src.accounts import QuestradeAccounts, AccountsUtils

import os, sys

if os.name == 'nt':
    investment_directory = 'C:/Users/A/Documents/K/Ongoing Projects/Investments/Questrade_Wrapper/'
elif os.name == 'posix':
    investment_directory = '/mnt/a_drive/investments/Questrade_Wrapper/'
sys.path.append('%ssrc/' % investment_directory)
from accounts import QuestradeAccounts, AccountsUtils


@pytest.fixture
def token_fixture(pathname='src/'):
    """ Create token fixture given pathname where JSON file for refresh token exists

    Args:
        pathname: Folder where refreshtoken_windows.json exists

    Returns: QuestradeToken object

    """
    token = QuestradeAccounts(pathname)
    return token


def test_acc_positions(token_fixture):
    assert isinstance(token_fixture.account_positions(), pd.DataFrame)


def test_acc_balances(token_fixture):
    assert isinstance(token_fixture.account_balances(), pd.DataFrame)


def test_append_to_df(token_fixture):
    # TODO
    # grab new positions
    # new_positions = token.account_positions()
    # df_positions = token.append_to_df(df_positions, new_positions)
    df = pd.DataFrame()
    df_temp = token_fixture.account_balances()
    assert isinstance(token_fixture.append_to_df(df, df_temp), pd.DataFrame)


def test_acc_trades(token_fixture):
    assert isinstance(token_fixture.account_trades(), pd.DataFrame)


def test_acc_returns(token_fixture):
    df = token_fixture.account_trades()
    assert isinstance(token_fixture.account_returns(df, endDay=''), pd.DataFrame)


def test_acc_transfers(token_fixture):
    assert isinstance(token_fixture.account_transfers(), pd.DataFrame)


# TODO: test token.save()
# token.save([df_positions, df_balances, df_trades, df_returns, df_transfers], '%saccount_data.pickle' %direct_data)

# TODO: test AccountsUtils
# positions_converted, balances_converted, trades_converted, returns_converted, transfers_converted = AccountsUtils.sql_to_df(direct_data + 'account_data.db')

# TODO: test pickling
# df_positions, df_balances, df_trades, df_returns, df_transfers = pickle.load(open('%saccount_data.pickle' % direct_data, 'rb'), encoding='latin1')
