# -*- coding: utf-8 -*-
"""
Created on Tue May 01 00:23:45 2018

@author: A
Note: TAKE THIS INTO ACCOUNT THE LEAST, AFTER INDICATORS
Analyze a specific stock: what are the chances stock goes up or down (next day, next week, next month, next 3 months, next 4 months)

Ideas:
Multiple stocks watchlist graphs
- after flat/squeeze (low st. dev.) (slow decrease or slow increase)
- after peaks or dips (find max/min peaks and their dates), will it go up or down. (probably best in short term)
- calculate companies' eps, pe, yield. compare with sector average
- when to sell?
"""
import sys, os, csv
if os.name == 'nt':
    sys.path.append('C:/Users/A/Documents/K/Ongoing Projects/Investments/Questrade_Wrapper/src/')
elif os.name == 'posix':
    sys.path.append('/mnt/a_drive/investments/Questrade_Wrapper/src/')
import datetime, pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from numpy.polynomial.polynomial import polyfit
import matplotlib.dates as mdates
import numpy as np
import questrade
# import src.questrade as questrade


def csv_tolist(filename='C:/Users/A/Downloads/quotes.csv'):
    # import csv symbols to list
    csv_obj = csv.reader(open(filename, 'r'))
    symbs = []
    for row in csv_obj:
        symbs.append(row[0])
    symbs = symbs[1:]
    return symbs

def select_start(years=0, months=0, weeks=0, days=0, hours=0):
    days += int(years*365)
    days += int(months*30)
    start = datetime.datetime.now() - datetime.timedelta(weeks=weeks, days=days, hours=hours)
    datestring = start.strftime('%Y-%m-%d') + ' to today'
    return datestring

def create_fig():
    # create figure
    fig = plt.figure() # tight_layout=True, figsize=(8,8)
    gs = GridSpec(4, 3, figure=fig)
    ax1 = fig.add_subplot(gs[0:2, 0])
    ax2 = fig.add_subplot(gs[2, 0])
    ax3 = fig.add_subplot(gs[3, 0])
    
    ax4 = fig.add_subplot(gs[0:2, 1])
    ax5 = fig.add_subplot(gs[2, 1])
    ax6 = fig.add_subplot(gs[3, 1])
    
    ax7 = fig.add_subplot(gs[0:2, 2])
    ax8 = fig.add_subplot(gs[2, 2])
    ax9 = fig.add_subplot(gs[3, 2])
    return ax1, ax2, ax3, ax4, ax5, ax6, ax7, ax8, ax9    

class analyze_stock(questrade.QuestradeToken):
    # create a class for the stock
    def __init__(self, direct_token, symb, datestring, interval, periods, change, delta, span, span_volume):
        super().__init__(direct_token)
        self.symb = symb
        self.datestring = datestring
        self.interval = interval
        self.df, self.start_date, self.end_date = self.df_candles(self.datestring, self.interval)
        self.periods = periods
        self.change = change
        self.delta = delta
        self.span = span
        self.span_volume = span_volume
        
    
    def df_candles(self, datestring, interval):
        # get candles data and modify it for whatever use
        data = self.candles(self.symb, datestring='beginning to today', interval=interval) # grab max data as possible
        df = pd.DataFrame(data) # convert to dataframe
        df['mid_oc'] = (df['open'] + df['close'])/2
        df['start2'] = pd.to_datetime(df['start']) # convert from isoformat to datetime
        df['end2'] = pd.to_datetime(df['end'])
            
        # restrict daterange from initial df
        resp = self._daterange(datestring) 
        
        start_date = pd.to_datetime(resp['startTime'])
        end_date = pd.to_datetime(resp['endTime'])
        mask = (df['start2'] > start_date) & (df['start2'] < end_date) 
        df2 = df.loc[mask]
        df2 = df2.reset_index(drop=True)
        return df2, start_date, end_date

    def fit_maxmin(self, periods):
        # fit max/min linear lines
        t = int(len(self.df)/periods)
        df_maxmin = []
        for j in range(periods):
            df_section = list(self.df['mid_oc'][j*t:(j+1)*t])
            df_maxmin.append([self.df['start2'][j*t+df_section.index(max(df_section))], max(df_section), self.df['start2'][j*t+df_section.index(min(df_section))], min(df_section)])
        df_maxmin = pd.DataFrame(df_maxmin)
        df_maxmin.columns = ['date_max', 'max', 'date_min', 'min']
        return df_maxmin

    def plot_maxmin(self, ax1, markers=False):
        # give data points and fit values, plot linear fit to respective, already existing plot
        b, m = polyfit(mdates.date2num(self.maxmin['date_max']), self.maxmin['max'], 1)
        ax1.plot(mdates.date2num(self.maxmin['date_max']), m*mdates.date2num(self.maxmin['date_max'])+b, color='red', linestyle=':', label='Max/min trendlines')
        b, m = polyfit(mdates.date2num(self.maxmin['date_min']), self.maxmin['min'], 1)
        ax1.plot(mdates.date2num(self.maxmin['date_min']), m*mdates.date2num(self.maxmin['date_min'])+b, color='red', linestyle=':')
        
        if markers == True:
            ax1.plot(mdates.date2num(self.maxmin['date_max']), self.maxmin['max'], color='gray', marker='o', linestyle='None')
            ax1.plot(mdates.date2num(self.maxmin['date_min']), self.maxmin['min'], color='gray', marker='o', linestyle='None')
        return ax1
    
    def bigchange(self, change, delta):
        # given % change, what is success rate of that days' buy-in after delta intervals to be positive
        # this only works for specific intervals, how to choose # of days/hours
        # picking OHLC values for sucess rate, which one is best? Idk        
        cols = ['VWAP', 'close', 'high', 'low', 'open', 'volume', 'mid_oc']
        # price change low/open and high/open
        percent_change = 1 + float(change)/100
        if change < 0:
            ids = self.df[self.df['low']/self.df['open'] < percent_change] # change from open to low
        elif change > 0:
            ids = self.df[self.df['high']/self.df['open'] > percent_change] 
        ids = ids.reset_index()
        # calculate whether after delta after, if value is positive. -change = open before/after, +change = close before/after. Does this matter?
        day_change = ids['start2'] + datetime.timedelta(days=delta)
        current_guess = []
        ids_after2 = pd.DataFrame()
        for ea in range(len(day_change)):
            while (self.df['start2'].isin([day_change.iloc[ea]]).any() or day_change.iloc[ea] >= self.end_date) == False: # check if day is on weekend/holiday/non-existing day
                day_change_new = day_change.iloc[ea] + datetime.timedelta(days=1)
                day_change.iloc[ea] = day_change_new
            if day_change.iloc[ea] >= self.end_date: # days don't exist for these, time for your guess
                print('%s guess: %s' %(self.symb, day_change.iloc[ea]))
                current_guess.append(day_change.iloc[ea])
            ids_after2 = ids_after2.append(self.df[self.df['start2']==day_change.iloc[ea]])
        ids_after = self.df[self.df['start2'].isin(day_change)]
        ids_after = ids_after.reset_index()
#        ids_diff = ids_after[cols] - ids[cols] # take difference of before and after
        ids_after2 = ids_after2.reset_index()
        ids_diff = ids_after2[cols] - ids[cols]
        # determine success rate
        if change < 0:
            rate_success = sum(ids_diff['mid_oc']>0)/float(len(ids_diff)) # % rate, negative change, look at opening difference
            ids_success = ids[ids_diff['mid_oc']>0]
        elif change > 0:
            rate_success = sum(ids_diff['close']>0)/float(len(ids_diff)) # % rate, positive change, look at closing difference
            ids_success = ids[ids_diff['close']>0]
        print(' %s rate: %.4f, %d/%d' %(self.symb, rate_success, len(ids_success), len(ids_diff)))
        ids_guess = ids[len(ids)-len(current_guess):]
        return ids, ids_success, ids_guess

    def plot_bigchange(self, ax1):
        # plot bigchange
        self.df.plot('start2', 'mid_oc', ax=ax1, title='%s: %.2f, %d/%d' %(self.symb, len(self.ids_success)/float(len(self.ids)), len(self.ids_success), len(self.ids)), label=self.symb)
#        self.df.plot('start2', 'high', ax=ax1, marker='.', color='y', linestyle='None', markersize=3)
#        self.df.plot('start2', 'low', ax=ax1, marker='.', color='r', linestyle='None', markersize=3)
        self.ids.plot('start2', 'mid_oc', ax=ax1, marker='o', color='orange', linestyle='None', label='-5% week change')
#        try:
#            self.ids_success.plot('start2', 'mid_oc', ax=ax1, marker='.', color='green', linestyle='None')
#            self.ids_guess.plot('start2', 'mid_oc', ax=ax1, marker='.', color='r', linestyle='None')
#        except:
#            print('')    
        ax1.get_legend().remove()     
        return ax1
    
    def smooth_ewm(self, span, y='price'):
        if y == 'price':
            ema = self.df['mid_oc'].ewm(span=span, adjust=False).mean()
#        print ema
        elif y == 'volume':
            ema = self.df['volume'].ewm(span=span, adjust=False).mean()
        return ema
        
    def plot_ewm(self, ema, ax):
        ax.plot(self.df['start2'], ema, color='#9467bd', linestyle=':', linewidth=2, label="EMA")
        return ax
    
    def run_analysis(self):
        self.maxmin = self.fit_maxmin(self.periods)
        self.ids, self.ids_success, self.ids_guess = self.bigchange(self.change, self.delta)
        self.ema_price = self.smooth_ewm(self.span)
        self.ema_volume = self.smooth_ewm(self.span_volume, y='volume')
        return self
    
    def run_plot(self, ax1, ax2, ax3):
        self = self.run_analysis()
        ax1 = self.plot_bigchange(ax1)
        ax1 = self.plot_maxmin(ax1)
        ax1 = self.plot_ewm(self.ema_price, ax1)
        ax3 = self.plot_ewm(self.ema_volume, ax3)
        ax3.plot(self.df['start2'], self.df['volume'], linestyle='none', marker='.')
        
        self.overall_indicator(ax2)
        
        for ax in [ax1, ax2, ax3]:
            ax.set_xlim(self.start_date, self.end_date)
            ax.set_xlabel('')
        for ax in [ax1, ax2]:
            ax.get_xaxis().set_ticks([])
            
    def overall_indicator(self, ax):
        # algo to determine overall indicator
        smoothed = self.moving_average(self.df['mid_oc'], n=3)
        ema = smoothed.ewm(span=self.span, adjust=False).mean()
        ema_diff = np.diff(ema) * self.df['volume'][1:] # normalize to volume: high v*high p = load off (getting profits), low v*low p = possible increase (no more hype or want to keep), high v*low p = load off (cutting losses), low v*high p = edging (people scared of dip or want to keep)
        ema_diff = ema_diff/abs(ema_diff).max()
        #ema_diff = stock1.df['mid_oc'] - ema2
        ax.plot(self.df['start2'][1:], ema_diff)
        ax.set_xlim(min(self.df['start2'][1:]), max(self.df['start2'][1:]))
        ax.axhline(y=0, linestyle='--', color='gray')
        return ax
    
    def moving_average(self, a, n=3):
        ret = a.cumsum()
        ret = (ret - ret.shift(n)) / n
        return ret

#####################
##### MAIN CODE #####
#####################
# main parameters
direct_token = 'C:/Users/A/Documents/K/Ongoing Projects/Investments/src/'
#token = questrade.calltoken(direct_token)
#symbs = ['dbx', 'zqq.to']

interval = 'OneWeek'
periods = 4 # daterange/periods for all analyses
span, span_volume = 10, 10 # for ewm 
change, delta = -5, 8 # for bigchange: change, after x periods

stock1 = analyze_stock(direct_token, 'TD.TO', select_start(years=2), interval, periods, change, delta, span, span_volume) # symb, datestring, interval, periods, change, delta, span, span_volume

stock1 = stock1.run_analysis()
#stock1.run_plot(ax1, ax2, ax3)

fig = plt.figure(tight_layout=True, figsize=(8,4*3))
ax1 = fig.add_subplot(311)
ax1 = stock1.plot_bigchange(ax1)
ax1 = stock1.plot_maxmin(ax1)
ax1 = stock1.plot_ewm(stock1.ema_price, ax1)
ax1.set_xlabel('')
ax1.set_xticklabels([])
ax1.set_ylabel('Market Price')
ax1.set_title('Market Price vs. Date')
ax1.legend()

#fig = plt.figure(tight_layout=True, figsize=(8,4))
ax2 = fig.add_subplot(312)
ax2.bar(stock1.df['start2'], stock1.df['volume'], width=3)
ax2 = stock1.plot_ewm(stock1.ema_volume, ax2)
ax2.set_xlim(min(stock1.df['start2']), max(stock1.df['start2']))
#ax2.tick_params(labelrotation=45)
ax2.set_xticklabels([])
#ax2.set_xlabel('')
ax2.set_ylabel('Volume')
ax2.set_title('Volume vs. Date')
ax2.legend()


#fig = plt.figure(tight_layout=True, figsize=(8,4))
ax3 = fig.add_subplot(313)
ax3 = stock1.overall_indicator(ax3)
ax3.tick_params(labelrotation=45)
ax3.set_xlabel('Date')
ax3.set_ylabel('Dollars')
ax3.set_title('Dollars vs. Date')


'''
# LT (one-two years, OneWeek)
datestring_lt = select_start(years=1)
interval_lt = 'OneWeek'
change_lt, delta_lt = 5, 8 # % change, after x periods
span_lt = 20

# MT (three-ten months, OneDay)
datestring_mt = select_start(months=6)
interval_mt = 'OneDay'
change_mt, delta_mt = 3, 14
span_mt = 60

# ST (weeks-two months, OneHour)
datestring_st = select_start(months=2)
interval_st = 'TwoHours'
change_st, delta_st = 3, 7 # % change, after x periods
span_st = 80

for sym in symbs:
    ax1, ax2, ax3, ax4, ax5, ax6, ax7, ax8, ax9  = create_fig()
    
    stock1 = analyze_stock(sym, datestring_lt, interval_lt, periods_lt, change_lt, delta_lt, span_lt, span_volume_lt)
    stock1.run_plot(ax1, ax2, ax3)
    
    stock2 = analyze_stock(sym, datestring_mt, interval_mt, periods_mt, change_mt, delta_mt, span_mt, span_volume_mt)
    stock2.run_plot(ax4, ax5, ax6)
    
    stock3 = analyze_stock(sym, datestring_st, interval_st, periods_st, change_st, delta_st, span_st, span_volume_st)
    stock3.run_plot(ax7, ax8, ax9)    
'''


# bollinger bands, parabolic stop and reverse, relative stregnth index, stocastic slow, big volume indicator: MACD with histogram


plt.show()

'''
OneMinute = 'OneMinute'
TwoMinutes = 'TwoMinutes'
ThreeMinutes = 'ThreeMinutes'    
FourMinutes = 'FourMinutes'
FiveMinutes = 'FiveMinutes'
TenMinutes = 'TenMinutes'
FifteenMinutes = 'FifteenMinutes'
TwentyMinutes = 'TwentyMinutes'
HalfHour = 'HalfHour'
OneHour = 'OneHour'
TwoHours = 'TwoHours'
FourHours = 'FourHours'
OneDay = 'OneDay'
OneWeek = 'OneWeek'
OneMonth = 'OneMonth'
OneYear = 'OneYear'
'''
