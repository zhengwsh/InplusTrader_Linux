# -*- coding: utf-8 -*-
"""
Create on 2017/02/18
@author: vinson zheng
@group: inpluslab
@contact: 1530820222@qq.com
"""

import sys, os
import datetime
import numpy as np
import pymongo
from pymongo import MongoClient
import talib as ta
import plot as iplot

import matplotlib.colors as colors
import matplotlib.dates as mdates
from matplotlib.dates import date2num
import matplotlib.ticker as mticker
import matplotlib.mlab as mlab
import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager

from matplotlib.collections import LineCollection, PolyCollection
from matplotlib.lines import Line2D, TICKLEFT, TICKRIGHT
from matplotlib.patches import Rectangle
from matplotlib.transforms import Affine2D


class DrawDailyK(object):
    """docstring for DrawDailyK"""
    def __init__(self):
        self.conn = MongoClient('172.18.181.134', 27017)
        self.Symbol_Db = self.conn.ifTrader_Symbol_Db
        self.Daily_Db = self.conn.ifTrader_Daily_Db
        #self.OneMin_Db = self.conn.ifTrader_1Min_Db
        #self.Tick_Db = self.conn.ifTrader_Tick_Db


    def fetch_data(self, ticker, start=None, end=None):
        self.ticker = ticker
        self.today = datetime.date.today()
        self.end = self.today.strftime("%Y-%m-%d") if end is None else end
        self.start = (self.today-datetime.timedelta(days=180)).strftime("%Y-%m-%d") if start is None else start
        
        self.startdate = datetime.datetime.strptime(self.start, "%Y-%m-%d")
        self.enddate = datetime.datetime.strptime(self.end, "%Y-%m-%d")


        flt = {'date' : {'$gte':self.start, '$lt':self.end}}
        self.r = self.Daily_Db[self.ticker].find(flt).sort("date",pymongo.ASCENDING)


    def draw(self):
        plt.rc('axes', grid=True)
        plt.rc('grid', color='0.75', linestyle='-', linewidth=0.5)
        
        
        #fig, (ax2, ax3, ax1) = plt.subplots(3, 1)
        fig, ax2 = plt.subplots(1, 1)
        fig.set_facecolor('gray')
        ax2.set_facecolor('#d5d5d5')
        ax2t = ax2.twinx()
        #set(gca, 'Units', 'normalized', 'Position', [0.505 0.505 0.495 0.495])
        plt.subplots_adjust(0.05, 0.05, 0.95, 0.95)

        #-----------------------------------
        kwidth = 0.4
        OFFSET = kwidth / 2.0
        alpha = 1.0
        lines = []
        patches = []
        colorup = 'r'
        colordown = 'g'
        dateL = []
        openL = []
        highL = []
        lowL = []
        closeL = []
        volumeL = []
        amountL = []
        for daybar in self.r:
            date = datetime.datetime.strptime(daybar['date'], "%Y-%m-%d")
            t = date2num(date)
            open = float(daybar['open'])
            high = float(daybar['high'])
            low = float(daybar['low'])
            close = float(daybar['close'])
            volume = float(daybar['volume'])
            amount = float(daybar['amount'])
            dateL.append(t)
            closeL.append(close)
            volumeL.append(volume)

            if close >= open:
                color = colorup
                lower = open
                height = close - open
            else:
                color = colordown
                lower = close
                height = open - close

            vline = Line2D(
                xdata=(t, t), ydata=(low, high),
                color=color,
                linewidth=0.5,
                antialiased=True,
            )

            rect = Rectangle(
                xy=(t - OFFSET, lower),
                width=kwidth,
                height=height,
                facecolor=color,
                edgecolor=color,
            )
            
            rect.set_alpha(alpha)

            lines.append(vline)
            patches.append(rect)
            ax2.add_line(vline)
            ax2.add_patch(rect)

        ax2.autoscale_view()
        ax2.xaxis_date()
        ax2.set_title('%s DAILY K-LINE' % self.ticker)


        dateL = np.array(dateL)
        openL = np.array(openL)
        highL = np.array(highL)
        lowL = np.array(lowL)
        closeL = np.array(closeL)
        volumeL = np.array(volumeL)
        amountL = np.array(amountL)

        vmax = volumeL.max()
        poly = ax2t.fill_between(dateL, volumeL, 0, label='Volume', facecolor='darkgoldenrod', edgecolor='darkgoldenrod')
        ax2t.xaxis_date()
        ax2t.set_ylim(0, 5*vmax)
        ax2t.set_yticks([])

        ma5 = ta.SMA(closeL, 5)
        ma30 = ta.SMA(closeL, 30)
        
        linema5, = ax2.plot(dateL, ma5, color='blue', lw=2, label='SMA (5)')
        linema30, = ax2.plot(dateL, ma30, color='red', lw=2, label='SMA (30)')
        props = font_manager.FontProperties(size=10)
        leg = ax2.legend(loc='upper right', shadow=True, fancybox=True, prop=props)
        leg.get_frame().set_alpha(0.5)

        plt.show()
        
        '''
        s = '%s O:%1.2f H:%1.2f L:%1.2f C:%1.2f, V:%1.1fM Chg:%+1.2f' % (
            dateL[-1],
            openL[-1], lastL[-1],
            lowL[-1], closeL[-1],
            volumeL[-1],
            closeL[-1] - openL[-1])
        t4 = ax2.text(0.3, 0.9, s, transform=ax2.transAxes, fontsize=textsize)
        '''
        '''
        #ax3.set_yticks([])
        # turn off upper axis tick labels, rotate the lower ones, etc
        for ax in ax1, ax2, ax2t, ax3:
            if ax != ax3:
                for label in ax.get_xticklabels():
                    label.set_visible(False)
            else:
                for label in ax.get_xticklabels():
                    label.set_rotation(30)
                    label.set_horizontalalignment('right')

            ax.fmt_xdata = mdates.DateFormatter('%Y-%m-%d')


        class MyLocator(mticker.MaxNLocator):
            def __init__(self, *args, **kwargs):
                mticker.MaxNLocator.__init__(self, *args, **kwargs)

            def __call__(self, *args, **kwargs):
                return mticker.MaxNLocator.__call__(self, *args, **kwargs)

        # at most 5 ticks, pruning the upper and lower so they don't overlap
        # with other ticks
        #ax2.yaxis.set_major_locator(mticker.MaxNLocator(5, prune='both'))
        #ax3.yaxis.set_major_locator(mticker.MaxNLocator(5, prune='both'))

        ax2.yaxis.set_major_locator(MyLocator(5, prune='both'))
        ax3.yaxis.set_major_locator(MyLocator(5, prune='both'))
        '''




# setup application
if __name__ == '__main__':
    dt = DrawDailyK()
    if len(sys.argv) > 2:
        dt.fetch_data(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        dt.fetch_data(sys.argv[1])
    dt.draw()

    # python drawDK.py 600048 2017-01-01 2017-02-20
