# -*- coding: utf-8 -*-
"""
Created on Thu Apr 19 21:10:12 2018

@author: A
Questrade API
- Note: Questrade usually closes for maintence every midnight
- If not on windows, selenium won't run
Requires: directory
* _open_api
* _load_refresh
* _get_access 

calltoken
* __init__
* get_number
* check_access
* save_refresh

* __init__
* _runapi
* positions
* balances
* executions: daterange
* orders: daterange, all/open/close
* cancel_order: orderid # shouldn't use
* activities: daterange
callmarket
* symbs: names
* candles: name, start, end, interval
* _name2ids: name
* _daterange

* ex_rate

"""
import requests, datetime, time, pickle
from selenium import webdriver
import dateutil.parser
import os

def _open_api(username=None, password=None, sa1=None, sa2=None): # one output
    # required only if refresh token expired
    if username == None:
        if os.name == 'nt':
            inputs = raw_input('refresh token expired. enter user, pw, SA1, SA2: ')
        username, password, sa1, sa2 = inputs.split(', ')  
    # open brower
    driver = webdriver.Chrome(r'%schromedriver.exe' %direct) # hardcoded, should change
#    driver = webdriver.Chrome(r'/mnt/name/Questrade_API/chromedriver.exe') 
    driver.get('https://login.questrade.com/Signin.aspx?ReturnUrl=%2fAPIAccess%2fuserapps.aspx')
    # input login
    inputElem_username = driver.find_element_by_id('ctl00_DefaultContent_txtUsername')
    inputElem_password = driver.find_element_by_id('ctl00_DefaultContent_txtPassword')
    inputElem_username.send_keys(username)
    inputElem_password.send_keys(password)
    driver.find_element_by_id('ctl00_DefaultContent_btnLogin').click()
    # input answer
    question = driver.find_element_by_xpath("//div[contains(@class, 'question lg')]")
    inputElem_content = driver.find_element_by_id('ctl00_DefaultContent_txtAnswer')
    if 'SA1' in question.text:
        inputElem_content.send_keys(sa1)
    elif 'SA2' in question.text:
        inputElem_content.send_keys(sa2)
    driver.find_element_by_id('ctl00_DefaultContent_btnContinue').click()
    # generate refresh token
    driver.find_element_by_xpath("//div[contains(@class, 'genNewToken')]").click()
    time.sleep(5) # let key load
    inputElem_refresh = driver.find_element_by_xpath("//span[contains(@id, 'spanTokenValue')]")
    refresh_token = str(inputElem_refresh.text)
#    print('generated refresh token: %s' %refresh_token)
    driver.quit()
    return refresh_token

def _load_refresh(direct): # one output
    # load last refresh token if file not expired, else runs _open_api()
    if os.name == 'nt':
        filename = '%srefreshtoken_windows.pickle' %direct
    elif os.name == 'posix':
        filename = '%srefreshtoken_linux.pickle' %direct
#    filename = '%srefreshtoken.pickle' %direct
    refresh_token, expiry_date = pickle.load(open(filename, 'rb'))
    if datetime.datetime.today() <= datetime.datetime.strptime(expiry_date, '%Y-%m-%d'):
        print('refresh token loaded: %s' %refresh_token)
        return refresh_token #, expiry_date
    else:
        refresh_token2 = _open_api()
        print('new refresh token: %s' %refresh_token2)
        return refresh_token2

def _get_access(refresh_token): # three output
    # required only if access token expire. Note: as long as access token is used every thirty minutes, it refreshes
    url = 'https://login.questrade.com/oauth2/token?'
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        }
    r = requests.get(url, params=data)
    time_before = time.time()
    if str(r) != '<Response [400]>':
        r = r.json()
        time_after = time_before + r['expires_in']
        #time.ctime(time_after) # access token expires at
        r['token_type']
        refresh_token = str(r['refresh_token']) # obtain another refresh token
        access_token = str('%s %s' %(r['token_type'], r['access_token']))
        url = str(r['api_server'])
        print('\ngenerated access token \nrefresh: %s \naccess: %s \nexpires at: %s' %(refresh_token, access_token, time.ctime(time_after)))
        return refresh_token, access_token, url, time_after
    else:
        refresh_token2 = _open_api()
        print('new refresh token: %s' %refresh_token2)
        refresh_token, access_token, url, time_after = _get_access(refresh_token2)
        return refresh_token, access_token, url, time_after

def _get_number(self): # one output
    # get accounts information/account number
    url2 = self.url + 'v1/accounts/'
    r = requests.get(url2, headers={'authorization': self.access_token})
    r = r.json()
    self.account_number = str(r['accounts'][0]['number'])
    return self

class calltoken: 
    # initalize calltoken to grab data from account or market
    def __init__(self, direct):
        self.direct = direct
        refresh_token = _load_refresh(self.direct) # try loading previously saved refresh token. If expired, goes to _open_api()
        self.refresh_token, self.access_token, self.url, self.time_after = _get_access(refresh_token) # try loading access token. If 400 error, goes to _open_api()
        self.save_refresh()
#        self.auth = {'authorization': self.access_token} # replace with all authorizations later
        self = _get_number(self) # get account number for account calls
#        self.account_number = 'NUMBER' # or just hardcode
#        self.check_access()        
        self.account_info = [self.direct, self.refresh_token, self.access_token, self.url, self.account_number] # bundle all important information
        print('\ntoken initialized')
        
    def get_number(self): # one output
        # get accounts information/account number
        url2 = self.url + 'v1/accounts/'
        r = requests.get(url2, headers={'authorization': self.access_token})
        r = r.json()
        self.account_number = str(r['accounts'][0]['number'])
        return self

    def check_access(self, call='/positions'): # three outputs
        # check if access token is expired, else runs _get_access()
        call = '/positions'
        url2 = self.url + 'v1/accounts/' + self.account_number + call
        r = requests.get(url2, headers={'authorization': self.access_token})
        r = r.json()
        try:
            r['message']
            print(r['message'] + '. _get_access() ran. new access_token')
            self.refresh_token, self.access_token, self.url, self.time_after = _get_access(self.refresh_token)
            self.account_info = [self.direct, self.refresh_token, self.access_token, self.url, self.account_number]            
            self.save_refresh()
            return self
        except:
            self.time_after = time.time() + 1800 # 30 minutes
            print('access token still valid. New expiry: %s' %time.ctime(self.time_after))
            return

    def save_refresh(self):
        # save last refresh token for next time so no log in required. Lasts for seven days.
        token_expire = datetime.date.today() + datetime.timedelta(days=6)
        if os.name == 'nt':
            filename = '%srefreshtoken_windows.pickle' %(self.direct)
        elif os.name == 'posix':
            filename = '%srefreshtoken_linux.pickle' %(self.direct)
#        filename = '%srefreshtoken.pickle' %(self.direct)
        pickle.dump([self.refresh_token, str(token_expire)], open(filename, 'wb'))
        print('\nsaved refresh: %s \nexpires: %s' %(self.refresh_token, token_expire))
        
#        self.direct = info[0] # direct
#        self.access_token = info[1] # access_token
#        self.url = info[2] # url
#        self.account_number = info[3] # account_number
#        print('account intialized')
    
    def _runapi(self, data=None):
        # run requests
        if data == None:
            r = requests.get(self.url2, headers={'authorization': self.access_token})
            return r.json()
        else:
            r = requests.get(self.url2, params=data, headers={'authorization': self.access_token})
            return r.json()
        
    def positions(self):
        # get current positions
        self.url2 = self.url + 'v1/accounts/' + self.account_number + '/positions'
        r = self._runapi()
        positions = r['positions'] # list of positions
        key_positions = r['positions'][0].keys() # 'totalCost', 'closedQuantity', 'symbol', 'symbolId', 'isRealTime', 'closedPnl', 'currentPrice', 'openQuantity', 'averageEntryPrice', 'isUnderReorg', 'currentMarketValue', 'openPnl'
        return positions, key_positions
    
    def balances(self):
        # get current balances
        self.url2 = self.url + 'v1/accounts/' + self.account_number + '/balances'
        r = self._runapi()
        balances = r
        key_balances = r.keys() # 'perCurrencyBalances', 'sodPerCurrencyBalances', 'combinedBalances', 'sodCombinedBalances'
        key_balances_depth = r[str(key_balances[0])][0].keys() # always look at 0. 0 = CAD, 1 = USD. 'marketValue', 'cash', 'isRealTime', 'buyingPower', 'currency', 'maintenanceExcess', 'totalEquity'
        return balances, key_balances, key_balances_depth

    def executions(self, datestring='creation to today'):
        # get executions
        # set date range by: 'YYYY-MM-DD to YYYY-MM-DD'. Default full range
        startTime, endTime = self._daterange(datestring)
        self.url2 = self.url + 'v1/accounts/' + self.account_number + '/executions'
        data = {
            'startTime': startTime,
            'endTime': endTime,
            }        
        r = self._runapi(data)
        execs = r['executions'] # list of executions
        key_exec_depth = execs[0].keys() # 'orderId', 'orderChainId', 'secFee', 'timestamp', 'price', 'symbolId', 'venue', 'exchangeExecId', 'legId', 'id', 'commission', 'totalCost', 'canadianExecutionFee', 'notes', 'executionFee', 'parentId', 'quantity', 'symbol', 'orderPlacementCommission', 'side'
        return execs, key_exec_depth
    
    def orders(self, datestring='creation to today', stateFilter='All', orderId=None):
        # get orders
        # set date range by: 'YYYY-MM-DD to YYYY-MM-DD'
        # set all, open, or closed orders by: 'All', 'Open', 'Closed'
        # set orderId if want to retrieve single order detail
        startTime, endTime = self._daterange(datestring)        
        self.url2 = self.url + 'v1/accounts/' + self.account_number + '/orders'
        data = {
            'startTime': startTime,
            'endTime': endTime,
            'stateFilter': stateFilter,
            'orderId': orderId,
            }
        r = self._runapi(data)
        orders = r['orders'] # list of orders
        key_orders = orders[0].keys() # need to explore more
        return orders, key_orders
    
    def cancel_order(self, orderid):
        # cancel order, works but shouldn't use
        # find open orders by running self.orders()
        self.url2 = self.url + 'v1/accounts/' + self.account_number + '/orders/' + orderid
        r = self._runapi()
        print r
    
    def activities(self, datestring='2018-04-01 to 2018-04-20'):
        # get account activities
        # maximum 31 days of data
        startTime, endTime = self._daterange(datestring)
        if dateutil.parser.parse(endTime) - dateutil.parser.parse(startTime) <= datetime.timedelta(31):
            self.url2 = self.url + 'v1/accounts/' + self.account_number + '/activities'
            data = {
                'startTime': startTime,
                'endTime': endTime,
                }
            r = self._runapi(data)
            activities = r['activities'] # list of activities
            key_activities = activities[0].keys() #'settlementDate', 'description', 'tradeDate', 'type', 'symbol', 'transactionDate', 'symbolId', 'grossAmount', 'currency', 'commission', 'action', 'netAmount', 'price', 'quantity'
            return activities, key_activities
        else:
            print('out of range. maximum of 31 days.')
            # HOW TO GET RID OF ERROR
            return None, None
    
    # ignore symb/search, options; market/quotes, markets and strategies might be useful later
    # ignore accounts/orders, impact, bracket, strategy
    def symbs(self, names):
        # get symbols
        # set symbols as: 'name1,name2'
#        names = 'RHT,HTHT'
        self.url2 = self.url + 'v1/symbols?'
        data = {
        #    'ids': start_time,
            'names': names,
            }
        r = self._runapi(data)
        symbs = r['symbols'] # list of symbols
        key_symbs = symbs[0].keys() # explore more
        return symbs, key_symbs
    
    def candles(self, name=None, datestring='creation to today', interval='OneDay'):
        # get candles. Note: data can only go so far
        # set symbol ids by: 'name'
        # set date range by: 'YYYY-MM-DD to YYYY-MM-DD/today'
        # set interval by enumeration
        ids = str(self._name2ids(name))
        self.url2 = self.url + 'v1/markets/candles/' + ids + '?'
        startTime, endTime = self._daterange(datestring)
        data = {
            'startTime': startTime,
            'endTime': endTime,
            'interval': interval,
            }        
        r = self._runapi(data)
        candles = r['candles']
        key_candles = candles[0].keys() # 'volume', 'end', 'VWAP', 'high', 'start', 'low', 'close', 'open'
        return candles, key_candles    
    
    def _name2ids(self, name):
        # grab symbol id from name. used for candles
        self.url2 = self.url + 'v1/symbols?'
        data = {
        #    'ids': start_time,
            'names': name,
            }
        r = self._runapi(data)
        ids = r['symbols'][0]['symbolId'] # list of symbols
        return ids
    
    def _daterange(self, daterange):
        # format input string date range to isoformat
        # set date range as: 'YYYY-MM-DD to YYYY-MM-DD'
        # startDay can be creation or beginning, endDay can be today
        if daterange.split()[0] == 'creation':
            startDay = datetime.datetime(2018, 01, 1, 0, 0).isoformat() + str('Z')
        elif daterange.split()[0] == 'beginning':
            startDay = datetime.datetime(2000, 01, 1, 0, 0).isoformat() + str('Z')
        else:
            startDay = datetime.datetime.strptime(daterange.split()[0], '%Y-%m-%d').isoformat() + str('Z')
        if daterange.split()[2] == 'today':
            endDay = datetime.datetime.now().isoformat() + str('Z')
        else:
            endDay = (datetime.datetime.strptime(daterange.split()[2], '%Y-%m-%d')+ datetime.timedelta(days=1)).isoformat() + str('Z')
        return startDay, endDay    
    
    def ex_rate(self):
        # get current CAD/USD exchange rate
        cashCAD = token.balances()[0]['sodCombinedBalances'][0]['cash'] # try sod, some how ex change is strange when b/s in the same day
        cashUSD = token.balances()[0]['sodCombinedBalances'][1]['cash']
        ex = cashCAD / cashUSD # CAD/USD. MAKE THIS INTO FUNCTION LATER
        return ex
        
#####################
##### MAIN CODE #####
#####################
# auto set-up
if os.name == 'nt':
    direct = 'C:/Users/name/Questrade_API/' # need for pickle load
elif os.name == 'posix':
    direct = '/mnt/name/Questrade_API/'
        
token = calltoken(direct)
#account = callaccount(token.account_info)

if __name__ == "__main__":
    print('\nquestrade.py ran directly')
    # showcase all functions/to debug
    if False:
        direct = 'C:/Users/name/Questrade_API/'
        
        token = calltoken(direct)
        token.get_number()
        token.check_access() # sometimes check status of access token, if expire, will create new one
        token.save_refresh()
        
        account = callaccount(token.account_info)
        positions, key_positions = account.positions()
        balances, key_balances, key_balances_depth = account.balances()
        execs, key_exec_depth = account.executions('YYYY-MM-DD to YYYY-MM-DD')
        orders, key_orders = account.orders('YYYY-MM-DD to YYYY-MM-DD', 'All')
        account.cancel_order('orderId')
        activities, key_activities = account.activities('YYYY-MM-DD to YYYY-MM-DD')
        
        symbs, key_symbs = account.symbs('RHT,HTHT')
        candles, key_candles = account.candles(name, 'YYYY-MM-DD HH:mm', 'YYYY-MM-DD HH:mm', 'OneDay')
    else:
        print('showcase not ran')
else:
    print('\nquestrade imported')

