# -*- coding: utf-8 -*-
"""
Create on 2017/02/18
@author: vinson zheng
@group: inpluslab
@contact: 1530820222@qq.com
"""

import sys, os
import pickle
import math
import datetime
import numpy as np
import pandas as pd
import talib as ta
import pymongo
from pymongo import MongoClient
import matplotlib

# 这个要紧跟在 import matplotlib 之后，而且必须安装了 wxpython 2.8 才行。
matplotlib.use("WXAgg", warn=True)  

import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, MultipleLocator, LogLocator, FuncFormatter, NullFormatter, LogFormatter

reload(sys)
sys.setdefaultencoding("utf-8")

conn = MongoClient('172.18.181.134')
Symbol_Db = conn.ifTrader_Symbol_Db
Daily_Db = conn.ifTrader_Daily_Db
OneMin_Db = conn.ifTrader_1Min_Db
Tick_Db = conn.ifTrader_Tick_Db

def Plot(useexpo=True):
    # fetch data
    dateL = []
    openL = []
    highL = []
    lowL = []
    closeL = []
    volumeL = []
    amountL = []

    ticker = '600048'
    start = '2016-01-01'
    end = '2017-02-17'
    today = datetime.date.today()
    end = today.strftime("%Y-%m-%d") if end is None else end
    start = (today-datetime.timedelta(days=180)).strftime("%Y-%m-%d") if start is None else start

    flt = {'date' : {'$gte':start, '$lt':end}}
    r = Daily_Db[ticker].find(flt).sort("date",pymongo.ASCENDING)

    for daybar in r:
        dateL.append(daybar['date'])
        openL.append(float(daybar['open']))
        highL.append(float(daybar['high']))
        lowL.append(float(daybar['low']))
        closeL.append(float(daybar['close']))
        volumeL.append(float(daybar['volume']))
        amountL.append(float(daybar['amount']))

    dateL = np.array(dateL)
    openL = np.array(openL)
    highL = np.array(highL)
    lowL = np.array(lowL)
    closeL = np.array(closeL)
    volumeL = np.array(volumeL)
    amountL = np.array(amountL)
    ma1 = ta.SMA(closeL, 2)
    ma5 = ta.SMA(closeL, 5)
    ma30 = ta.SMA(closeL, 30)


    pdata = pd.DataFrame({u'日期':dateL, u'开盘':openL, u'最高':highL, u'最低':lowL, u'收盘':closeL, u'成交量':volumeL, u'1日均':ma1, u'5日均':ma5, u'30日均':ma30})
    print pdata.head(2)

    #   计算图片的尺寸（单位英寸）
    #==================================================================================================================================================
    length= len(pdata[u'日期'])       # 所有数据的长度，就是天

    
    highest_price= max(pdata[u'最高'])    # 最高价
    lowest_price= min( [plow for plow in pdata[u'最低'] if plow != None] )    # 最低价

    yhighlim_price= round(highest_price+1, 2) # K线子图 Y 轴最大坐标
    ylowlim_price=  round(lowest_price-1, 2)  # K线子图 Y 轴最小坐标

    print yhighlim_price
    print ylowlim_price
    xfactor= 10.0/230.0 # 一条 K 线的宽度在 X 轴上所占距离（英寸）
    yfactor= 0.3    # Y 轴上每一个距离单位的长度（英寸），这个单位距离是线性坐标和对数坐标通用的
     
    if useexpo: # 要使用对数坐标
        expbase= 1.1    # 底数，取得小一点，比较接近 1。股价 3 元到 4 元之间有大约 3 个单位距离
        ymulti_price= math.log(yhighlim_price, expbase) - math.log(ylowlim_price, expbase)  # 价格在 Y 轴上的 “份数”
    else:
        ymulti_price= (yhighlim_price - ylowlim_price) / 100    # 价格在 Y 轴上的 “份数”
     
    ymulti_vol= 3.0     # 成交量部分在 Y 轴所占的 “份数”
    ymulti_top= 0.2     # 顶部空白区域在 Y 轴所占的 “份数”
    ymulti_bot= 0.8     # 底部空白区域在 Y 轴所占的 “份数”
 
    xmulti_left= 10.0   # 左侧空白区域所占的 “份数”
    xmulti_right= 3.0   # 右侧空白区域所占的 “份数”
 
    xmulti_all= length + xmulti_left + xmulti_right
    xlen_fig= xmulti_all * xfactor      # 整个 Figure 的宽度
    ymulti_all= ymulti_price + ymulti_vol + ymulti_top + ymulti_bot
    ylen_fig= ymulti_all * yfactor      # 整个 Figure 的高度
     
    rect_1= (xmulti_left/xmulti_all, (ymulti_bot+ymulti_vol)/ymulti_all, length/xmulti_all, ymulti_price/ymulti_all)    # K线图部分
    rect_2= (xmulti_left/xmulti_all, ymulti_bot/ymulti_all, length/xmulti_all, ymulti_vol/ymulti_all)   # 成交量部分
 

    #   建立 Figure 对象
    #==================================================================================================================================================
    figfacecolor= 'white'
    figedgecolor= 'black'
    figdpi= 600
    figlinewidth= 1.0
 
    figobj= plt.figure(figsize=(xlen_fig, ylen_fig), dpi=figdpi, facecolor=figfacecolor, edgecolor=figedgecolor, linewidth=figlinewidth) # Figure 对象
 
    #==================================================================================================================================================
    #==================================================================================================================================================
    #=======    成交量部分
    #==================================================================================================================================================
    #==================================================================================================================================================
 
    #   添加 Axes 对象
    #==================================================================================================================================================
    axes_2= figobj.add_axes(rect_2, facecolor='black')
    axes_2.set_axisbelow(True)  # 网格线放在底层
 
    #   改变坐标线的颜色
    #==================================================================================================================================================
    for child in axes_2.get_children():
        if isinstance(child, matplotlib.spines.Spine):
            child.set_color('lightblue')
 
    #   得到 X 轴 和 Y 轴 的两个 Axis 对象
    #==================================================================================================================================================
    xaxis_2= axes_2.get_xaxis()
    yaxis_2= axes_2.get_yaxis()
 
    #   设置两个坐标轴上的 grid
    #==================================================================================================================================================
    xaxis_2.grid(True, 'major', color='0.3', linestyle='solid', linewidth=0.2)
    xaxis_2.grid(True, 'minor', color='0.3', linestyle='dotted', linewidth=0.1)
 
    yaxis_2.grid(True, 'major', color='0.3', linestyle='solid', linewidth=0.2)
    yaxis_2.grid(True, 'minor', color='0.3', linestyle='dotted', linewidth=0.1)
 
 
 
    #==================================================================================================================================================
    #=======    绘图
    #==================================================================================================================================================
    xindex= np.arange(length)    # X 轴上的 index，一个辅助数据
 
    zipoc= zip(pdata[u'开盘'], pdata[u'收盘'])
    up=   np.array( [ True if po < pc and po != None else False for po, pc in zipoc] )        # 标示出该天股价日内上涨的一个序列
    down= np.array( [ True if po > pc and po != None else False for po, pc in zipoc] )        # 标示出该天股价日内下跌的一个序列
    side= np.array( [ True if po == pc and po != None else False for po, pc in zipoc] )      # 标示出该天股价日内走平的一个序列
 
 
 
    volume= pdata[u'成交量']
    rarray_vol= np.array(volume)
    volzeros= np.zeros(length)   # 辅助数据
 
    # XXX: 如果 up/down/side 各项全部为 False，那么 vlines() 会报错。
    if True in up:
        axes_2.vlines(xindex[up], volzeros[up], rarray_vol[up], color='red', linewidth=3.0, label='_nolegend_')
    if True in down:
        axes_2.vlines(xindex[down], volzeros[down], rarray_vol[down], color='green', linewidth=3.0, label='_nolegend_')
    if True in side:
        axes_2.vlines(xindex[side], volzeros[side], rarray_vol[side], color='0.7', linewidth=3.0, label='_nolegend_')
     
 
 
    #   设定 X 轴坐标的范围 
    #==================================================================================================================================================
    axes_2.set_xlim(-1, length)
 
 
 
    #   设定 X 轴上的坐标
    #==================================================================================================================================================
    #datelist= [ datetime.date(int(ys), int(ms), int(ds)) for ys, ms, ds in [ dstr.split('-') for dstr in pdata[u'日期'] ] ]
    datelist= [ datetime.datetime.strptime(dstr, "%Y-%m-%d") for dstr in pdata[u'日期'] ]
    
    # 确定 X 轴的 MajorLocator
    mdindex= [] # 每个月第一个交易日在所有日期列表中的 index
    years= set([d.year for d in datelist])  # 所有的交易年份
 
    for y in sorted(years):     
        months= set([d.month for d in datelist if d.year == y])     # 当年所有的交易月份
        for m in sorted(months):
            monthday= min([dt for dt in datelist if dt.year==y and dt.month==m])    # 当月的第一个交易日
            mdindex.append(datelist.index(monthday))
 
    xMajorLocator= FixedLocator(np.array(mdindex))
 
    # 确定 X 轴的 MinorLocator
    wdindex= [] # 每周第一个交易日在所有日期列表中的 index
    for d in datelist:
        if d.weekday() == 0: wdindex.append(datelist.index(d))
 
    xMinorLocator= FixedLocator(np.array(wdindex))
 
    # 确定 X 轴的 MajorFormatter 和 MinorFormatter
    def x_major_formatter_2(idx, pos=None):
        print idx
        return datelist[int(idx)].strftime('%Y-%m-%d')

    def x_minor_formatter_2(idx, pos=None):
        return datelist[idx].strftime('%m-%d')
 
    xMajorFormatter= FuncFormatter(x_major_formatter_2)
    xMinorFormatter= FuncFormatter(x_minor_formatter_2)
 
    # 设定 X 轴的 Locator 和 Formatter
    xaxis_2.set_major_locator(xMajorLocator)
    xaxis_2.set_major_formatter(xMajorFormatter)
 
    xaxis_2.set_minor_locator(xMinorLocator)
    xaxis_2.set_minor_formatter(xMinorFormatter)
 
    # 设定 X 轴主要坐标点与辅助坐标点的样式
    for malabel in axes_2.get_xticklabels(minor=False):
        malabel.set_fontsize(3)
        malabel.set_horizontalalignment('right')
        malabel.set_rotation('30')
 
    for milabel in axes_2.get_xticklabels(minor=True):
        milabel.set_fontsize(2)
        milabel.set_horizontalalignment('right')
        milabel.set_rotation('30')
 
 
 
    #   设定 Y 轴坐标的范围 
    #==================================================================================================================================================
    maxvol= max(volume) # 注意是 int 类型
    axes_2.set_ylim(0, maxvol)
 
 
 
    #   设定 Y 轴上的坐标
    #==================================================================================================================================================
    vollen= len(str(maxvol))
     
    yMajorLocator_2= MultipleLocator(10**(vollen-1))
    yMinorLocator_2= MultipleLocator((10**(vollen-2))*5)
 
    # 确定 Y 轴的 MajorFormatter
    #   def y_major_formatter_2(num, pos=None):
    #       numtable= {'1':u'一', '2':u'二', '3':u'三', '4':u'四', '5':u'五', '6':u'六', '7':u'七', '8':u'八', '9':u'九', }
    #       dimtable= {3:u'百', 4:u'千', 5:u'万', 6:u'十万', 7:u'百万', 8:u'千万', 9:u'亿', 10:u'十亿', 11:u'百亿'}
    #       return numtable[str(num)[0]] + dimtable[vollen] if num != 0 else '0'
 
    def y_major_formatter_2(num, pos=None):
        return int(num)
    yMajorFormatter_2= FuncFormatter(y_major_formatter_2)
 
    # 确定 Y 轴的 MinorFormatter
    #   def y_minor_formatter_2(num, pos=None):
    #       return int(num)
    #   yMinorFormatter_2= FuncFormatter(y_minor_formatter_2)
    yMinorFormatter_2= NullFormatter()
 
    # 设定 X 轴的 Locator 和 Formatter
    yaxis_2.set_major_locator(yMajorLocator_2)
    yaxis_2.set_major_formatter(yMajorFormatter_2)
 
    yaxis_2.set_minor_locator(yMinorLocator_2)
    yaxis_2.set_minor_formatter(yMinorFormatter_2)
 
    # 设定 Y 轴主要坐标点与辅助坐标点的样式
    for malab in axes_2.get_yticklabels(minor=False):
        malab.set_fontsize(3)
 
    for milab in axes_2.get_yticklabels(minor=True):
        milab.set_fontsize(2)
 
 
 
    #==================================================================================================================================================
    #==================================================================================================================================================
    #=======    K 线图部分
    #==================================================================================================================================================
    #==================================================================================================================================================
 
    #   添加 Axes 对象
    #==================================================================================================================================================
    axes_1= figobj.add_axes(rect_1, facecolor='black', sharex=axes_2)
    axes_1.set_axisbelow(True)  # 网格线放在底层
     
    if useexpo:
        axes_1.set_yscale('log', basey=expbase) # 使用对数坐标
 
    #   改变坐标线的颜色
    #==================================================================================================================================================
    for child in axes_1.get_children():
        if isinstance(child, matplotlib.spines.Spine):
            child.set_color('lightblue')
 
    #   得到 X 轴 和 Y 轴 的两个 Axis 对象
    #==================================================================================================================================================
    xaxis_1= axes_1.get_xaxis()
    yaxis_1= axes_1.get_yaxis()
 
    #   设置两个坐标轴上的 grid
    #==================================================================================================================================================
    xaxis_1.grid(True, 'major', color='0.3', linestyle='solid', linewidth=0.2)
    xaxis_1.grid(True, 'minor', color='0.3', linestyle='dotted', linewidth=0.1)
 
    yaxis_1.grid(True, 'major', color='0.3', linestyle='solid', linewidth=0.2)
    yaxis_1.grid(True, 'minor', color='0.3', linestyle='dotted', linewidth=0.1)
 
 
 
    #==================================================================================================================================================
    #=======    绘图
    #==================================================================================================================================================
 
    #   绘制 K 线部分
    #==================================================================================================================================================
    rarray_open= np.array(pdata[u'开盘'])
    rarray_close= np.array(pdata[u'收盘'])
    rarray_high= np.array(pdata[u'最高'])
    rarray_low= np.array(pdata[u'最低'])
 
    # XXX: 如果 up, down, side 里有一个全部为 False 组成，那么 vlines() 会报错。
    if True in up:
        axes_1.vlines(xindex[up], rarray_low[up], rarray_high[up], color='red', linewidth=0.6, label='_nolegend_')
        axes_1.vlines(xindex[up], rarray_open[up], rarray_close[up], color='red', linewidth=3.0, label='_nolegend_')
    if True in down:
        axes_1.vlines(xindex[down], rarray_low[down], rarray_high[down], color='green', linewidth=0.6, label='_nolegend_')
        axes_1.vlines(xindex[down], rarray_open[down], rarray_close[down], color='green', linewidth=3.0, label='_nolegend_')
    if True in side:
        axes_1.vlines(xindex[side], rarray_low[side], rarray_high[side], color='0.7', linewidth=0.6, label='_nolegend_')
        axes_1.vlines(xindex[side], rarray_open[side], rarray_close[side], color='0.7', linewidth=3.0, label='_nolegend_')
 
    #   绘制均线部分
    #==================================================================================================================================================
    rarray_1dayave= np.array(pdata[u'1日均'])
    rarray_5dayave= np.array(pdata[u'5日均'])
    rarray_30dayave= np.array(pdata[u'30日均'])
     
    axes_1.plot(xindex, rarray_1dayave, 'o-', color='white', linewidth=0.1, markersize=0.7, markeredgecolor='white', markeredgewidth=0.1)   # 1日加权均线
    axes_1.plot(xindex, rarray_5dayave, 'o-', color='yellow', linewidth=0.1, markersize=0.7, markeredgecolor='yellow', markeredgewidth=0.1) # 5日均线
    axes_1.plot(xindex, rarray_30dayave, 'o-', color='green', linewidth=0.1, markersize=0.7, markeredgecolor='green', markeredgewidth=0.1)  # 30日均线
 
    #   设定 X 轴坐标的范围 
    #==================================================================================================================================================
    axes_1.set_xlim(-1, length)
 
 
 
    #   先设置 label 位置，再将 X 轴上的坐标设为不可见。因为与 成交量子图 共用 X 轴
    #==================================================================================================================================================
 
    # 设定 X 轴的 Locator 和 Formatter
    xaxis_1.set_major_locator(xMajorLocator)
    xaxis_1.set_major_formatter(xMajorFormatter)
 
    xaxis_1.set_minor_locator(xMinorLocator)
    xaxis_1.set_minor_formatter(xMinorFormatter)
 
    # 将 X 轴上的坐标设为不可见。
    for malab in axes_1.get_xticklabels(minor=False):
        malab.set_visible(False)
 
    for milab in axes_1.get_xticklabels(minor=True):
        milab.set_visible(False)
 
    # 用这一段效果也一样
    #   plt.setp(axes_1.get_xticklabels(minor=False), visible=False)
    #   plt.setp(axes_1.get_xticklabels(minor=True), visible=False)
 
 
 
    #   设定 Y 轴坐标的范围 
    #==================================================================================================================================================
    axes_1.set_ylim(ylowlim_price, yhighlim_price)
 
 
 
    #   设定 Y 轴上的坐标
    #==================================================================================================================================================
     
    if useexpo:
        #   主要坐标点
        #-----------------------------------------------------
        yMajorLocator_1= LogLocator(base=expbase)
         
        yMajorFormatter_1= NullFormatter()
 
        # 设定 X 轴的 Locator 和 Formatter
        yaxis_1.set_major_locator(yMajorLocator_1)
        yaxis_1.set_major_formatter(yMajorFormatter_1)
 
        # 设定 Y 轴主要坐标点与辅助坐标点的样式
        #   for mal in axes_1.get_yticklabels(minor=False):
        #       mal.set_fontsize(3)
 
        #   辅助坐标点
        #-----------------------------------------------------
        minorticks= range(int(ylowlim_price), int(yhighlim_price)+1, 100)
         
        yMinorLocator_1= FixedLocator(np.array(minorticks))
 
        # 确定 Y 轴的 MinorFormatter
        def y_minor_formatter_1(num, pos=None):
            return str(num/100.0) + '0'
 
        yMinorFormatter_1= FuncFormatter(y_minor_formatter_1)
 
        # 设定 X 轴的 Locator 和 Formatter
        yaxis_1.set_minor_locator(yMinorLocator_1)
        yaxis_1.set_minor_formatter(yMinorFormatter_1)
 
        # 设定 Y 轴主要坐标点与辅助坐标点的样式
        for mil in axes_1.get_yticklabels(minor=True):
            mil.set_fontsize(3)
 
    else:   # 如果使用线性坐标，那么只标主要坐标点
        yMajorLocator_1= MultipleLocator(100)
 
        def y_major_formatter_1(num, pos=None):
            return str(num/100.0) + '0'
 
        yMajorFormatter_1= FuncFormatter(y_major_formatter_1)
 
        # 设定 Y 轴的 Locator 和 Formatter
        yaxis_1.set_major_locator(yMajorLocator_1)
        yaxis_1.set_major_formatter(yMajorFormatter_1)
 
        # 设定 Y 轴主要坐标点与辅助坐标点的样式
        for mal in axes_1.get_yticklabels(minor=False):
            mal.set_fontsize(3)
 
 
    #   保存图片
    #==================================================================================================================================================
    #figobj.savefig(figpath, dpi=figdpi, facecolor=figfacecolor, edgecolor=figedgecolor, linewidth=figlinewidth)
    plt.show()
 
 
 
if __name__ == '__main__':
    Plot(useexpo=False)