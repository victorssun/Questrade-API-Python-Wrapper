# -*- coding: utf-8 -*-
"""
Created on Thu Apr 19 21:10:12 2018

@author: A
Questrade API wrapper
- requires JSON formatted API token. System is down usually at 230am-530am EST.

functions: positions, balances, executions, orders, activities, symbs, candles, ex_rate

"""
import requests, datetime, time
import dateutil.parser
from dateutil.tz import tzutc
import os
import json


class IntervalType:
    OneYear = 'OneYear'
    OneMonth = 'OneMonth'
    OneWeek = 'OneWeek'
    OneDay = 'OneDay'
    FourHours = 'FourHours'


class QuestradeToken:
    def __init__(self, direct, refresh_token=None):
        self.directory = direct

        self.refresh_token = refresh_token
        self.expiry_date = None

        self.access_token = None
        self.url = None
        self.account_number = None

        self.initialize()

    def initialize(self):
        """
        Set refresh token, expiry date, access token, and account number properties

        :return: bool success
        """
        if not self.refresh_token:
            if os.name == 'nt':
                response = self._load_refresh('refreshtoken_windows.json')
            elif os.name == 'posix':
                response = self._load_refresh('refreshtoken_linux.json')
            else:
                response = None
            if not response:
                self._manual_refresh()

        response = self._load_access()
        count = 0
        while not response:
            self._manual_refresh()
            response = self._load_access()
            count +=1
            if count > 3:
                print('initalization failed at loading access')
                return False

        self.account_number = self.get_number()

        print('initialization success')
        return True

    def check_access(self):
        """
        Check if access token is expired (if no API requests after 30 minutes, access token expires).
        Load new access token from refresh token if expired.

        :return: bool success
        """
        call = '/positions'
        url2 = self.url + 'v1/accounts/' + self.account_number + call
        success, response_data = self._send_request(url2)
        if success:
            self.time_after = time.time() + 1800  # 30 minutes
            print('access token still valid. New expiry: %s' %time.ctime(self.time_after))
        else:
            print(response_data.json()['message'] + '. _load_access() ran to get new access token')
            success = self._load_access()
            if success:
                print('_load_access() success.')
            else:
                print('_load_access() failed. recommended to _manual_refresh()')

    # --- PUBLIC ---

    def get_number(self, i=0):
        # get accounts information/account number, for account calls
        # TODO: if more QT accounts, need to be updated -- could be 'TFSA', 'Cash', 'Margin'
        url2 = self.url + 'v1/accounts/'
        success, r = self._send_request(url2)
        return str(r['accounts'][i]['number'])

    def ex_rate(self):
        # get current CAD/USD exchange rate from cash balance valued in CAD vs. USD
        url2 = self.url + 'v1/accounts/' + self.account_number + '/balances'
        success, r = self._send_request(url2)
        cashCAD = r['sodCombinedBalances'][0]['cash'] # try sod, some how ex change is strange when b/s in the same day
        cashUSD = r['sodCombinedBalances'][1]['cash']
        return cashCAD / cashUSD

    def positions(self):
        # get a list of current positions with a dictionary of detailed stock info
        url2 = self.url + 'v1/accounts/' + self.account_number + '/positions'
        success, r = self._send_request(url2)
        return r['positions'] # list of positions

    def balances(self, currency='CAD'):
        # get combined CAD and USD balances
        url2 = self.url + 'v1/accounts/' + self.account_number + '/balances'
        success, r = self._send_request(url2)
        if currency == 'CAD':
            return r['combinedBalances'][0]
        elif currency == 'USD':
            return r['combinedBalances'][1]
        else:
            print('invalid arg')

    def balances_by_currency(self):
        # get list of dictionaries of CAD and USD balances separated
        url2 = self.url + 'v1/accounts/' + self.account_number + '/balances'
        success, r = self._send_request(url2)
        return r['perCurrencyBalances']

    def executions(self, datestring='creation to today'):
        # get a list of executions with detailed sell order info: date range does not work... I don't know why
        data = self._daterange(datestring)
        if datetime.datetime.utcnow().replace(tzinfo=tzutc()) - dateutil.parser.parse(data['endTime']) >= datetime.timedelta(30):
            print('Note: only capable of grabbing last 30 days')
        url2 = self.url + 'v1/accounts/' + self.account_number + '/executions'
        success, r = self._send_request(url2, data)
        return r['executions'] # list of executions

    def orders(self, datestring='creation to today', stateFilter='All', orderId=None):
        # get a dictionary of current orders: only limited to last 30 days
        # set all, open, or closed orders by: 'All', 'Open', 'Closed', orderId for single order detail
        data = self._daterange(datestring)
        if datetime.datetime.utcnow().replace(tzinfo=tzutc()) - dateutil.parser.parse(data['endTime']) >= datetime.timedelta(30):
            print('Note: only capable of grabbing last 30 days')
        url2 = self.url + 'v1/accounts/' + self.account_number + '/orders'
        data['stateFilter'] = stateFilter
        data['orderId'] = orderId
        success, r = self._send_request(url2, data)
        return r['orders'] # list of orders

    def activities(self, datestring='2018-04-01 to 2018-04-20'):
        # get account activities
        # maximum 31 days of data
        data = self._daterange(datestring)
        if dateutil.parser.parse(data['endTime']) - dateutil.parser.parse(data['startTime']) <= datetime.timedelta(31):
            url2 = self.url + 'v1/accounts/' + self.account_number + '/activities'
            success, r = self._send_request(url2, data)
            return r['activities'] # list of activities
        else:
            print('out of range. maximum of 31 days.')
            return None

    def symbs(self, names):
        # get list of symbols input as 'RHT,HTHT'
        url2 = self.url + 'v1/symbols?'
        data = {
            'names': names,
            }
        success, r = self._send_request(url2, data)
        return r['symbols']

    def candles(self, name=None, datestring='creation to today', interval='OneDay'):
        # get candles. daterange seems to be any range again, watch for changes
        ids = str(self._name2ids(name))
        url2 = self.url + 'v1/markets/candles/' + ids + '?'
        data = self._daterange(datestring)
        data['interval'] = interval
        success, r = self._send_request(url2, data)
        candles = r['candles']
        return candles

    def _name2ids(self, name):
        # grab symbol id from name. used for candles
        url2 = self.url + 'v1/symbols?'
        data = {
            'names': name,
            }
        success, r = self._send_request(url2, data)
        return r['symbols'][0]['symbolId'] # list of symbols

    # --- PRIVATE ---

    def _load_access(self):
        """
        Set access token property.
        Crabbing an access token generates a new refresh token that gets saved to .json file

        :return: bool success
        """
        url = 'https://login.questrade.com/oauth2/token?'
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
            }
        time_before = time.time()
        r = requests.get(url, params=data)
        if str(r) == '<Response [200]>':
            response_data = r.json()
            self.time_after = time_before + response_data['expires_in']
            self.refresh_token = str(response_data['refresh_token']) # obtain another refresh token
            self.access_token = str('%s %s' %(response_data['token_type'], response_data['access_token']))
            self.url = str(response_data['api_server'])
            print('new refresh: %s \nnew access: %s \nexpires at: %s' %(self.refresh_token, self.access_token, time.ctime(self.time_after)))
            self._save_refresh()
            return True
        else:
            print('load access token failed')
            return False

    def _load_refresh(self, fn='refreshtoken_windows.json'):
        """
        Load refresh token from given filename, setting refresh token and expirty date property

        :param fn: filename of JSON formatted refresh API  token
        :return: bool success
        """
        filename = '%s%s' %(self.directory, fn)

        try:
            f = open(filename)
            data = json.load(f)
            f.close()
        except:
            # if file does not open assume no file or incorrect format, therefore generate blank file
            f = open(filename, 'w')
            data = {
                'refresh_token': "PLACE_REFRESH_TOKEN_HERE",
                'expiry_date': str(datetime.date.today() + datetime.timedelta(days=6))
            }
            json.dump(data, f, indent=4)
            f.close()
            print('blank .JSON refreshtoken file crated.')

        self.refresh_token = data['refresh_token']
        self.expiry_date = data['expiry_date']

        if datetime.datetime.today() > datetime.datetime.strptime(self.expiry_date, '%Y-%m-%d'):
            print('refresh token expired.')
            return False

        print('refresh token loaded: {}, expires {}'.format(self.refresh_token, self.expiry_date))
        return True

    def _save_refresh(self):
        """
        Save current refresh token to refreshtoken_windows/linux.json file
        Required to be run every time access token is generated.

        :return:
        """
        expiry_date = datetime.date.today() + datetime.timedelta(days=6)
        if os.name == 'nt':
            filename = '%srefreshtoken_windows.json' %(self.directory)
        elif os.name == 'posix':
            filename = '%srefreshtoken_linux.json' %(self.directory)
        f = open(filename, 'w')
        data = {
                'refresh_token': self.refresh_token,
                'expiry_date': str(expiry_date)
                }
        json.dump(data, f, indent=4)
        f.close()
        print('saved refresh: %s \nexpires: %s' %(self.refresh_token, expiry_date))

    def _manual_refresh(self):
        self.refresh_token = input('enter new refresh token: ')
        self.expiry_date = datetime.datetime.strftime(datetime.datetime.today() + datetime.timedelta(days=6), '%Y-%m-%d')
        print('may require to run _load_access()')

    def _daterange(self, daterange):
        """
        Format input daterange string to isoformat

        :param daterange: daterange as a string -- ex. 'YYYY-MM-DD to YYYY-MM-DD'
            - first date can be creation for '2018-01-01' or beginning for '2000-01-01'
        :return: {'startTime: isoformat startday, 'endTime' isoformat endday}
        """
        # startDay can be creation or beginning, endDay can be today
        if daterange.split()[0] == 'creation':
            startDay = datetime.datetime(2018, 1, 1, 0, 0).isoformat() + str('Z')
        elif daterange.split()[0] == 'beginning':
            startDay = datetime.datetime(2000, 1, 1, 0, 0).isoformat() + str('Z')
        else:
            startDay = datetime.datetime.strptime(daterange.split()[0], '%Y-%m-%d').isoformat() + str('Z')
        if daterange.split()[2] == 'today':
            tdate = datetime.datetime.now()
            endDay = datetime.datetime(tdate.year, tdate.month, tdate.day+1, 0, 0).isoformat() + str('Z')
        else:
            endDay = datetime.datetime.strptime(daterange.split()[2], '%Y-%m-%d').isoformat() + str('Z')
        return {'startTime': startDay, 'endTime': endDay}

    def _send_request(self, url, data=None):
        """
        Checks if request is successful and parse out data

        :param url: url of API request
        :param data: data parameters of API request
        :return: bool success, data
        """
        if data == None:
            r = requests.get(url, headers={'authorization': self.access_token})
        else:
            r = requests.get(url, params=data, headers={'authorization': self.access_token})

        if str(r) == '<Response [200]>':
            self.time_after =  time.time() + 1800 # 30 mins
            return True, r.json()
        else:
            print('Error: {}'.format(r.json()))
            return False, r


#####################
##### MAIN CODE #####
#####################
if __name__ == "__main__":
    print('\nquestrade.py ran directly')
    # example of using an instance of the class
    if os.name == 'nt':
        direct = 'C:/Users/A/Documents/K/Ongoing Projects/Investments/Questrade_Wrapper/src/' # need for pickle load
    elif os.name == 'posix':
        direct = '/mnt/a_drive/investments/Questrade_Wrapper/src/'
    token = QuestradeToken(direct)

    # url = token.url + 'v1/accounts/' + token.account_number + '/activities'
    # data = token._daterange('creation to today')
    # success, response = token._send_request(url, data)
    # response.json()

    # token.check_access()

    positions = token.positions()
    balances = token.balances('CAD')
    balances_separated = token.balances_by_currency()
    ex = token.ex_rate()
    execs = token.executions()
    orders = token.orders() # last 30 days of orders only
    activities = token.activities('2021-01-01 to 2021-01-31')
    symbs = token.symbs('TSLA,TMO')
    candles = token.candles(name='MSFT', datestring='2000-01-01 to 2001-01-01')

else:
    print('\nquestrade imported')
