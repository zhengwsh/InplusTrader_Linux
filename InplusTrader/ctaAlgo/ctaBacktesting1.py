# encoding: UTF-8

'''
本文件中包含的是CTA模块的回测引擎，回测引擎的API和CTA引擎一致，
可以使用和实盘相同的代码进行回测。
'''
from __future__ import division
from itertools import product
import copy
import os
import sys
import re
import csv
import time
import multiprocessing
import json
import pymongo
import threading

from datetime import datetime
from collections import OrderedDict
from progressbar import ProgressBar
from collections import deque

from ctaBase import *

from vtConstant import *
from vtGateway import VtOrderData, VtTradeData
from vtFunction import loadMongoSetting


########################################################################
class BacktestingEngine(object):
    """
    CTA回测引擎
    函数接口和策略引擎保持一样，
    从而实现同一套代码从回测到实盘。
    增加双合约回测功能
    增加快速慢速切换功能（挂单策略建议使用快速模式）
    """

    TICK_MODE = 'tick'
    BAR_MODE = 'bar'
    bufferSize = 1000
    Version = 20170726

    # ----------------------------------------------------------------------
    def __init__(self, optimism=False):
        """Constructor"""
        # 本地停止单编号计数
        self.stopOrderCount = 0
        # stopOrderID = STOPORDERPREFIX + str(stopOrderCount)

        # 本地停止单字典
        # key为stopOrderID，value为stopOrder对象
        self.stopOrderDict = {}  # 停止单撤销后不会从本字典中删除
        self.workingStopOrderDict = {}  # 停止单撤销后会从本字典中删除

        # 回测相关
        self.strategy = None  # 回测策略
        self.vtSymbol = None
        self.vtSymbol1 = None
        self.mode = self.BAR_MODE  # 回测模式，默认为K线
        self.shfe = True  # 上期所
        self.fast = False  # 是否支持排队

        self.plot = True
        self.plotfile = False
        self.optimism = False

        self.leverage = 0.07 # 杠杠比率
        self.leverage1 = 0.07 # 杠杠比率
        self.slippage = 0  # 回测时假设的滑点
        self.slippage1 = 0  # 回测时假设的滑点
        self.rate = 0  # 回测时假设的佣金比例（适用于百分比佣金）
        self.rate1 = 0  # 回测时假设的佣金比例（适用于百分比佣金）
        self.size = 1  # 合约大小，默认为1
        self.size1 = 1  # 合约大小，默认为1
        self.mPrice = 1  # 最小价格变动，默认为1
        self.mPrice1 = 1  # 最小价格变动，默认为1

        self.dbClient = None  # 数据库客户端
        self.mcClient = None  # 数据库客户端
        self.dbCursor = None  # 数据库指针
        self.dbCursor1 = None  # 数据库指针

        self.backtestingData = deque([])  # 回测用的数据
        self.backtestingData1 = deque([])  # 回测用的数据

        self.dataStartDate = None  # 回测数据开始日期，datetime对象
        self.dataEndDate = None  # 回测数据结束日期，datetime对象
        self.strategyStartDate = None  # 策略启动日期（即前面的数据用于初始化），datetime对象

        self.limitOrderDict = OrderedDict()  # 限价单字典
        self.workingLimitOrderDict = OrderedDict()  # 活动限价单字典，用于进行撮合用
        self.limitOrderCount = 0  # 限价单编号

        self.limitOrderDict1 = OrderedDict()  # 合约2限价单字典
        self.workingLimitOrderDict1 = OrderedDict()  # 合约2活动限价单字典，用于进行撮合用

        self.tradeCount = 0  # 成交编号
        self.tradeDict = OrderedDict()  # 成交字典

        self.tradeCount1 = 0  # 成交编号1
        self.tradeDict1 = OrderedDict()  # 成交字典1

        self.tradeSnap = OrderedDict()  # 主合约市场快照
        self.tradeSnap1 = OrderedDict()  # 副合约市场快照

        self.trade1Snap = OrderedDict()  # 主合约市场快照1
        self.trade1Snap1 = OrderedDict()  # 副合约市场快照1

        self.i = 0  # 主合约数据准备进度
        self.j = 0  # 副合约数据准备进度
        self.dataClass = None
        self._dataClass = None

        self.logList = []  # 日志记录

        self.orderPrice = {}  # 主合约限价单价格
        self.orderVolume = {}  # 副合约限价单盘口

        self.orderPrice1 = {}  # 限价单价格
        self.orderVolume1 = {}  # 限价单盘口

        # 当前最新数据，用于模拟成交用
        self.tick = None
        self.tick1 = None
        self.lasttick = None
        self.lasttick1 = None
        self.bar = None
        self.bar1 = None
        self.lastbar = None
        self.lastbar1 = None
        self.dt = None  # 最新的时间

    # ----------------------------------------------------------------------
    def setStartDate(self, startDate='20170501'):
        """设置回测的启动日期
           支持两种日期模式"""
        if len(startDate) == 8:
            self.dataStartDate = datetime.strptime(startDate, '%Y%m%d')
        elif len(startDate) == 10:
            self.dataStartDate = datetime.strptime(startDate, '%Y-%m-%d')
        else:
            self.dataStartDate = datetime.strptime(startDate, '%Y-%m-%d %H:%M:%S') #'%Y%m%d %H:%M:%S'

    # ----------------------------------------------------------------------
    def setEndDate(self, endDate='20170501'):
        """设置回测的结束日期
           支持两种日期模式"""
        if len(endDate) == 8:
            self.dataEndDate = datetime.strptime(endDate, '%Y%m%d')
        elif len(endDate) == 10:
            self.dataEndDate = datetime.strptime(endDate, '%Y-%m-%d')
        else:
            self.dataEndDate = datetime.strptime(endDate, '%Y-%m-%d %H:%M:%S')

    # ----------------------------------------------------------------------
    def setBacktestingMode(self, mode):
        """设置回测模式"""
        self.mode = mode
        if self.mode == self.BAR_MODE:
            self.dataClass = CtaBarData
            self._dataClass = CtaBarData1
        else:
            self.dataClass = CtaTickData
            self._dataClass = CtaTickData1

    # ----------------------------------------------------------------------
    def loadHistoryData1(self, dbName, symbol):
        """载入历史数据"""
        # symbol = 'I88tick'
        host, port, logging = loadMongoSetting()
        if not self.dbClient:
            self.dbClient = pymongo.MongoClient(host, port, socketKeepAlive=True)
        collection = self.dbClient[dbName][symbol]
        self.output(u'开始载入合约2数据')

        # 首先根据回测模式，确认要使用的数据类
        if self.mode == self.BAR_MODE:
            dataClass = CtaBarData
            func = self.newBar1
        else:
            dataClass = CtaTickData
            func = self.newTick1

        # 载入回测数据
        fltStartDate = self.dataStartDate.strftime("%Y-%m-%d %H:%M:%S")
        fltEndDate = self.dataEndDate.strftime("%Y-%m-%d %H:%M:%S")
        self.output("Start : " + str(self.dataStartDate))
        self.output("End : " + str(self.dataEndDate))
        if not self.dataEndDate:
            flt = {'datetime': {'$gte': fltStartDate}}  # 数据过滤条件
        else:
            flt = {'datetime': {'$gte': fltStartDate,
                                '$lte': fltEndDate}}
        self.dbCursor1 = collection.find(flt, no_cursor_timeout=True).batch_size(self.bufferSize)

        self.output(u'载入完成，数据量：%s' % (self.dbCursor1.count()))
        self.output(u' ')

    # ----------------------------------------------------------------------
    def loadHistoryData(self, dbName, symbol):
        """载入历史数据"""
        # symbol = 'I88tick'
        host, port, logging = loadMongoSetting()
        if not self.dbClient:
            self.dbClient = pymongo.MongoClient(host, port, socketKeepAlive=True)
        collection = self.dbClient[dbName][symbol]
        self.output(u'开始载入合约1数据')

        # 首先根据回测模式，确认要使用的数据类
        if self.mode == self.BAR_MODE:
            dataClass = CtaBarData
            func = self.newBar
        else:
            dataClass = CtaTickData
            func = self.newTick

        # 载入回测数据
        fltStartDate = self.dataStartDate.strftime("%Y-%m-%d %H:%M:%S")
        fltEndDate = self.dataEndDate.strftime("%Y-%m-%d %H:%M:%S")
        self.output("Start : " + str(self.dataStartDate))
        self.output("End : " + str(self.dataEndDate))
        if not self.dataEndDate:
            flt = {'datetime': {'$gte': fltStartDate}}  # 数据过滤条件
        else:
            flt = {'datetime': {'$gte': fltStartDate,
                                '$lte': fltEndDate}}
        self.dbCursor = collection.find(flt, no_cursor_timeout=True).batch_size(self.bufferSize)

        self.output(u'载入完成，数据量：%s' % (self.dbCursor.count()))
        self.output(u' ')

    # ----------------------------------------------------------------------
    def prepareData(self, dbCursor_count, dbCursor_count1):
        """数据准备线程"""
        while len(self.backtestingData) < self.bufferSize and self.j < dbCursor_count:
            d = self.dbCursor.next()
            _data = self._dataClass()
            data = self.dataClass()
            _data.__dict__ = d

            if self.mode == 'tick':
                data.vtSymbol = self.strategy.vtSymbol #'I88'
                data.lastPrice = _data.price  # 最新成交价
                data.volume = _data.volume  # 最新成交量
                data.openInterest = _data.open_interest  # 持仓量

                data.upperLimit = _data.limit_up  # 涨停价
                data.lowerLimit = _data.limit_down  # 跌停价

                data.bidPrice1 = _data.bidPrice1
                data.askPrice1 = _data.askPrice1
                data.bidVolume1 = _data.bidVolume1
                data.askVolume1 = _data.askVolume1

                data.date = _data.date  # 日期
                data.time = _data.time  # 时间
                data.datetime = datetime.strptime(_data.datetime, "%Y-%m-%d %H:%M:%S.%f")  # python的datetime时间对象

            elif self.mode == 'bar':
                data.vtSymbol = self.strategy.vtSymbol  # 'I88'
                data.open = _data.open
                data.high = _data.high
                data.low = _data.low
                data.close = _data.close
                data.volume = _data.volume

                data.date = _data.date  # 日期
                data.time = _data.time  # 时间
                data.datetime = datetime.strptime(_data.datetime, "%Y-%m-%d %H:%M:%S")  # python的datetime时间对象

            self.backtestingData.append(data)
            self.j += 1
        while len(self.backtestingData1) < self.bufferSize and self.i < dbCursor_count1:
            d1 = self.dbCursor1.next()
            _data = self._dataClass()
            data1 = self.dataClass()
            _data.__dict__ = d1

            if self.mode == 'tick':
                data1.vtSymbol = self.strategy.vtSymbol1 #'I88'
                data1.lastPrice = _data.price  # 最新成交价
                data1.volume = _data.volume  # 最新成交量
                data1.openInterest = _data.open_interest  # 持仓量

                data1.upperLimit = _data.limit_up  # 涨停价
                data1.lowerLimit = _data.limit_down  # 跌停价

                data1.bidPrice1 = _data.bidPrice1
                data1.askPrice1 = _data.askPrice1
                data1.bidVolume1 = _data.bidVolume1
                data1.askVolume1 = _data.askVolume1

                data1.date = _data.date  # 日期
                data1.time = _data.time  # 时间
                data1.datetime = datetime.strptime(_data.datetime, "%Y-%m-%d %H:%M:%S.%f")  # python的datetime时间对象

            elif self.mode == 'bar':
                data1.vtSymbol = self.strategy.vtSymbol1  # 'I88'
                data1.open = _data.open
                data1.high = _data.high
                data1.low = _data.low
                data1.close = _data.close
                data1.volume = _data.volume

                data1.date = _data.date  # 日期
                data1.time = _data.time  # 时间
                data1.datetime = datetime.strptime(_data.datetime, "%Y-%m-%d %H:%M:%S")  # python的datetime时间对象

            self.backtestingData1.append(data1)
            self.i += 1

    # ----------------------------------------------------------------------
    def runBacktesting(self):
        """运行回测
           判断是否双合约"""
        if self.strategy.vtSymbol1 == None:
            self.runBacktesting_one()
        else:
            self.runBacktesting_two()

    # ----------------------------------------------------------------------
    def runBacktesting_two(self):
        """运行回测"""
        if self.mode == self.BAR_MODE:
            self.dataClass = CtaBarData
            func = self.newBar
            func1 = self.newBar1
            func2 = self.newBar01
        else:
            self.dataClass = CtaTickData
            func = self.newTick
            func1 = self.newTick1
            func2 = self.newTick01
        self.output(u'-' * 30)
        self.output(u'开始回测')

        self.strategy.inited = True
        self.strategy.onInit()
        self.output(u'策略初始化完成')

        self.strategy.trading = True
        self.strategy.onStart()
        self.output(u'策略启动完成')

        dbCursor_count = self.dbCursor.count()
        dbCursor_count1 = self.dbCursor1.count()
        self.i = 0;
        self.j = 0;
        lastData = None
        lastData1 = None
        t = None
        self.output(u'开始回放双合约数据')
        # 双合约回测
        while (self.i < dbCursor_count1 and self.j < dbCursor_count) or (
            self.backtestingData and self.backtestingData1):
            # 启动数据准备线程
            t = threading.Thread(target=self.prepareData, args=(dbCursor_count, dbCursor_count1))
            t.start()
            # 模拟撮合
            while self.backtestingData and self.backtestingData1:
                # 考虑切片数据可能不连续，同步两个合约的数据
                if self.backtestingData1[0].datetime > self.backtestingData[0].datetime:
                    if lastData1:
                        func2(self.backtestingData[0], lastData1)
                    lastData = self.backtestingData.popleft()
                elif self.backtestingData[0].datetime > self.backtestingData1[0].datetime:
                    if lastData:
                        func2(lastData, self.backtestingData1[0])
                    lastData1 = self.backtestingData1.popleft()
                elif self.backtestingData and self.backtestingData1 and self.backtestingData1[0].datetime == \
                        self.backtestingData[0].datetime:
                    func2(self.backtestingData[0], self.backtestingData1[0])
                    lastData = self.backtestingData.popleft()
                    lastData1 = self.backtestingData1.popleft()
            t.join()

        self.strategy.onStop()
        self.output(u'数据回放结束')

    # ----------------------------------------------------------------------
    def runBacktesting_one(self):
        """运行回测"""
        if self.mode == self.BAR_MODE:
            self.dataClass = CtaBarData
            func = self.newBar
            func1 = self.newBar1
        else:
            self.dataClass = CtaTickData
            func = self.newTick
        self.output(u'开始回测')

        self.strategy.inited = True
        self.strategy.onInit()
        self.output(u'策略初始化完成')

        self.strategy.trading = True
        self.strategy.onStart()
        self.output(u'策略启动完成')

        self.output(u'开始回放单合约数据')
        dbCursor_count = self.dbCursor.count()
        self.j = 0;
        self.i = 0;
        dbCursor_count1 = 0
        lastData = None
        lastData1 = None
        t = None
        # 单合约回测
        while self.j < dbCursor_count or self.backtestingData:
            # 启动数据准备线程
            t = threading.Thread(target=self.prepareData, args=(dbCursor_count, dbCursor_count1))
            t.start()
            # 模拟撮合
            while self.backtestingData:
                lastData = self.backtestingData.popleft()
                func(lastData)
            t.join()

        self.strategy.onStop()
        self.output(u'数据回放结束')

    # ----------------------------------------------------------------------
    def newBar(self, bar):
        """新的K线"""
        self.bar = bar
        self.dt = bar.datetime
        self.crossLimitOrder()  # 先撮合限价单
        # self.crossStopOrder()       # 再撮合停止单
        self.strategy.onBar(bar)  # 推送K线到策略中

    # ----------------------------------------------------------------------
    def newBar1(self, bar):
        """新的K线"""
        self.bar1 = bar
        self.dt = bar.datetime
        self.crossLimitOrder1()  # 先撮合限价单
        self.strategy.onBar(bar)  # 推送K线到策略中

    # ----------------------------------------------------------------------
    def newBar01(self, bar, bar1):
        """新的Bar"""
        self.dt = bar.datetime
        self.bar = bar
        self.bar1 = bar1
        # 低速模式（延时1个Tick撮合）
        self.crossBarLimitOrder1()
        self.crossBarLimitOrder()
        # 没有切片的合约不发送行情（为了和实盘一致）
        if bar1.datetime >= bar.datetime:
            self.strategy.onBar(self.bar1)
        if bar.datetime >= bar1.datetime:
            self.strategy.onBar(self.bar)
        self.strategy.onSpread()
        # 高速模式（直接撮合）
        if self.optimism:
            self.crossBarLimitOrder1()
            self.crossBarLimitOrder()
        self.lastbar = self.bar
        self.lastbar1 = self.bar1

    # ----------------------------------------------------------------------
    def newTick(self, tick):
        """新的Tick"""
        self.tick = tick
        self.dt = tick.datetime
        # 低速模式（延时1个Tick撮合）
        self.crossLimitOrder()
        self.strategy.onTick(tick)
        # 高速模式（直接撮合）
        if self.optimism:
            self.crossLimitOrder()
        self.lasttick = tick

    # ----------------------------------------------------------------------
    def newTick1(self, tick):
        """新的Tick"""
        self.tick1 = tick
        self.dt = tick.datetime
        # 低速模式（延时1个Tick撮合）
        self.crossLimitOrder()
        self.strategy.onTick(tick)
        # 高速模式（直接撮合）
        if self.optimism:
            self.crossLimitOrder()
        self.lasttick1 = tick

    # ----------------------------------------------------------------------
    def newTick01(self, tick, tick1):
        """新的Tick"""
        self.dt = tick.datetime
        self.tick = tick
        self.tick1 = tick1
        # 低速模式（延时1个Tick撮合）
        self.crossLimitOrder1()
        self.crossLimitOrder()
        # 没有切片的合约不发送行情（为了和实盘一致）
        if tick1.datetime >= tick.datetime:
            self.strategy.onTick(self.tick1)
        if tick.datetime >= tick1.datetime:
            self.strategy.onTick(self.tick)
        # 高速模式（直接撮合）
        if self.optimism:
            self.crossLimitOrder1()
            self.crossLimitOrder()
        self.lasttick = self.tick
        self.lasttick1 = self.tick1

    # ----------------------------------------------------------------------
    def initStrategy(self, strategyClass, setting=None):
        """
        初始化策略
        setting是策略的参数设置，如果使用类中写好的默认设置则可以不传该参数
        """
        self.strategy = strategyClass(self, setting)
        # self.strategy.name = self.strategy.className

    # ----------------------------------------------------------------------
    def sendOrder(self, vtSymbol, orderType, price, volume, strategy):
        """发单"""
        self.limitOrderCount += 1
        orderID = str(self.limitOrderCount)

        order = VtOrderData()
        order.vtSymbol = vtSymbol
        order.price = price
        order.priceType = PRICETYPE_LIMITPRICE
        order.totalVolume = volume
        order.status = STATUS_NOTTRADED  # 刚提交尚未成交
        order.orderID = orderID
        order.vtOrderID = orderID
        order.orderTime = str(self.dt)

        # CTA委托类型映射
        if orderType == CTAORDER_BUY:
            order.direction = DIRECTION_LONG
            order.offset = OFFSET_OPEN
        elif orderType == CTAORDER_SHORT:
            order.direction = DIRECTION_SHORT
            order.offset = OFFSET_OPEN
        elif orderType == CTAORDER_SELL and not self.shfe:
            order.direction = DIRECTION_SHORT
            order.offset = OFFSET_CLOSE
        elif orderType == CTAORDER_SELL and self.shfe:
            order.direction = DIRECTION_SHORT
            order.offset = OFFSET_CLOSEYESTERDAY
        elif orderType == CTAORDER_COVER and not self.shfe:
            order.direction = DIRECTION_LONG
            order.offset = OFFSET_CLOSE
        elif orderType == CTAORDER_COVER and self.shfe:
            order.direction = DIRECTION_LONG
            order.offset = OFFSET_CLOSEYESTERDAY
        elif orderType == CTAORDER_SELL_TODAY:
            order.direction = DIRECTION_SHORT
            order.offset = OFFSET_CLOSETODAY
        elif orderType == CTAORDER_COVER_TODAY:
            order.direction = DIRECTION_LONG
            order.offset = OFFSET_CLOSETODAY

            # 保存到限价单字典中
        if vtSymbol == strategy.vtSymbol:
            self.workingLimitOrderDict[orderID] = order
            self.limitOrderDict[orderID] = order
        elif vtSymbol == strategy.vtSymbol1:
            self.workingLimitOrderDict1[orderID] = order
            self.limitOrderDict1[orderID] = order

        return orderID

    # ----------------------------------------------------------------------
    def sendOrderFAK(self, vtSymbol, orderType, price, volume, strategy):
        """发单"""
        self.limitOrderCount += 1
        orderID = str(self.limitOrderCount)

        order = VtOrderData()
        order.vtSymbol = vtSymbol
        order.price = price
        order.priceType = PRICETYPE_FAK
        order.totalVolume = volume
        order.status = STATUS_NOTTRADED  # 刚提交尚未成交
        order.orderID = orderID
        order.vtOrderID = orderID
        order.orderTime = str(self.dt)

        # CTA委托类型映射
        if orderType == CTAORDER_BUY:
            order.direction = DIRECTION_LONG
            order.offset = OFFSET_OPEN
        elif orderType == CTAORDER_SELL and not self.shfe:
            order.direction = DIRECTION_SHORT
            order.offset = OFFSET_CLOSE
        elif orderType == CTAORDER_SELL and self.shfe:
            order.direction = DIRECTION_SHORT
            order.offset = OFFSET_CLOSEYESTERDAY
        elif orderType == CTAORDER_SELL_TODAY:
            order.direction = DIRECTION_SHORT
            order.offset = OFFSET_CLOSETODAY
        elif orderType == CTAORDER_SHORT:
            order.direction = DIRECTION_SHORT
            order.offset = OFFSET_OPEN
        elif orderType == CTAORDER_COVER and not self.shfe:
            order.direction = DIRECTION_LONG
            order.offset = OFFSET_CLOSE
        elif orderType == CTAORDER_COVER and self.shfe:
            order.direction = DIRECTION_LONG
            order.offset = OFFSET_CLOSEYESTERDAY
        elif orderType == CTAORDER_COVER_TODAY:
            order.direction = DIRECTION_LONG
            order.offset = OFFSET_CLOSETODAY

            # 保存到限价单字典中
        if vtSymbol == strategy.vtSymbol:
            self.workingLimitOrderDict[orderID] = order
            self.limitOrderDict[orderID] = order
        elif vtSymbol == strategy.vtSymbol1:
            self.workingLimitOrderDict1[orderID] = order
            self.limitOrderDict1[orderID] = order

        return orderID

    # ----------------------------------------------------------------------
    def sendOrderFOK(self, vtSymbol, orderType, price, volume, strategy):
        """发单"""
        self.limitOrderCount += 1
        orderID = str(self.limitOrderCount)

        order = VtOrderData()
        order.vtSymbol = vtSymbol
        order.price = price
        order.priceType = PRICETYPE_FOK
        order.totalVolume = volume
        order.status = STATUS_NOTTRADED  # 刚提交尚未成交
        order.orderID = orderID
        order.vtOrderID = orderID
        order.orderTime = str(self.dt)

        # CTA委托类型映射
        if orderType == CTAORDER_BUY:
            order.direction = DIRECTION_LONG
            order.offset = OFFSET_OPEN
        elif orderType == CTAORDER_SELL and not self.shfe:
            order.direction = DIRECTION_SHORT
            order.offset = OFFSET_CLOSE
        elif orderType == CTAORDER_SELL and self.shfe:
            order.direction = DIRECTION_SHORT
            order.offset = OFFSET_CLOSEYESTERDAY
        elif orderType == CTAORDER_SELL_TODAY:
            order.direction = DIRECTION_SHORT
            order.offset = OFFSET_CLOSETODAY
        elif orderType == CTAORDER_SHORT:
            order.direction = DIRECTION_SHORT
            order.offset = OFFSET_OPEN
        elif orderType == CTAORDER_COVER and not self.shfe:
            order.direction = DIRECTION_LONG
            order.offset = OFFSET_CLOSE
        elif orderType == CTAORDER_COVER and self.shfe:
            order.direction = DIRECTION_LONG
            order.offset = OFFSET_CLOSEYESTERDAY
        elif orderType == CTAORDER_COVER_TODAY:
            order.direction = DIRECTION_LONG
            order.offset = OFFSET_CLOSETODAY

            # 保存到限价单字典中
        if vtSymbol == strategy.vtSymbol:
            self.workingLimitOrderDict[orderID] = order
            self.limitOrderDict[orderID] = order
        elif vtSymbol == strategy.vtSymbol1:
            self.workingLimitOrderDict1[orderID] = order
            self.limitOrderDict1[orderID] = order

        return orderID

    # ----------------------------------------------------------------------
    def cancelOrder(self, vtOrderID):
        """撤单"""
        # 找到订单
        if vtOrderID in self.workingLimitOrderDict:
            order = self.workingLimitOrderDict[vtOrderID]
        elif vtOrderID in self.workingLimitOrderDict1:
            order = self.workingLimitOrderDict1[vtOrderID]
        else:
            order = None
            return False
        # 委托回报
        if order.status == STATUS_NOTTRADED:
            order.status = STATUS_CANCELLED
            order.cancelTime = str(self.dt)
            self.strategy.onOrder(order)
        else:
            order.status = STATUS_PARTTRADED_PARTCANCELLED
            order.cancelTime = str(self.dt)
            self.strategy.onOrder(order)
        # 删除数据
        if vtOrderID in self.workingLimitOrderDict:
            self.removeOrder(vtOrderID)
        elif vtOrderID in self.workingLimitOrderDict1:
            self.removeOrder1(vtOrderID)
        return True

    # ----------------------------------------------------------------------
    def sendStopOrder(self, vtSymbol, orderType, price, volume, strategy):
        """发停止单（本地实现）"""
        self.stopOrderCount += 1
        stopOrderID = STOPORDERPREFIX + str(self.stopOrderCount)

        so = StopOrder()
        so.vtSymbol = vtSymbol
        so.price = price
        so.volume = volume
        so.strategy = strategy
        so.stopOrderID = stopOrderID
        so.status = STOPORDER_WAITING

        if orderType == CTAORDER_BUY:
            so.direction = DIRECTION_LONG
            so.offset = OFFSET_OPEN
        elif orderType == CTAORDER_SELL:
            so.direction = DIRECTION_SHORT
            so.offset = OFFSET_CLOSE
        elif orderType == CTAORDER_SHORT:
            so.direction = DIRECTION_SHORT
            so.offset = OFFSET_OPEN
        elif orderType == CTAORDER_COVER:
            so.direction = DIRECTION_LONG
            so.offset = OFFSET_CLOSE

            # 保存stopOrder对象到字典中
        self.stopOrderDict[stopOrderID] = so
        self.workingStopOrderDict[stopOrderID] = so

        return stopOrderID

    # ----------------------------------------------------------------------
    def cancelStopOrder(self, stopOrderID):
        """撤销停止单"""
        # 检查停止单是否存在
        if stopOrderID in self.workingStopOrderDict:
            so = self.workingStopOrderDict[stopOrderID]
            so.status = STOPORDER_CANCELLED
            del self.workingStopOrderDict[stopOrderID]

    # ----------------------------------------------------------------------
    def filterTradeTime(self):
        """过滤非交易时间"""
        if self.dt:
            hour = self.dt.hour
            # 丢弃非交易时间错误数据
            if (hour >= 15 and hour < 20) or (hour >= 2 and hour < 8):
                return True
            # 清空隔交易日订单
            elif hour == 8:
                self.lasttick = None
                self.lasttick1 = None
                for orderID in self.workingLimitOrderDict:
                    self.cancelOrder(orderID)
                for orderID in self.workingLimitOrderDict1:
                    self.cancelOrder(orderID)
                return True
            elif hour == 20:
                self.lasttick = None
                self.lasttick1 = None
                for orderID in self.workingLimitOrderDict:
                    self.cancelOrder(orderID)
                for orderID in self.workingLimitOrderDict1:
                    self.cancelOrder(orderID)
                return True
        return False

    # ----------------------------------------------------------------------
    def calcTickVolume(self, tick, lasttick, size):
        """计算两边盘口的成交量"""
        if (not lasttick):
            currentVolume = tick.volume
            currentTurnOver = tick.turnover
            pOnAsk = tick.askPrice1
            pOnBid = tick.bidPrice1
        else:
            currentVolume = tick.volume - lasttick.volume
            currentTurnOver = tick.turnover - lasttick.turnover
            pOnAsk = lasttick.askPrice1
            pOnBid = lasttick.bidPrice1

        if lasttick and currentVolume > 0:
            currentPrice = currentTurnOver / currentVolume / size
            ratio = (currentPrice - lasttick.bidPrice1) / (lasttick.askPrice1 - lasttick.bidPrice1)
            ratio = max(ratio, 0)
            ratio = min(ratio, 1)
            volOnAsk = ratio * currentVolume / 2
            volOnBid = (currentVolume - volOnAsk) / 2
        else:
            volOnAsk = 0
            volOnBid = 0
        return volOnBid, volOnAsk, pOnBid, pOnAsk

    # ----------------------------------------------------------------------
    def removeOrder(self, orderID):
        """清除订单信息"""
        del self.workingLimitOrderDict[orderID]
        if orderID in self.orderPrice:
            del self.orderPrice[orderID]
        if orderID in self.orderVolume:
            del self.orderVolume[orderID]

    # ----------------------------------------------------------------------
    def removeOrder1(self, orderID):
        """清除订单信息"""
        del self.workingLimitOrderDict1[orderID]
        if orderID in self.orderPrice1:
            del self.orderPrice1[orderID]
        if orderID in self.orderVolume1:
            del self.orderVolume1[orderID]

    # ----------------------------------------------------------------------
    def snapMarket(self, tradeID):
        """快照市场"""
        if self.mode == self.TICK_MODE:
            self.tradeSnap[tradeID] = copy.copy(self.tick)
            self.tradeSnap1[tradeID] = copy.copy(self.tick1)
        else:
            self.tradeSnap[tradeID] = copy.copy(self.bar)
            self.tradeSnap1[tradeID] = copy.copy(self.bar1)

    # ----------------------------------------------------------------------
    def strategyOnTrade(self, order, volumeTraded, priceTraded):
        """处理成交回报"""
        # 推送成交数据,
        self.tradeCount += 1
        tradeID = str(self.tradeCount)
        trade = VtTradeData()
        # 省略回测无关内容
        # trade.tradeID = tradeID
        # trade.vtTradeID = tradeID
        # trade.orderID = order.orderID
        # trade.vtOrderID = order.orderID
        trade.dt = self.dt
        trade.vtSymbol = order.vtSymbol
        trade.direction = order.direction
        trade.offset = order.offset
        trade.tradeTime = self.dt.strftime('%Y%m%d %H:%M:%S.') + self.dt.strftime('%f')[:1]
        trade.volume = volumeTraded
        trade.price = priceTraded
        self.strategy.onTrade(copy.copy(trade))
        # 快照市场，用于计算持仓盈亏，暂不支持
        # self.snapMarket(tradeID)
        if trade.vtSymbol == self.strategy.vtSymbol:
            self.tradeDict[tradeID] = trade
        else:
            self.tradeDict1[tradeID] = trade

    # ----------------------------------------------------------------------
    def crossLimitOrder(self):
        """基于最新数据撮合限价单"""
        # 缓存数据
        tick = self.tick
        lasttick = self.lasttick
        bar = self.bar
        # 过滤数据
        if self.filterTradeTime():
            return

        # 确定撮合价格
        if self.mode == self.BAR_MODE:
            # Bar价格撮合，目前不支持FokopenFak
            buyCrossPrice = bar.low  # 若买入方向限价单价格高于该价格，则会成交
            sellCrossPrice = bar.high  # 若卖出方向限价单价格低于该价格，则会成交
        else:
            # Tick采用对价撮合，支持Fok，Fak
            buyCrossPrice = tick.askPrice1 if tick.askPrice1 > 0 else tick.bidPrice1 + self.mPrice
            sellCrossPrice = tick.bidPrice1 if tick.bidPrice1 > 0 else tick.askPrice1 - self.mPrice

        # 遍历限价单字典中的所有限价单
        for orderID, order in self.workingLimitOrderDict.items():
            # 判断是否会成交
            buyCross = order.direction == DIRECTION_LONG and order.price >= buyCrossPrice
            sellCross = order.direction == DIRECTION_SHORT and order.price <= sellCrossPrice

            # 如果可以对价撮合
            if buyCross or sellCross:

                # 计算成交量
                volumeTraded = (order.totalVolume - order.tradedVolume)
                if self.mode == self.TICK_MODE:
                    volumeTraded = min(volumeTraded, tick.askVolume1) if buyCross \
                        else min(volumeTraded, tick.bidVolume1)
                    volumeTraded = max(volumeTraded, 1)

                # 计算成交价
                if orderID in self.orderPrice and order.tradedVolume == 0:
                    priceTraded = order.price
                else:
                    priceTraded = min(order.price, buyCrossPrice) if buyCross \
                        else max(order.price, sellCrossPrice)

                # 推送委托数据
                order.tradedVolume += volumeTraded
                # 分别处理普通限价，FOK，FAK订单
                if order.priceType == PRICETYPE_FOK:
                    if order.tradedVolume < order.totalVolume:
                        order.status = STATUS_CANCELLED
                        volumeTraded = 0
                    else:
                        order.status = STATUS_ALLTRADED

                elif order.priceType == PRICETYPE_FAK:
                    if order.tradedVolume < order.totalVolume:
                        order.status = STATUS_PARTTRADED_PARTCANCELLED
                    else:
                        order.status = STATUS_ALLTRADED
                else:
                    if order.tradedVolume < order.totalVolume:
                        order.status = STATUS_PARTTRADED
                        self.orderPrice[orderID] = order.price
                        self.orderVolume[orderID] = 0
                    else:
                        order.status = STATUS_ALLTRADED
                # 推送委托回报
                self.strategy.onOrder(order)
                # 推送成交回报
                if volumeTraded > 0:
                    self.strategyOnTrade(order, volumeTraded, priceTraded)
                # 处理完毕，删除数据
                if not order.status == STATUS_PARTTRADED:
                    self.removeOrder(orderID)

            # 模拟排队撮合部分，TICK模式有效（使用Tick内成交均价简单估计两边盘口的成交量）
            elif self.mode == self.TICK_MODE and not self.fast:

                # 计算估计的两边盘口的成交量
                volOnBid, volOnAsk, pOnBid, pOnAsk = self.calcTickVolume(tick, lasttick, self.size)

                # 排队队列维护
                if orderID in self.orderPrice:
                    # 非首次进入队列
                    if orderID not in self.orderVolume:
                        if order.price == sellCrossPrice and order.direction == DIRECTION_LONG:
                            self.orderVolume[orderID] = tick.bidVolume1
                        elif order.price == buyCrossPrice and order.direction == DIRECTION_SHORT:
                            self.orderVolume[orderID] = tick.askVolume1
                    # 首先排队进入，然后被打穿(不允许直接在买卖盘中间成交)
                    elif order.price > sellCrossPrice and order.direction == DIRECTION_LONG:
                        self.orderVolume[orderID] = 0
                    elif order.price < buyCrossPrice and order.direction == DIRECTION_SHORT:
                        self.orderVolume[orderID] = 0
                    # 更新排队值
                    elif order.price == pOnBid and order.direction == DIRECTION_LONG:
                        self.orderVolume[orderID] -= volOnBid
                    elif order.price == pOnAsk and order.direction == DIRECTION_SHORT:
                        self.orderVolume[orderID] -= volOnAsk
                else:
                    # 首次进入队列
                    self.orderPrice[orderID] = order.price
                    if order.direction == DIRECTION_SHORT and order.price == tick.askPrice1:
                        self.orderVolume[orderID] = tick.askVolume1
                    elif order.direction == DIRECTION_LONG and order.price == tick.bidPrice1:
                        self.orderVolume[orderID] = tick.bidVolume1

                # 排队成交，注意，目前简单一次性全部成交！！
                if orderID in self.orderVolume and self.orderVolume[orderID] <= 0:

                    # 推送委托数据
                    priceTraded = order.price
                    volumeTraded = order.totalVolume - order.tradedVolume
                    order.tradedVolume = order.totalVolume
                    order.status = STATUS_ALLTRADED
                    self.strategy.onOrder(order)

                    # 推送成交回报
                    self.strategyOnTrade(order, volumeTraded, priceTraded)

                    # 从字典中删除该限价单
                    self.removeOrder(orderID)
                else:
                    order.tradedVolume = 0
                    order.status = STATUS_NOTTRADED
                    if order.priceType == PRICETYPE_FOK or order.priceType == PRICETYPE_FAK:
                        order.status = STATUS_CANCELLED
                        self.removeOrder(orderID)
                    self.strategy.onOrder(order)

    # ----------------------------------------------------------------------
    def crossLimitOrder1(self):
        """基于最新数据撮合限价单"""
        # 缓存数据
        lasttick1 = self.lasttick1
        tick1 = self.tick1
        bar1 = self.bar1
        if self.filterTradeTime():
            return

        # 区分K线撮合和TICK撮合模式
        if self.mode == self.BAR_MODE:
            buyCrossPrice = bar1.low  # 若买入方向限价单价格高于该价格，则会成交
            sellCrossPrice = bar1.high  # 若卖出方向限价单价格低于该价格，则会成交
        else:
            # TICK对价撮合，并过滤涨跌停板
            buyCrossPrice = tick1.askPrice1 if tick1.askPrice1 > 0 else tick1.bidPrice1 + self.mPrice1
            sellCrossPrice = tick1.bidPrice1 if tick1.bidPrice1 > 0 else tick1.askPrice1 - self.mPrice1

        # 遍历限价单字典中的所有限价单
        for orderID, order in self.workingLimitOrderDict1.items():

            # 判断是否对价直接成交
            buyCross = order.direction == DIRECTION_LONG and order.price >= buyCrossPrice
            sellCross = order.direction == DIRECTION_SHORT and order.price <= sellCrossPrice

            # 如果直接对价成交
            if buyCross or sellCross:
                # 计算成交量
                volumeTraded = (order.totalVolume - order.tradedVolume)
                if self.mode == self.TICK_MODE:
                    volumeTraded = min(volumeTraded, tick1.askVolume1) if buyCross \
                        else min(volumeTraded, tick1.bidVolume1)
                    volumeTraded = max(volumeTraded, 1)

                # 计算成交价
                if orderID in self.orderPrice1 and order.tradedVolume == 0:
                    priceTraded = order.price
                else:
                    priceTraded = min(order.price, buyCrossPrice) if buyCross else max(order.price, sellCrossPrice)

                # 委托回报，区分普通限价单，FOK，FAK
                order.tradedVolume += volumeTraded
                if order.priceType == PRICETYPE_FOK:
                    if order.tradedVolume < order.totalVolume:
                        order.status = STATUS_CANCELLED
                        volumeTraded = 0
                    else:
                        order.status = STATUS_ALLTRADED
                elif order.priceType == PRICETYPE_FAK:
                    if order.tradedVolume < order.totalVolume:
                        order.status = STATUS_PARTTRADED_PARTCANCELLED
                    else:
                        order.status = STATUS_ALLTRADED
                else:
                    if order.tradedVolume < order.totalVolume:
                        order.status = STATUS_PARTTRADED
                        self.orderPrice1[orderID] = order.price
                        self.orderVolume1[orderID] = 0
                    else:
                        order.status = STATUS_ALLTRADED

                # 推送委托回报
                self.strategy.onOrder(order)
                # 推送成交回报
                if volumeTraded > 0:
                    self.strategyOnTrade(order, volumeTraded, priceTraded)
                # 清除订单信息
                if not order.status == STATUS_PARTTRADED:
                    self.removeOrder1(orderID)

            # 模拟排队撮合部分,只在TICK模式有效    
            elif self.mode == self.TICK_MODE and not self.fast:

                # 计算两边盘口的成交量
                volOnBid, volOnAsk, pOnBid, pOnAsk = self.calcTickVolume(tick1, lasttick1, self.size1)

                # 排队队列维护
                if orderID in self.orderPrice1:
                    # 非首次进入队列
                    if orderID not in self.orderVolume1:
                        if order.price == sellCrossPrice and order.direction == DIRECTION_LONG:
                            self.orderVolume1[orderID] = tick1.bidVolume1
                        elif order.price == buyCrossPrice and order.direction == DIRECTION_SHORT:
                            self.orderVolume1[orderID] = tick1.askVolume1
                    # 首先排队进入，然后被打穿(不允许直接在买卖盘中间成交)
                    elif order.price > sellCrossPrice and order.direction == DIRECTION_LONG:
                        self.orderVolume1[orderID] = 0
                    elif order.price < buyCrossPrice and order.direction == DIRECTION_SHORT:
                        self.orderVolume1[orderID] = 0
                    # 更新排队值
                    elif order.price == pOnBid and order.direction == DIRECTION_LONG:
                        self.orderVolume1[orderID] -= volOnBid
                    elif order.price == pOnAsk and order.direction == DIRECTION_SHORT:
                        self.orderVolume1[orderID] -= volOnAsk
                else:
                    # 首次进入队列
                    self.orderPrice1[orderID] = order.price
                    if order.direction == DIRECTION_SHORT and order.price == tick1.askPrice1:
                        self.orderVolume1[orderID] = tick1.askVolume1
                    elif order.direction == DIRECTION_LONG and order.price == tick1.bidPrice1:
                        self.orderVolume1[orderID] = tick1.bidVolume1

                # 排队成功，注意，目前模拟为一次性成交所有订单量！！
                if orderID in self.orderVolume1 and self.orderVolume1[orderID] <= 0:
                    # 推送委托数据
                    priceTraded = order.price
                    volumeTraded = order.totalVolume - order.tradedVolume
                    order.tradedVolume = order.totalVolume
                    order.status = STATUS_ALLTRADED
                    self.strategy.onOrder(order)

                    # 推送成交回报
                    self.strategyOnTrade(order, volumeTraded, priceTraded)

                    # 从字典中删除该限价单
                    self.removeOrder1(orderID)
                else:
                    order.tradedVolume = 0
                    order.status = STATUS_NOTTRADED
                    if order.priceType == PRICETYPE_FOK or order.priceType == PRICETYPE_FAK:
                        order.status = STATUS_CANCELLED
                        self.removeOrder1(orderID)
                    self.strategy.onOrder(order)

    # ----------------------------------------------------------------------
    def crossBarLimitOrder(self):
        """基于最新数据撮合限价单"""
        # 先确定会撮合成交的价格
        if self.mode == self.BAR_MODE:
            buyCrossPrice = self.bar.low  # 若买入方向限价单价格高于该价格，则会成交
            sellCrossPrice = self.bar.high  # 若卖出方向限价单价格低于该价格，则会成交
            buyBestCrossPrice = self.bar.open  # 在当前时间点前发出的买入委托可能的最优成交价
            sellBestCrossPrice = self.bar.open  # 在当前时间点前发出的卖出委托可能的最优成交价
        else:
            buyCrossPrice = self.tick.askPrice1
            sellCrossPrice = self.tick.bidPrice1
            buyBestCrossPrice = self.tick.askPrice1
            sellBestCrossPrice = self.tick.bidPrice1

        # 遍历限价单字典中的所有限价单
        for orderID, order in self.workingLimitOrderDict.items():
            # 判断是否会成交
            buyCross = order.direction == DIRECTION_LONG and order.price >= buyCrossPrice
            sellCross = order.direction == DIRECTION_SHORT and order.price <= sellCrossPrice

            # 如果发生了成交
            if buyCross or sellCross:
                # 推送成交数据
                self.tradeCount += 1  # 成交编号自增1
                tradeID = str(self.tradeCount)
                trade = VtTradeData()
                trade.vtSymbol = order.vtSymbol
                trade.tradeID = tradeID
                trade.vtTradeID = tradeID
                trade.orderID = order.orderID
                trade.vtOrderID = order.orderID
                trade.direction = order.direction
                trade.offset = order.offset

                # 以买入为例：
                # 1. 假设当根K线的OHLC分别为：100, 125, 90, 110
                # 2. 假设在上一根K线结束(也是当前K线开始)的时刻，策略发出的委托为限价105
                # 3. 则在实际中的成交价会是100而不是105，因为委托发出时市场的最优价格是100
                if buyCross:
                    trade.price = min(order.price, buyBestCrossPrice)
                    self.strategy.pos += order.totalVolume
                else:
                    trade.price = max(order.price, sellBestCrossPrice)
                    self.strategy.pos -= order.totalVolume

                trade.volume = order.totalVolume
                trade.tradeTime = str(self.dt)
                trade.dt = self.dt
                self.strategy.onTrade(trade)

                self.tradeDict[tradeID] = trade

                # 推送委托数据
                order.tradedVolume = order.totalVolume
                order.status = STATUS_ALLTRADED
                self.strategy.onOrder(order)

                # 从字典中删除该限价单
                del self.workingLimitOrderDict[orderID]

    # ----------------------------------------------------------------------
    def crossBarLimitOrder1(self):
        """基于最新数据撮合限价单"""
        # 先确定会撮合成交的价格
        if self.mode == self.BAR_MODE:
            buyCrossPrice = self.bar.low  # 若买入方向限价单价格高于该价格，则会成交
            sellCrossPrice = self.bar.high  # 若卖出方向限价单价格低于该价格，则会成交
            buyBestCrossPrice = self.bar.open  # 在当前时间点前发出的买入委托可能的最优成交价
            sellBestCrossPrice = self.bar.open  # 在当前时间点前发出的卖出委托可能的最优成交价
        else:
            buyCrossPrice = self.tick.askPrice1
            sellCrossPrice = self.tick.bidPrice1
            buyBestCrossPrice = self.tick.askPrice1
            sellBestCrossPrice = self.tick.bidPrice1

        # 遍历限价单字典中的所有限价单
        for orderID, order in self.workingLimitOrderDict.items():
            # 判断是否会成交
            buyCross = order.direction == DIRECTION_LONG and order.price >= buyCrossPrice
            sellCross = order.direction == DIRECTION_SHORT and order.price <= sellCrossPrice

            # 如果发生了成交
            if buyCross or sellCross:
                # 推送成交数据
                self.tradeCount += 1  # 成交编号自增1
                tradeID = str(self.tradeCount)
                trade = VtTradeData()
                trade.vtSymbol = order.vtSymbol
                trade.tradeID = tradeID
                trade.vtTradeID = tradeID
                trade.orderID = order.orderID
                trade.vtOrderID = order.orderID
                trade.direction = order.direction
                trade.offset = order.offset

                # 以买入为例：
                # 1. 假设当根K线的OHLC分别为：100, 125, 90, 110
                # 2. 假设在上一根K线结束(也是当前K线开始)的时刻，策略发出的委托为限价105
                # 3. 则在实际中的成交价会是100而不是105，因为委托发出时市场的最优价格是100
                if buyCross:
                    trade.price = min(order.price, buyBestCrossPrice)
                    self.strategy.pos += order.totalVolume
                else:
                    trade.price = max(order.price, sellBestCrossPrice)
                    self.strategy.pos -= order.totalVolume

                trade.volume = order.totalVolume
                trade.tradeTime = str(self.dt)
                trade.dt = self.dt
                self.strategy.onTrade(trade)

                self.tradeDict1[tradeID] = trade

                # 推送委托数据
                order.tradedVolume = order.totalVolume
                order.status = STATUS_ALLTRADED
                self.strategy.onOrder(order)

                # 从字典中删除该限价单
                del self.workingLimitOrderDict[orderID]

    # ----------------------------------------------------------------------
    def crossStopOrder(self):
        """基于最新数据撮合停止单"""
        # 停止单撮合未更新
        # 先确定会撮合成交的价格，这里和限价单规则相反
        if self.mode == self.BAR_MODE:
            buyCrossPrice = self.bar.high  # 若买入方向停止单价格低于该价格，则会成交
            sellCrossPrice = self.bar.low  # 若卖出方向限价单价格高于该价格，则会成交
            bestCrossPrice = self.bar.open  # 最优成交价，买入停止单不能低于，卖出停止单不能高于
        else:
            buyCrossPrice = self.tick.lastPrice
            sellCrossPrice = self.tick.lastPrice
            bestCrossPrice = self.tick.lastPrice

        # 遍历停止单字典中的所有停止单
        for stopOrderID, so in self.workingStopOrderDict.items():
            # 判断是否会成交
            buyCross = so.direction == DIRECTION_LONG and so.price <= buyCrossPrice
            sellCross = so.direction == DIRECTION_SHORT and so.price >= sellCrossPrice

            # 如果发生了成交
            if buyCross or sellCross:
                # 推送成交数据
                self.tradeCount += 1
                tradeID = str(self.tradeCount)
                trade = VtTradeData()
                trade.vtSymbol = so.vtSymbol
                trade.tradeID = tradeID
                trade.vtTradeID = tradeID

                if buyCross:
                    trade.price = max(bestCrossPrice, so.price)
                else:
                    trade.price = min(bestCrossPrice, so.price)

                self.limitOrderCount += 1
                orderID = str(self.limitOrderCount)
                trade.orderID = orderID
                trade.vtOrderID = orderID

                trade.direction = so.direction
                trade.offset = so.offset
                trade.volume = so.volume
                trade.tradeTime = self.dt.strftime('%Y%m%d %H:%M:%S.') + self.dt.strftime('%f')[:1]
                trade.dt = self.dt
                self.strategy.onTrade(copy.copy(trade))

                self.tradeDict[tradeID] = trade
                self.tradeDict1[tradeID] = trade

                # 推送委托数据
                so.status = STOPORDER_TRIGGERED

                order = VtOrderData()
                order.vtSymbol = so.vtSymbol
                order.symbol = so.vtSymbol
                order.orderID = orderID
                order.vtOrderID = orderID
                order.direction = so.direction
                order.offset = so.offset
                order.price = so.price
                order.totalVolume = so.volume
                order.tradedVolume = so.volume
                order.status = STATUS_ALLTRADED
                order.orderTime = trade.tradeTime
                self.strategy.onOrder(order)

                self.limitOrderDict[orderID] = order

                # 从字典中删除该限价单
                del self.workingStopOrderDict[stopOrderID]

                # ----------------------------------------------------------------------

    # ----------------------------------------------------------------------
    def insertData(self, dbName, collectionName, data):
        """考虑到回测中不允许向数据库插入数据，防止实盘交易中的一些代码出错"""
        pass

    # ----------------------------------------------------------------------
    def writeCtaLog(self, content):
        """记录日志"""
        log = str(self.dt) + ' ' + content
        self.logList.append(log)

    # ----------------------------------------------------------------------
    def output(self, content):
        """输出内容"""
        if not self.plot:
            return
        if self.plotfile:
            print content.encode('utf8')
        else:
            print content

    # ----------------------------------------------------------------------
    def makeRecord(self, tradeTime, offset, direction, price, pnl):
        """记录成交内容"""
        resDict = {}
        resDict[u'datetime'] = tradeTime
        resDict[u'price'] = price
        resDict[u'contract0'] = self.strategy.vtSymbol
        resDict[u'contract1'] = self.strategy.vtSymbol
        resDict[u'offset'] = offset
        resDict[u'direction'] = direction
        resDict[u'pnl'] = pnl
        if self.strategy.vtSymbol1:
            resDict[u'contract1'] = self.strategy.vtSymbol1
        return resDict

    # ----------------------------------------------------------------------
    def calculateBacktestingResult(self, detial=False):
        """
        计算回测结果
        """
        self.output(u'按逐笔对冲计算回测结果')
        # 首先基于回测后的成交记录，计算每笔交易的盈亏
        pnlDict = OrderedDict()  # 每笔盈亏的记录
        longTrade = deque([])  # 未平仓的多头交易
        shortTrade = deque([])  # 未平仓的空头交易
        longTrade1 = deque([])  # 合约2未平仓的多头交易
        shortTrade1 = deque([])  # 合约2未平仓的空头交易
        resList = [{"name": self.strategy.name}]

        # 计算滑点，一个来回包括两次
        totalSlippage = self.slippage * 2
        self.output(u'总交易量 : ' + str(len(self.tradeDict)))
        self.output(u'总交易量1 : ' + str(len(self.tradeDict1)))

        leg2 = True

        if self.tradeDict.values():
            dict_trade = self.tradeDict.values()
        else:
            dict_trade = self.tradeDict1.values()
            leg2 = False

        if self.tradeDict1.values():
            dict_trade1 = self.tradeDict1.values()
        else:
            dict_trade1 = self.tradeDict.values()
            leg2 = False

        for trade1 in dict_trade1:
            # 多头交易
            if trade1.direction == DIRECTION_LONG:
                # 当前多头交易为平空
                untraded = True
                while (shortTrade1 and untraded):
                    entryTrade = shortTrade1[0]
                    exitTrade = trade1
                    volume = min(entryTrade.volume, exitTrade.volume)
                    entryTrade.volume = entryTrade.volume - volume
                    exitTrade.volume = exitTrade.volume - volume
                    if entryTrade.volume == 0:
                        shortTrade1.popleft()
                    if exitTrade.volume == 0:
                        untraded = False

                    if exitTrade.dt not in pnlDict:
                        pnlDict[exitTrade.dt] = TradingResult(entryTrade.price, entryTrade.dt,
                                                              exitTrade.price, exitTrade.dt,
                                                              -volume, self.rate1, self.slippage1, self.size1)
                    elif leg2:
                        pnlDict[exitTrade.dt].add(entryTrade.price, entryTrade.dt,
                                                  exitTrade.price, exitTrade.dt,
                                                  -volume, self.rate1, self.slippage1, self.size1)
                    if exitTrade.dt in pnlDict and leg2:
                        pnlDict[exitTrade.dt].posPnl = self.calcPosPNL1(exitTrade.tradeID, shortTrade, longTrade,
                                                                        shortTrade1, longTrade1, leg2)
                    elif not leg2:
                        pnlDict[exitTrade.dt].posPnl = self.calcPosPNL1(exitTrade.tradeID, shortTrade, longTrade,
                                                                        shortTrade1, longTrade1, leg2)
                # 如果尚无空头交易
                if untraded:
                    longTrade1.append(trade1)
            # 空头交易        
            else:
                # 当前空头交易为平多
                untraded = True
                while (untraded and longTrade1):
                    entryTrade = longTrade1[0]
                    exitTrade = trade1
                    volume = min(entryTrade.volume, exitTrade.volume)
                    entryTrade.volume = entryTrade.volume - volume
                    exitTrade.volume = exitTrade.volume - volume
                    if entryTrade.volume == 0:
                        longTrade1.popleft()
                    if exitTrade.volume == 0:
                        untraded = False

                    if exitTrade.dt not in pnlDict:
                        pnlDict[exitTrade.dt] = TradingResult(entryTrade.price, entryTrade.dt,
                                                              exitTrade.price, exitTrade.dt,
                                                              volume, self.rate1, self.slippage1, self.size1)
                    elif leg2:
                        pnlDict[exitTrade.dt].add(entryTrade.price, entryTrade.dt,
                                                  exitTrade.price, exitTrade.dt,
                                                  volume, self.rate1, self.slippage1, self.size1)
                    if exitTrade.dt in pnlDict and leg2:
                        pnlDict[exitTrade.dt].posPnl = self.calcPosPNL1(exitTrade.tradeID, shortTrade, longTrade,
                                                                        shortTrade1, longTrade1, leg2)
                    elif not leg2:
                        pnlDict[exitTrade.dt].posPnl = self.calcPosPNL1(exitTrade.tradeID, shortTrade, longTrade,
                                                                        shortTrade1, longTrade1, leg2)

                # 如果尚无多头交易
                if untraded:
                    shortTrade1.append(trade1)

        for trade in dict_trade:
            # 多头交易
            if trade.direction == DIRECTION_LONG:
                # 当前多头交易为平空
                untraded = True
                while (shortTrade and untraded):
                    entryTrade = shortTrade[0]
                    exitTrade = trade

                    # 计算比例佣金
                    volume = min(entryTrade.volume, exitTrade.volume)
                    entryTrade.volume = entryTrade.volume - volume
                    exitTrade.volume = exitTrade.volume - volume
                    if entryTrade.volume == 0:
                        shortTrade.popleft()
                    if exitTrade.volume == 0:
                        untraded = False

                    if exitTrade.dt not in pnlDict:
                        pnlDict[exitTrade.dt] = TradingResult(entryTrade.price, entryTrade.dt,
                                                              exitTrade.price, exitTrade.dt,
                                                              -volume, self.rate, self.slippage, self.size)
                    elif leg2:
                        pnlDict[exitTrade.dt].add(entryTrade.price, entryTrade.dt,
                                                  exitTrade.price, exitTrade.dt,
                                                  -volume, self.rate, self.slippage, self.size)
                    if exitTrade.dt in pnlDict and leg2:
                        pnlDict[exitTrade.dt].posPnl = self.calcPosPNL(exitTrade.tradeID, shortTrade, longTrade,
                                                                       shortTrade1, longTrade1, leg2)
                    elif not leg2:
                        pnlDict[exitTrade.dt].posPnl = self.calcPosPNL(exitTrade.tradeID, shortTrade, longTrade,
                                                                       shortTrade1, longTrade1, leg2)
                    pnl = pnlDict[exitTrade.dt].pnl
                    # 记录用来可视化的成交内容
                    resDict = self.makeRecord(entryTrade.tradeTime, u'开', u'卖', entryTrade.price, pnl)
                    resList.append(resDict)
                    resDict = self.makeRecord(exitTrade.tradeTime, u'平', u'买', exitTrade.price, pnl)
                    resList.append(resDict)
                # 如果尚无空头交易
                if untraded:
                    longTrade.append(trade)

            # 空头交易        
            else:
                # 当前空头交易为平多
                untraded = True
                while (longTrade and untraded):
                    entryTrade = longTrade[0]
                    exitTrade = trade
                    # 计算比例佣金
                    volume = min(entryTrade.volume, exitTrade.volume)
                    entryTrade.volume = entryTrade.volume - volume
                    exitTrade.volume = exitTrade.volume - volume
                    if entryTrade.volume == 0:
                        longTrade.popleft()
                    if exitTrade.volume == 0:
                        untraded = False

                    if exitTrade.dt not in pnlDict:
                        pnlDict[exitTrade.dt] = TradingResult(entryTrade.price, entryTrade.dt,
                                                              exitTrade.price, exitTrade.dt,
                                                              volume, self.rate, self.slippage, self.size)
                    elif leg2:
                        pnlDict[exitTrade.dt].add(entryTrade.price, entryTrade.dt,
                                                  exitTrade.price, exitTrade.dt,
                                                  volume, self.rate, self.slippage, self.size)
                    if exitTrade.dt in pnlDict and leg2:
                        pnlDict[exitTrade.dt].posPnl = self.calcPosPNL(exitTrade.tradeID, shortTrade, longTrade,
                                                                       shortTrade1, longTrade1, leg2)
                    elif not leg2:
                        pnlDict[exitTrade.dt].posPnl = self.calcPosPNL(exitTrade.tradeID, shortTrade, longTrade,
                                                                       shortTrade1, longTrade1, leg2)
                    pnl = pnlDict[exitTrade.dt].pnl
                    # 记录用来可视化的成交内容
                    resDict = self.makeRecord(entryTrade.tradeTime, u'开', u'买', entryTrade.price, pnl)
                    resList.append(resDict)
                    resDict = self.makeRecord(exitTrade.tradeTime, u'平', u'卖', exitTrade.price, pnl)
                    resList.append(resDict)
                # 如果尚无多头交易
                if untraded:
                    shortTrade.append(trade)

        # 计算剩余持仓盈亏
        while (shortTrade):
            entryTrade = shortTrade.popleft()
            volume = entryTrade.volume
            if self.mode == self.TICK_MODE:
                exitTime = self.tick.datetime
                exitPrice = self.tick.askPrice1
            else:
                exitTime = self.bar.datetime
                exitPrice = self.bar.close

            if exitTime not in pnlDict:
                pnlDict[exitTime] = TradingResult(entryTrade.price, entryTrade.dt,
                                                  exitPrice, exitTime,
                                                  -volume, self.rate, self.slippage, self.size)
                pnl = pnlDict[exitTime].pnl
            elif leg2:
                pnlDict[exitTime].add(entryTrade.price, entryTrade.dt,
                                      exitPrice, exitTime,
                                      -volume, self.rate, self.slippage, self.size)
                pnl = pnlDict[exitTime].pnl
            # 记录用来可视化的成交内容
            resDict = self.makeRecord(entryTrade.tradeTime, u'开持', u'卖', entryTrade.price, pnl)
            resList.append(resDict)
            resDict = self.makeRecord(str(exitTime), u'平持', u'买', exitPrice, pnl)
            resList.append(resDict)
        while (longTrade):
            entryTrade = longTrade.popleft()
            volume = entryTrade.volume
            if self.mode == self.TICK_MODE:
                exitTime = self.tick.datetime
                exitPrice = self.tick.bidPrice1
            else:
                exitTime = self.bar.datetime
                exitPrice = self.bar.close

            if exitTime not in pnlDict:
                pnlDict[exitTime] = TradingResult(entryTrade.price, entryTrade.dt,
                                                  exitPrice, exitTime,
                                                  volume, self.rate, self.slippage, self.size)
                pnl = pnlDict[exitTime].pnl
            elif leg2:
                pnlDict[exitTime].add(entryTrade.price, entryTrade.dt,
                                      exitPrice, exitTime,
                                      volume, self.rate, self.slippage, self.size)
                pnl = pnlDict[exitTime].pnl
            # 记录用来可视化的成交内容
            resDict = self.makeRecord(entryTrade.tradeTime, u'开持', u'买', entryTrade.price, pnl)
            resList.append(resDict)
            resDict = self.makeRecord(str(exitTime), u'平持', u'卖', exitPrice, pnl)
            resList.append(resDict)
        while (leg2 and shortTrade1):
            entryTrade = shortTrade1.popleft()
            volume = entryTrade.volume
            if self.mode == self.TICK_MODE:
                exitTime = self.tick1.datetime
                exitPrice = self.tick1.askPrice1
            else:
                exitTime = self.bar1.datetime
                exitPrice = self.bar1.close

            if exitTime not in pnlDict:
                pnlDict[exitTime] = TradingResult(entryTrade.price, entryTrade.dt,
                                                  exitPrice, exitTime,
                                                  -volume, self.rate1, self.slippage1, self.size1)
                pnl = pnlDict[exitTime].pnl
            else:
                pnlDict[exitTime].add(entryTrade.price, entryTrade.dt,
                                      exitPrice, exitTime,
                                      -volume, self.rate1, self.slippage1, self.size1)
                pnl = pnlDict[exitTime].pnl
            # 记录用来可视化的成交内容
            resDict = self.makeRecord(entryTrade.tradeTime, u'开持', u'卖', entryTrade.price, pnl)
            resList.append(resDict)
            resDict = self.makeRecord(str(exitTime), u'平持', u'买', exitPrice, pnl)
            resList.append(resDict)
        while (leg2 and longTrade1):
            entryTrade = longTrade1.popleft()
            volume = entryTrade.volume
            if self.mode == self.TICK_MODE:
                exitTime = self.tick1.datetime
                exitPrice = self.tick1.bidPrice1
            else:
                exitTime = self.bar.datetime
                exitPrice = self.bar.close

            if exitTime not in pnlDict:
                pnlDict[exitTime] = TradingResult(entryTrade.price, entryTrade.dt,
                                                  exitPrice, exitTime,
                                                  volume, self.rate1, self.slippage1, self.size1)
            else:
                pnlDict[exitTime].add(entryTrade.price, entryTrade.dt,
                                      exitPrice, exitTime,
                                      volume, self.rate1, self.slippage1, self.size1)
                pnl = pnlDict[exitTime].pnl
            # 记录用来可视化的成交内容
            resDict = self.makeRecord(entryTrade.tradeTime, u'开持', u'买', entryTrade.price, pnl)
            resList.append(resDict)
            resDict = self.makeRecord(exitTime, u'平持', u'卖', exitPrice, pnl)
            resList.append(resDict)

        # 由于双合约的问题，需要整理时间序列和结果序列

        timeList = []  # 时间序列
        resultList = []  # 交易结果序列
        pnlDict0 = sorted(pnlDict.iteritems(), key=lambda d: d[0])
        for k, v in pnlDict0:
            timeList.append(k)
            resultList.append(v)

        # 然后基于每笔交易的结果，我们可以计算具体的盈亏曲线和最大回撤等        
        timeList = []  # 时间序列
        pnlList = []  # 每笔盈亏序列
        capital = 0  # 资金
        maxCapital = 0  # 资金最高净值
        drawdown = 0  # 回撤

        totalResult = 0  # 总成交数量
        totalTurnover = 0  # 总成交金额（合约面值）
        totalCommission = 0  # 总手续费
        totalSlippage = 0  # 总滑点

        capitalList = []  # 盈亏汇总的时间序列
        drawdownList = []  # 回撤的时间序列

        winningResult = 0  # 盈利次数
        losingResult = 0  # 亏损次数
        totalWinning = 0  # 总盈利金额
        totalLosing = 0  # 总亏损金额

        for result in resultList:
            capital += result.pnl
            maxCapital = max(capital + result.posPnl, maxCapital)
            drawdown = round(capital + result.posPnl - maxCapital, 2)

            pnlList.append(result.pnl)
            timeList.append(result.exitDt)  # 交易的时间戳使用平仓时间
            capitalList.append(capital + result.posPnl)
            drawdownList.append(drawdown)

            totalResult += 1
            totalTurnover += result.turnover
            totalCommission += result.commission
            totalSlippage += result.slippage

            if result.pnl >= 0:
                winningResult += 1
                totalWinning += result.pnl
            else:
                losingResult += 1
                totalLosing += result.pnl

        # 计算盈亏相关数据
        if totalResult:
            winningRate = winningResult * 1.0 / totalResult * 100  # 胜率
        else:
            winningRate = 0

        averageWinning = 0  # 这里把数据都初始化为0
        averageLosing = 0
        profitLossRatio = 0

        if winningResult:
            averageWinning = totalWinning / winningResult  # 平均每笔盈利
        else:
            averageWinning = 0

        if losingResult:
            averageLosing = totalLosing / losingResult  # 平均每笔亏损
        else:
            averageLosing = 0

        if averageLosing:
            profitLossRatio = -averageWinning / averageLosing  # 盈亏比
        else:
            profitLossRatio = 0

        # 返回回测结果
        d = {}
        d['capital'] = capital
        d['maxCapital'] = maxCapital
        d['drawdown'] = drawdown
        d['totalResult'] = totalResult
        d['totalTurnover'] = totalTurnover
        d['totalCommission'] = totalCommission
        d['totalSlippage'] = totalSlippage
        d['timeList'] = timeList
        d['pnlList'] = pnlList
        d['capitalList'] = capitalList
        d['drawdownList'] = drawdownList
        d['winningRate'] = winningRate
        d['averageWinning'] = averageWinning
        d['averageLosing'] = averageLosing
        d['profitLossRatio'] = profitLossRatio
        d['resList'] = resList

        return d

    # ----------------------------------------------------------------------
    def calcPosPNL(self, tradeID, shortTrade, longTrade, shortTrade1, longTrade1, leg2):
        """
        根据市场快照，计算每笔成交时间的持仓盈亏（按对价结算并扣除了手续费和滑点）
        """
        # 判断是否有持仓,加快无持仓策略的计算速度
        return 0
        allPos0 = len(shortTrade) + len(longTrade)
        if allPos0 == 0:
            return 0
        pnlDict = OrderedDict()  # 每笔盈亏的记录
        if tradeID in self.tradeSnap:
            tick = self.tradeSnap[tradeID]  # 主合约行情
            tick1 = self.tradeSnap1[tradeID]  # 副合约行情
        elif tradeID in self.trade1Snap:
            tick = self.trade1Snap[tradeID]  # 主合约行情
            tick1 = self.trade1Snap1[tradeID]  # 副合约行情
        else:
            tick = self.tradeSnap[tradeID]  # 主合约行情
            tick1 = self.tradeSnap1[tradeID]  # 副合约行情
        for entryTrade in shortTrade:
            volume = entryTrade.volume
            exitTime = tick.datetime
            exitPrice = tick.askPrice1

            if exitTime not in pnlDict:
                pnlDict[exitTime] = TradingResult(entryTrade.price, entryTrade.dt,
                                                  exitPrice, exitTime,
                                                  -volume, self.rate, self.slippage, self.size)
            elif leg2:
                pnlDict[exitTime].add(entryTrade.price, entryTrade.dt,
                                      exitPrice, exitTime,
                                      -volume, self.rate, self.slippage, self.size)
        for entryTrade in longTrade:
            volume = entryTrade.volume
            exitTime = tick.datetime
            exitPrice = tick.bidPrice1

            if exitTime not in pnlDict:
                pnlDict[exitTime] = TradingResult(entryTrade.price, entryTrade.dt,
                                                  exitPrice, exitTime,
                                                  volume, self.rate, self.slippage, self.size)
            elif leg2:
                pnlDict[exitTime].add(entryTrade.price, entryTrade.dt,
                                      exitPrice, exitTime,
                                      volume, self.rate, self.slippage, self.size)
        for entryTrade in shortTrade1:
            volume = entryTrade.volume
            exitTime = tick1.datetime
            exitPrice = tick1.askPrice1

            if exitTime not in pnlDict:
                pnlDict[exitTime] = TradingResult(entryTrade.price, entryTrade.dt,
                                                  exitPrice, exitTime,
                                                  -volume, self.rate1, self.slippage1, self.size1)
            else:
                pnlDict[exitTime].add(entryTrade.price, entryTrade.dt,
                                      exitPrice, exitTime,
                                      -volume, self.rate1, self.slippage1, self.size1)
        for entryTrade in longTrade1:
            volume = entryTrade.volume
            exitTime = tick1.datetime
            exitPrice = tick1.bidPrice1

            if exitTime not in pnlDict:
                pnlDict[exitTime] = TradingResult(entryTrade.price, entryTrade.dt,
                                                  exitPrice, exitTime,
                                                  volume, self.rate1, self.slippage1, self.size1)
            else:
                pnlDict[exitTime].add(entryTrade.price, entryTrade.dt,
                                      exitPrice, exitTime,
                                      volume, self.rate1, self.slippage1, self.size1)
        result = 0
        for v in pnlDict.values():
            result += v.pnl
        return result

    # ----------------------------------------------------------------------
    def calcPosPNL1(self, tradeID, shortTrade, longTrade, shortTrade1, longTrade1, leg2):
        """
        根据市场快照，计算每笔成交时间的持仓盈亏（按对价结算并扣除了手续费和滑点）
        """
        return 0
        # 判断是否有持仓,加快无持仓策略的计算速度
        allPos1 = len(shortTrade1) + len(longTrade1)
        if allPos1 == 0:
            return 0
        pnlDict = OrderedDict()  # 每笔盈亏的记录
        if tradeID in self.trade1Snap:
            tick = self.trade1Snap[tradeID]  # 主合约行情
            tick1 = self.trade1Snap1[tradeID]  # 副合约行情
        elif tradeID in self.tradeSnap:
            tick = self.tradeSnap[tradeID]  # 主合约行情
            tick1 = self.tradeSnap1[tradeID]  # 副合约行情
        else:
            return 0
        for entryTrade in shortTrade:
            volume = entryTrade.volume
            exitTime = tick.datetime
            exitPrice = tick.askPrice1

            if exitTime not in pnlDict:
                pnlDict[exitTime] = TradingResult(entryTrade.price, entryTrade.dt,
                                                  exitPrice, exitTime,
                                                  -volume, self.rate, self.slippage, self.size)
            elif leg2:
                pnlDict[exitTime].add(entryTrade.price, entryTrade.dt,
                                      exitPrice, exitTime,
                                      -volume, self.rate, self.slippage, self.size)
        for entryTrade in longTrade:
            volume = entryTrade.volume
            exitTime = tick.datetime
            exitPrice = tick.bidPrice1

            if exitTime not in pnlDict:
                pnlDict[exitTime] = TradingResult(entryTrade.price, entryTrade.dt,
                                                  exitPrice, exitTime,
                                                  volume, self.rate, self.slippage, self.size)
            elif leg2:
                pnlDict[exitTime].add(entryTrade.price, entryTrade.dt,
                                      exitPrice, exitTime,
                                      volume, self.rate, self.slippage, self.size)
        for entryTrade in shortTrade1:
            volume = entryTrade.volume
            exitTime = tick1.datetime
            exitPrice = tick1.askPrice1

            if exitTime not in pnlDict:
                pnlDict[exitTime] = TradingResult(entryTrade.price, entryTrade.dt,
                                                  exitPrice, exitTime,
                                                  -volume, self.rate1, self.slippage1, self.size1)
            else:
                pnlDict[exitTime].add(entryTrade.price, entryTrade.dt,
                                      exitPrice, exitTime,
                                      -volume, self.rate1, self.slippage1, self.size1)
        for entryTrade in longTrade1:
            volume = entryTrade.volume
            exitTime = tick1.datetime
            exitPrice = tick1.bidPrice1

            if exitTime not in pnlDict:
                pnlDict[exitTime] = TradingResult(entryTrade.price, entryTrade.dt,
                                                  exitPrice, exitTime,
                                                  volume, self.rate1, self.slippage1, self.size1)
            else:
                pnlDict[exitTime].add(entryTrade.price, entryTrade.dt,
                                      exitPrice, exitTime,
                                      volume, self.rate1, self.slippage1, self.size1)
        result = 0
        for v in pnlDict.values():
            result += v.pnl
        return result

    # ----------------------------------------------------------------------
    def showBacktestingResult(self):
        """
        显示回测结果
        """
        d = self.calculateBacktestingResult()
        timeList = d['timeList']
        pnlList = d['pnlList']
        capitalList = d['capitalList']
        drawdownList = d['drawdownList']
        resList = d['resList']

        self.output(u' ')
        self.output('-' * 30)
        self.output(u'显示回测结果')
        # 输出
        if len(resList) > 1:
            import codecs
            if os.path.exists('./ctaStrategy/opResults/'):
                filepath = './ctaStrategy/opResults/'
            else:
                filepath = './opResults/'
            settingFileName = filepath + self.strategy.name + '.json'
            f = codecs.open(settingFileName, 'w', 'utf-8')
            f.write(json.dumps(resList, indent=1, ensure_ascii=False))
            f.close()
        if len(timeList) > 0:
            self.output(u'第一笔交易：\t%s' % d['timeList'][0])
            self.output(u'最后一笔交易：\t%s' % d['timeList'][-1])

            self.output(u'总交易次数：\t%s' % formatNumber(d['totalResult']))
            self.output(u'总盈亏：\t%s' % formatNumber(d['capital']))
            self.output(u'最大回撤: \t%s' % formatNumber(min(d['drawdownList'])))

            self.output(u'平均每笔盈利：\t%s' % formatNumber(d['capital'] / d['totalResult']))
            self.output(u'平均每笔滑点：\t%s' % formatNumber(d['totalSlippage'] / d['totalResult']))
            self.output(u'平均每笔佣金：\t%s' % formatNumber(d['totalCommission'] / d['totalResult']))

            self.output(u'胜率\t\t%s%%' % formatNumber(d['winningRate']))
            self.output(u'平均每笔盈利\t%s' % formatNumber(d['averageWinning']))
            self.output(u'平均每笔亏损\t%s' % formatNumber(d['averageLosing']))
            self.output(u'盈亏比：\t%s' % formatNumber(d['profitLossRatio']))

            # 资金曲线插入数据库
            lastTime = None
            lastCap = 0
            lastDayCap = 0
            lastDraw = 0
            for (time, cap, drawdown) in zip(timeList, capitalList, drawdownList):
                if lastTime and time.day != lastTime.day:
                    capData = CtaCapData()
                    capData.name = self.strategy.name
                    capData.datetime = lastTime
                    capData.start = self.dataStartDate
                    capData.date = capData.datetime.replace(hour=0, minute \
                        =0, second=0, microsecond=0)
                    capData.cap = lastCap
                    capData.pnl = lastCap - lastDayCap
                    capData.drawdown = lastDraw
                    self.insertCap(CAPITAL_DB_NAME, self.strategy.name, capData)
                    lastDayCap = lastCap
                lastTime = time
                lastCap = cap
                lastDraw = drawdown

            capData = CtaCapData()
            capData.name = self.strategy.name
            capData.datetime = lastTime
            capData.start = self.dataStartDate
            capData.date = capData.datetime.replace(hour=0, minute \
                =0, second=0, microsecond=0)
            capData.cap = lastCap
            capData.pnl = lastCap - lastDayCap
            capData.drawdown = lastDraw
            self.insertCap(CAPITAL_DB_NAME, self.strategy.name, capData)

            # 绘图
            import matplotlib.pyplot as plt
            from matplotlib.dates import AutoDateLocator, DateFormatter
            plt.close()
            autodates = AutoDateLocator()
            yearsFmt = DateFormatter('%m-%d')
            # yearsFmt = DateFormatter('%Y-%m-%d')


            pCapital = plt.subplot(3, 1, 1)
            pCapital.set_ylabel("capital")
            pCapital.plot(timeList, capitalList)
            plt.title(self.strategy.name)

            plt.gcf().autofmt_xdate()  # 设置x轴时间外观
            plt.gcf().subplots_adjust(bottom=0.1)
            plt.gca().xaxis.set_major_locator(autodates)  # 设置时间间隔
            plt.gca().xaxis.set_major_formatter(yearsFmt)  # 设置时间显示格式

            pDD = plt.subplot(3, 1, 2)
            pDD.set_ylabel("DD")
            pDD.bar(range(len(drawdownList)), drawdownList)

            pPnl = plt.subplot(3, 1, 3)
            pPnl.set_ylabel("pnl")
            pPnl.hist(pnlList, bins=20)

            plt.show()

    # ----------------------------------------------------------------------
    def insertCap(self, dbName, collectionName, d):
        """插入数据到数据库（这里的data可以是CtaTickData或者CtaBarData）"""
        host, port, logging = loadMongoSetting()
        if not self.dbClient:
            self.dbClient = pymongo.MongoClient(host, port, socketKeepAlive=True)
        db = self.dbClient[dbName]
        collection = db[collectionName]
        collection.ensure_index([('date', pymongo.ASCENDING)], unique=True)
        flt = {'date': d.date}
        collection.update_one(flt, {'$set': d.__dict__}, upsert=True)

        # ----------------------------------------------------------------------

    # ----------------------------------------------------------------------
    def showBacktestingResult_nograph(self, filepath):
        """
        显示回测结果
        """
        d = self.calculateBacktestingResult()
        timeList = d['timeList']
        pnlList = d['pnlList']
        capitalList = d['capitalList']
        drawdownList = d['drawdownList']

        self.output(u'显示回测结果')
        # 输出
        if len(timeList) > 0:
            self.output('-' * 30)
            self.output(u'第一笔交易：\t%s' % d['timeList'][0])
            self.output(u'最后一笔交易：\t%s' % d['timeList'][-1])

            self.output(u'总交易次数：\t%s' % formatNumber(d['totalResult']))
            self.output(u'总盈亏：\t%s' % formatNumber(d['capital']))
            self.output(u'最大回撤: \t%s' % formatNumber(min(d['drawdownList'])))

            self.output(u'平均每笔盈利：\t%s' % formatNumber(d['capital'] / d['totalResult']))
            self.output(u'平均每笔滑点：\t%s' % formatNumber(d['totalSlippage'] / d['totalResult']))
            self.output(u'平均每笔佣金：\t%s' % formatNumber(d['totalCommission'] / d['totalResult']))

            self.output(u'胜率\t\t%s%%' % formatNumber(d['winningRate']))
            self.output(u'平均每笔盈利\t%s' % formatNumber(d['averageWinning']))
            self.output(u'平均每笔亏损\t%s' % formatNumber(d['averageLosing']))
            self.output(u'盈亏比：\t%s' % formatNumber(d['profitLossRatio']))
            self.output(u'显示回测结果')

            # 资金曲线插入数据库
            lastTime = None
            lastCap = 0
            lastDayCap = 0
            lastDraw = 0
            for (time, cap, drawdown) in zip(timeList, capitalList, drawdownList):
                if lastTime and time.day != lastTime.day:
                    capData = CtaCapData()
                    capData.name = self.strategy.name
                    capData.datetime = lastTime
                    capData.start = self.dataStartDate
                    capData.date = capData.datetime.replace(hour=0, minute \
                        =0, second=0, microsecond=0)
                    capData.cap = lastCap
                    capData.pnl = lastCap - lastDayCap
                    capData.drawdown = lastDraw
                    self.insertCap(CAPITAL_DB_NAME, self.strategy.name, capData)
                    lastDayCap = lastCap
                lastTime = time
                lastCap = cap
                lastDraw = drawdown

            # 绘图
            import matplotlib
            matplotlib.use('Qt4Agg')
            import matplotlib.pyplot as plt
            from matplotlib.dates import AutoDateLocator, DateFormatter
            autodates = AutoDateLocator()
            yearsFmt = DateFormatter('%m-%d')

            pCapital = plt.subplot(3, 1, 1)
            pCapital.set_ylabel("capital")
            pCapital.plot(timeList, capitalList)
            plt.gcf().autofmt_xdate()  # 设置x轴时间外观
            plt.gcf().subplots_adjust(bottom=0.1)
            plt.gca().xaxis.set_major_locator(autodates)  # 设置时间间隔
            plt.gca().xaxis.set_major_formatter(yearsFmt)  # 设置时间显示格式

            pDD = plt.subplot(3, 1, 2)
            pDD.set_ylabel("DD")
            pDD.bar(range(len(drawdownList)), drawdownList)

            pPnl = plt.subplot(3, 1, 3)
            pPnl.set_ylabel("pnl")
            pPnl.hist(pnlList, bins=20)

            plt.savefig(filepath)
            plt.close()

    # ----------------------------------------------------------------------
    def putStrategyEvent(self, name):
        """发送策略更新事件，回测中忽略"""
        pass

    # ----------------------------------------------------------------------
    def confSettle(self, name):
        """确认结算单，回测中忽略"""
        pass

    # ----------------------------------------------------------------------
    def setSlippage(self, slippage):
        """设置滑点"""
        self.slippage = slippage

    # ----------------------------------------------------------------------
    def setSlippage1(self, slippage):
        """设置滑点"""
        self.slippage1 = slippage

    # ----------------------------------------------------------------------
    def setSize(self, size):
        """设置合约大小"""
        self.size = size

    # ----------------------------------------------------------------------
    def setSize1(self, size):
        """设置合约大小"""
        self.size1 = size

    # ----------------------------------------------------------------------
    def setRate(self, rate):
        """设置佣金比例"""
        self.rate = rate

    # ----------------------------------------------------------------------
    def setRate1(self, rate):
        """设置佣金比例"""
        self.rate1 = rate

    # ----------------------------------------------------------------------
    def setLeverage(self, leverage):
        """设置杠杆比率"""
        self.leverage = leverage

    # ----------------------------------------------------------------------
    def setLeverage1(self, leverage):
        """设置杠杆比率"""
        self.leverage1 = leverage

    # ----------------------------------------------------------------------
    def setPrice(self, price):
        """设置合约大小"""
        self.mPrice = price

    # ----------------------------------------------------------------------
    def setPrice1(self, price):
        """设置合约大小"""
        self.mPrice1 = price

    # ----------------------------------------------------------------------
    def loadTick(self, dbName, collectionName, days):
        """从数据库中读取Tick数据，startDate是datetime对象"""
        startDate = datetime.now()

        d = {'datetime': {'$lte': startDate}}
        host, port, logging = loadMongoSetting()
        client = pymongo.MongoClient(host, port)
        collection = client[dbName][collectionName]

        cursor = collection.find(d).limit(days * 10 * 60 * 120)

        l = []
        if cursor:
            for d in cursor:
                tick = CtaTickData()
                tick.__dict__ = d
                l.append(tick)

        return l

        # ----------------------------------------------------------------------

    # ----------------------------------------------------------------------
    def loadBar(self, dbName, collectionName, days):
        """从数据库中读取Bar数据，startDate是datetime对象"""
        startDate = datetime.now()

        d = {'datetime': {'$lte': startDate}}
        host, port, logging = loadMongoSetting()
        client = pymongo.MongoClient(host, port)
        collection = client[dbName][collectionName]

        cursor = collection.find(d).limit(days * 10 * 60)

        l = []
        if cursor:
            for d in cursor:
                bar = CtaBarData()
                bar.__dict__ = d
                l.append(bar)

        return l

        # ----------------------------------------------------------------------

    # ----------------------------------------------------------------------
    def runOptimization(self, strategyClass, setting_c, optimizationSetting):
        """串行优化"""
        # 获取优化设置        
        settingList = optimizationSetting.generateSetting()
        targetName = optimizationSetting.optimizeTarget

        # 检查参数设置问题
        if not settingList or not targetName:
            self.output(u'优化设置有问题，请检查')
        vtSymbol = setting_c['vtSymbol']
        if 'vtSymbol1' in setting_c:
            vtSymbol1 = setting_c['vtSymbol1']
        else:
            vtSymbol1 = None
        # 遍历优化
        resultList = []
        opResults = []
        for setting in settingList:
            self.clearBacktestingResult()
            self.loadHistoryData(TICK_DB_NAME, vtSymbol)
            if vtSymbol1:
                self.loadHistoryData1(TICK_DB_NAME, vtSymbol1)
            self.output('-' * 30)
            self.output('setting: %s' % str(setting))
            self.initStrategy(strategyClass, setting_c)
            self.strategy.onUpdate(setting)
            self.runBacktesting()
            opResult = {}
            d = self.calculateBacktestingResult()
            for key in setting:
                opResult[key] = setting[key]
            opResult['totalResult'] = d['totalResult']
            opResult['capital'] = d['capital']
            if d['totalResult'] > 0:
                opResult['maxDrawdown'] = min(d['drawdownList'])
                opResult['winPerT'] = d['capital'] / d['totalResult']
                opResult['splipPerT'] = d['totalSlippage'] / d['totalResult']
                opResult['commiPerT'] = d['totalCommission'] / d['totalResult']
            else:
                opResult['maxDrawdown'] = 0
                opResult['winPerT'] = 0
                opResult['splipPerT'] = 0
                opResult['commiPerT'] = 0
            opResult['winningRate'] = d['winningRate']
            opResult['averageWinning'] = d['averageWinning']
            opResult['averageLosing'] = d['averageLosing']
            opResult['profitLossRatio'] = d['profitLossRatio']
            try:
                targetValue = d[targetName]
            except KeyError:
                targetValue = 0
            resultList.append(([str(setting)], targetValue))
            opResults.append(opResult)

        # 显示结果
        if os.path.exists('./ctaStrategy/opResults/'):
            filepath = './ctaStrategy/opResults/'
        else:
            filepath = './opResults/'
        with open(filepath + self.strategy.name + '.csv', 'wb') as csvfile:
            fieldnames = opResult.keys()
            writer = csv.DictWriter(csvfile, fieldnames)
            writer.writeheader()
            for opDict in opResults:
                writer.writerow(opDict)
        resultList.sort(reverse=True, key=lambda result: result[1])
        self.output('-' * 30)
        self.output(u'优化结果：')
        for result in resultList:
            self.output(u'%s: %s' % (result[0], result[1]))
        return result

    # ----------------------------------------------------------------------
    def clearBacktestingResult(self):
        """清空之前回测的结果"""
        # 交易行情相关
        self.dt = None
        self.backtestingData = deque([])
        self.backtestingData1 = deque([])
        self.tick = None
        self.tick1 = None
        self.bar = None
        self.bar1 = None
        self.lasttick = None
        self.lasttick1 = None

        self.logList = []  # 日志记录

        # 清空限价单相关
        self.limitOrderCount = 0
        self.limitOrderDict.clear()
        self.limitOrderDict1.clear()
        self.workingLimitOrderDict.clear()
        self.workingLimitOrderDict1.clear()
        self.orderPrice = {}  # 限价单价格
        self.orderVolume = {}  # 限价单盘口
        self.orderPrice1 = {}  # 限价单价格
        self.orderVolume1 = {}  # 限价单盘口

        # 清空停止单相关
        self.stopOrderCount = 0
        self.stopOrderDict.clear()
        self.workingStopOrderDict.clear()

        # 清空成交相关
        self.tradeCount = 0
        self.tradeDict.clear()
        self.tradeSnap.clear()
        self.tradeSnap1.clear()
        self.tradeCount1 = 0
        self.tradeDict1.clear()
        self.trade1Snap.clear()
        self.trade1Snap1.clear()


########################################################################
class TradingResult(object):
    """每笔交易的结果"""

    # ----------------------------------------------------------------------
    def __init__(self, entryPrice, entryDt, exitPrice,
                 exitDt, volume, rate, slippage, size):
        """Constructor"""
        self.entryPrice = entryPrice  # 开仓价格
        self.exitPrice = exitPrice  # 平仓价格

        self.entryDt = entryDt  # 开仓时间
        self.exitDt = exitDt  # 平仓时间

        self.volume = volume  # 交易数量（+/-代表方向）

        self.turnover = (self.entryPrice + self.exitPrice) * size * abs(volume)  # 成交金额
        self.commission = self.turnover * rate  # 手续费成本
        self.slippage = slippage * 2 * size * abs(volume)  # 滑点成本
        self.pnl = ((self.exitPrice - self.entryPrice) * volume * size
                    - self.commission - self.slippage)  # 净盈亏
        self.posPnl = 0  # 当时持仓盈亏

    # ----------------------------------------------------------------------
    def add(self, entryPrice, entryDt, exitPrice,
            exitDt, volume, rate, slippage, size):
        """Constructor"""
        self.entryPrice = entryPrice  # 开仓价格
        self.exitPrice = exitPrice  # 平仓价格

        self.entryDt = entryDt  # 开仓时间datetime
        self.exitDt = exitDt  # 平仓时间

        self.volume += volume  # 交易数量（+/-代表方向）

        turnover = (self.entryPrice + self.exitPrice) * size * abs(volume)
        self.turnover += turnover  # 成交金额
        commission = turnover * rate
        self.commission += commission  # 手续费成本
        slippage0 = slippage * 2 * size * abs(volume)
        self.slippage += slippage0  # 滑点成本
        self.pnl += ((self.exitPrice - self.entryPrice) * volume * size
                     - commission - slippage0)  # 净盈亏


########################################################################
class OptimizationSetting(object):
    """优化设置"""

    # ----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.paramDict = OrderedDict()

        self.optimizeTarget = ''  # 优化目标字段

    # ----------------------------------------------------------------------
    def addParameter(self, name, start, end, step):
        """增加优化参数"""
        if end <= start:
            print u'参数起始点必须小于终止点'
            return

        if step <= 0:
            print u'参数步进必须大于0'
            return

        l = []
        param = start

        while param <= end:
            l.append(param)
            param += step

        self.paramDict[name] = l

    # ----------------------------------------------------------------------
    def generateSetting(self):
        """生成优化参数组合"""
        # 参数名的列表
        nameList = self.paramDict.keys()
        paramList = self.paramDict.values()

        # 使用迭代工具生产参数对组合
        productList = list(product(*paramList))

        # 把参数对组合打包到一个个字典组成的列表中
        settingList = []
        for p in productList:
            d = dict(zip(nameList, p))
            settingList.append(d)

        return settingList

    # ----------------------------------------------------------------------
    def setOptimizeTarget(self, target):
        """设置优化目标字段"""
        self.optimizeTarget = target


# ---------------------------------------------------------------------------------------
def backtesting(setting_c, StartTime='', EndTime='', slippage=0, optimism=False, mode='T'):
    """读取策略配置"""
    # from ctaSetting import STRATEGY_CLASS
    from strategy import STRATEGY_CLASS
    from ctaBacktesting1 import BacktestingEngine
    vtSymbol = setting_c[u'vtSymbol']
    if u'vtSymbol1' in setting_c:
        vtSymbol1 = setting_c[u'vtSymbol1']
    else:
        vtSymbol1 = None
    className = setting_c[u'className']
    with open("CTA_v_setting.json") as f:
        l = json.load(f)
        for setting in l:
            name = setting[u'name']
            match = re.search('^' + name + '[0-9]', vtSymbol)
            if match:
                slippage = setting[u'mSlippage']
                rate = setting[u'mRate']
                price = setting[u'mPrice']
                size = setting[u'mSize']
                level = setting[u'mLevel']
            if vtSymbol1:
                match = re.search('^' + name + '[0-9]', vtSymbol1)
                if match:
                    slippage1 = setting[u'mSlippage']
                    rate1 = setting[u'mRate']
                    price1 = setting[u'mPrice']
                    size1 = setting[u'mSize']
                    level1 = setting[u'mLevel']

    output_s = sys.stdout
    sys.stderr = output_s
    engine = BacktestingEngine()
    engine.optimism = optimism
    # 设置引擎的回测模式, 默认为Tick
    dbName = TICK_DB_NAME
    if mode == 'T':
        engine.setBacktestingMode(engine.TICK_MODE)
        dbName = TICK_DB_NAME
    elif mode == 'B':
        engine.setBacktestingMode(engine.BAR_MODE)
        dbName = MINUTE_DB_NAME
    elif mode == 'D':
        engine.setBacktestingMode(engine.BAR_MODE)
        dbName = DAILY_DB_NAME

    if not StartTime:
        StartTime = str(setting_c[u'StartTime'])
    if not EndTime:
        EndTime = str(setting_c[u'EndTime'])

    # 设置回测用的数据起始日期
    engine.setStartDate(StartTime)
    engine.setEndDate(EndTime)

    # 载入历史数据到引擎中
    print ' '
    print ('-' * 30)
    engine.loadHistoryData(dbName, vtSymbol)
    if vtSymbol1:
        engine.loadHistoryData1(dbName, vtSymbol1)

    # 设置产品相关参数
    # 合约1
    engine.setSlippage(slippage)  # 滑点
    engine.setRate(rate)  # 万1.1
    engine.setSize(size)  # 合约大小
    engine.setPrice(price)  # 最小价格变动
    engine.setLeverage(level)  # 合约杠杆
    # 合约2
    if vtSymbol1:
        engine.setSlippage1(slippage1)  # 滑点
        engine.setRate1(rate1)  # 万1.1
        engine.setSize1(size1)  # 合约大小
        engine.setPrice1(price1)  # 最小价格变动
        engine.setLeverage1(level1)  # 合约杠杆
    else:
        engine.setSlippage1(slippage)  # 滑点
        engine.setRate1(rate)  # 万1.1
        engine.setSize1(size)  # 合约大小
        engine.setPrice1(price)  # 最小价格变动
        engine.setLeverage1(level)  # 合约杠杆

    engine.initStrategy(STRATEGY_CLASS[className], setting_c)
    engine.runBacktesting()
    engine.showBacktestingResult()
    sys.stdout = output_s


# ----------------------------------------------------------------------
def runParallelOptimization(setting_c, optimizationSetting, optimism=False, startTime='', endTime='', slippage=0,
                            mode='T'):
    """并行优化参数"""
    # 获取优化设置        
    global p
    global currentP
    print('-' * 30)
    print(u'开始优化策略 : ' + setting_c['name'])
    settingList = optimizationSetting.generateSetting()
    print(u'总共' + str(len(settingList)) + u'个优化')
    targetName = optimizationSetting.optimizeTarget
    p = ProgressBar(maxval=len(settingList))
    p.start()
    currentP = 0
    # 检查参数设置问题
    if not settingList or not targetName:
        print(u'优化设置有问题，请检查')

    # 多进程优化，启动一个对应CPU核心数量的进程池
    pool = multiprocessing.Pool(processes=multiprocessing.cpu_count() - 1)
    l = []
    for setting in settingList:
        l.append(pool.apply_async(optimize,
                                  args=(setting_c, setting, targetName, optimism, startTime, endTime, slippage, mode),
                                  callback=showProcessBar))
    pool.close()
    pool.join()
    p.finish()

    # 显示结果
    resultList = [res.get() for res in l]  # get()函数得出每个返回结果的值
    print('-' * 30)
    print(u'优化结果：')
    if os.path.exists('./strategy/opResults/'):
        filepath = './strategy/opResults/'
    else:
        filepath = './opResults/'
    with open(filepath + setting_c['name'] + '.csv', 'wb') as csvfile:
        fieldnames = resultList[0][1].keys()
        fieldnames.sort()
        writer = csv.DictWriter(csvfile, fieldnames)
        writer.writeheader()
        setting_t = {}
        value_t = -99999
        for (setting, opDict) in resultList:
            writer.writerow(opDict)
            if opDict[targetName] > value_t:
                setting_t = setting
                value_t = opDict[targetName]
        print(str(setting_t) + ':' + str(value_t))
    print(u'优化结束')
    print(u' ')


# ----------------------------------------------------------------------
def showProcessBar(result):
    """显示进度条"""
    global p
    global currentP
    currentP += 1
    p.update(currentP)


# ----------------------------------------------------------------------
def getSetting(name):
    """获取策略基础配置"""
    setting_c = {}
    settingFileName = './CTA_setting1.json'
    with open(settingFileName) as f:
        l = json.load(f)
        for setting in l:
            if setting['name'] == name:
                setting_c = setting
    setting_c[u'backtesting'] = True
    return setting_c


# ----------------------------------------------------------------------
def formatNumber(n):
    """格式化数字到字符串"""
    rn = round(n, 2)  # 保留两位小数
    return format(rn, ',')  # 加上千分符


# ----------------------------------------------------------------------
def optimize(setting_c, setting, targetName, optimism, startTime='', endTime='', slippage=0, mode='T'):
    """多进程优化时跑在每个进程中运行的函数"""
    setting_c[u'backtesting'] = True
    # from ctaSetting import STRATEGY_CLASS
    from strategy import STRATEGY_CLASS
    from ctaBacktesting1 import BacktestingEngine
    vtSymbol = setting_c[u'vtSymbol']
    if u'vtSymbol1' in setting_c:
        vtSymbol1 = setting_c[u'vtSymbol1']
    else:
        vtSymbol1 = None
    className = setting_c[u'className']
    if os.path.exists("CTA_v_setting.json"):
        fileName = "CTA_v_setting.json"
    else:
        fileName = "../CTA_v_setting.json"
    with open(fileName) as f:
        l = json.load(f)
        for setting_x in l:
            name = setting_x[u'name']
            match = re.search('^' + name + '[0-9]', vtSymbol)
            if match:
                rate = setting_x[u'mRate']
                price = setting_x[u'mPrice']
                size = setting_x[u'mSize']
                level = setting_x[u'mLevel']
            if vtSymbol1:
                match = re.search('^' + name + '[0-9]', vtSymbol1)
                if match:
                    rate1 = setting_x[u'mRate']
                    price1 = setting_x[u'mPrice']
                    size1 = setting_x[u'mSize']
                    level1 = setting_x[u'mLevel']

    name = setting_c[u'name']
    engine = BacktestingEngine()
    # engine.plot = False
    # engine.fast = True
    engine.plot = True
    engine.optimism = optimism
    # 设置引擎的回测模式
    if mode == 'T':
        engine.setBacktestingMode(engine.TICK_MODE)
        dbName = TICK_DB_NAME
    elif mode == 'B':
        engine.setBacktestingMode(engine.BAR_MODE)
        dbName = MINUTE_DB_NAME
    elif mode == 'D':
        engine.setBacktestingMode(engine.BAR_MODE)
        dbName = DAILY_DB_NAME

    # 设置回测用的数据起始日期
    if not startTime:
        startTime = str(setting_c[u'StartTime'])
    if not endTime:
        endTime = str(setting_c[u'EndTime'])
    engine.setStartDate(startTime)
    engine.setEndDate(endTime)
    engine.loadHistoryData(dbName, vtSymbol)
    if vtSymbol1:
        engine.loadHistoryData1(dbName, vtSymbol1)

    # 设置产品相关参数
    engine.setSlippage(slippage)  # 滑点
    engine.setLeverage(level)  # 合约杠杆

    engine.setSize(size)  # 合约大小
    engine.setRate(rate)  # 手续费
    engine.setPrice(price)  # 最小价格变动
    if vtSymbol1:
        engine.setSize1(size1)  # 合约大小
        engine.setRate1(rate1)  # 手续费
        engine.setPrice1(price1)  # 最小价格变动
    else:
        engine.setSize1(size)  # 合约大小
        engine.setRate1(rate)  # 手续费
        engine.setPrice1(price)  # 最小价格变动
    engine.initStrategy(STRATEGY_CLASS[className], setting_c)
    engine.strategy.onUpdate(setting)
    engine.runBacktesting()
    opResult = {}
    d = engine.calculateBacktestingResult()
    try:
        targetValue = d[targetName]
    except KeyError:
        targetValue = 0
    for key in setting:
        opResult[key] = setting[key]
    opResult['totalResult'] = d['totalResult']
    opResult['capital'] = round(d['capital'], 2)
    if d['totalResult'] > 0:
        opResult['maxDrawdown'] = min(d['drawdownList'])
        opResult['winPerT'] = round(d['capital'] / d['totalResult'], 2)
        opResult['splipPerT'] = round(d['totalSlippage'] / d['totalResult'], 2)
        opResult['commiPerT'] = round(d['totalCommission'] / d['totalResult'], 2)
    else:
        opResult['maxDrawdown'] = 0
        opResult['winPerT'] = 0
        opResult['splipPerT'] = 0
        opResult['commiPerT'] = 0
    opResult['winningRate'] = round(d['winningRate'], 2)
    opResult['averageWinning'] = round(d['averageWinning'], 2)
    opResult['averageLosing'] = round(d['averageLosing'], 2)
    opResult['profitLossRatio'] = round(d['profitLossRatio'], 2)
    return (setting, opResult)


if __name__ == '__main__':
    # 建议使用ipython notebook或者spyder来做回测
    """读取策略配置"""
    begin = datetime.now()

    # 回测策略选择
    name = 'spread'
    setting_c = getSetting(name)

    # 回测模式设置
    opt = False

    # 回测参数设置


    # 策略参数设置
    # optimizationSetting = OptimizationSetting()
    # optimizationSetting.addParameter('wLimit', 3, 4, 1) # 3, 6, 1
    # optimizationSetting.setOptimizeTarget('wLimit')

    # 确认检查
    print(u'即将开始优化回测，请确认下面的信息正确后开始回测：')
    print(u'1.回测引擎是正确的稳定版本')
    print(u'2.(乐观\悲观)模式选择正确')
    print(u'3.策略逻辑正确')
    print(u'4.策略参数初始化无遗漏')
    print(u'5.策略参数传递无遗漏')
    print(u'6.策略单次回测交割单检查正确')
    print(u'7.参数扫描区间合理')
    print(u'8.关闭结果文件')
    print(u'y/n:')
    choice = raw_input(u'')
    if not choice == 'y':
        exit(0)

    # 开始回测
    backtesting(setting_c, StartTime= "2017-05-19 21:01:00",
        EndTime = "2017-06-19 15:00:00", optimism=opt, mode='B')
    # runParallelOptimization(setting_c, optimizationSetting, optimism=opt, mode='T')
    end = datetime.now()
    print(u'回测用时: ' + str(end - begin))
    # outfile.close
