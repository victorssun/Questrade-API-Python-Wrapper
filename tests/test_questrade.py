"""
Test questrade.py class methods

`python -m pytest ./tests`
"""

import pytest
# from src.questrade import QuestradeToken

import os, sys

if os.name == 'nt':
    investment_directory = 'C:/Users/A/Documents/K/Ongoing Projects/Investments/Questrade_Wrapper/'
elif os.name == 'posix':
    investment_directory = '/mnt/a_drive/investments/Questrade_Wrapper/'
sys.path.append('%ssrc/' % investment_directory)
from questrade import QuestradeToken

@pytest.fixture
def token_fixture(pathname='src/'):
    """ Create token fixture given pathname where JSON file for refresh token exists

    Args:
        pathname: Folder where refreshtoken_windows.json exists

    Returns: QuestradeToken object

    """
    token = QuestradeToken(pathname)
    return token


# def test_initialize(pathname='src/'):
#     """ Indirectly test successful QuestradeToken initialization by checking if account_number exists
#
#     Args:
#         pathname: Folder where refresh_token_windows.json exists
#
#     Returns:
#
#     """
#     token = QuestradeToken(pathname)
#     assert isinstance(token.account_number, str)


def test_balances(token_fixture):
    assert isinstance(token_fixture.balances(), dict)


def test_positions(token_fixture):
    assert isinstance(token_fixture.positions(), list)


def test_balances_by_currency(token_fixture):
    assert isinstance(token_fixture.balances_by_currency(), list)


def test_exchange_rate(token_fixture):
    assert isinstance(token_fixture.ex_rate(), float)


def test_executions(token_fixture):
    assert isinstance(token_fixture.executions(), list)


def test_orders(token_fixture):
    assert isinstance(token_fixture.orders(), list)


def test_activities(token_fixture):
    assert isinstance(token_fixture.activities(), list)


def test_symbs(token_fixture):
    assert isinstance(token_fixture.symbs('TSLA,TMO'), list)


def test_candles(token_fixture):
    assert isinstance(token_fixture.candles('MSFT', datestring='2000-01-01 to 2001-01-01'), list)


# TODO: make tests more complex
# TODO: test access token
# TODO: test token._daterange() for activities, orders/executions
