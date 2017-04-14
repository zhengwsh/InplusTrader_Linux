# -*- coding: utf-8 -*-
"""
Create on 2017/01/18
@author: vinson zheng
@group: inpluslab
@contact: 1530820222@qq.com
"""

'''通联数据客户端，主要使用requests开发'''

import pymongo
import os, sys
from time import time
from datetime import datetime, timedelta
from multiprocessing.pool import ThreadPool

from ctaBase import *
from vtConstant import *
from vtFunction import loadMongoSetting

import requests
import json

FILENAME = 'datayes.json'
HTTP_OK = 200

# 以下为vn.trader和通联数据规定的交易所代码映射 
VT_TO_DATAYES_EXCHANGE = {}
VT_TO_DATAYES_EXCHANGE[EXCHANGE_CFFEX] = 'CCFX'     # 中金所
VT_TO_DATAYES_EXCHANGE[EXCHANGE_SHFE] = 'XSGE'      # 上期所 
VT_TO_DATAYES_EXCHANGE[EXCHANGE_CZCE] = 'XZCE'       # 郑商所
VT_TO_DATAYES_EXCHANGE[EXCHANGE_DCE] = 'XDCE'       # 大商所
DATAYES_TO_VT_EXCHANGE = {v:k for k,v in VT_TO_DATAYES_EXCHANGE.items()}


########################################################################
class DatayesClient(object):
    """通联数据客户端"""
    name = 'test download'

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        self.domain = ''    # 主域名
        self.version = ''   # API版本
        self.token = ''     # 授权码
        self.header = {}    # http请求头部
        self.settingLoaded = False  # 配置是否已经读取
        
        self.loadSetting()


    #----------------------------------------------------------------------
    def loadSetting(self):
        """载入配置"""
        try:
            FILENAME = 'datayes.json'
            path = os.path.abspath(os.path.dirname(__file__))
            FILENAME = os.path.join(path, FILENAME)            
            f = file(FILENAME)
        except IOError:
            print u'%s无法打开配置文件' % self.name
            return
        
        setting = json.load(f)
        
        try:
            self.domain = str(setting['domain'])
            self.version = str(setting['version'])
            self.token = str(setting['token'])
        except KeyError:
            print u'%s配置文件字段缺失' % self.name
            return
        
        self.header['Connection'] = 'keep_alive'
        self.header['Authorization'] = 'Bearer ' + self.token
        self.settingLoaded = True
        
        print u'%s配置载入完成' % self.name


    #----------------------------------------------------------------------
    def downloadData(self, path, params):
        """下载数据"""
        if not self.settingLoaded:
            print u'%s配置未载入' % self.name
            return None
        else:
            url = '/'.join([self.domain, self.version, path])
            r = requests.get(url=url, headers=self.header, params=params)
            
            if r.status_code != HTTP_OK:
                print u'%shttp请求失败，状态代码%s' %(self.name, r.status_code)
                return None
            else:
                result = r.json()
                if 'retMsg' in result and result['retMsg'] == 'Success':
                    return result['data']
                else:
                    if 'retMsg' in result:
                        print u'%s查询失败，返回信息%s' %(self.name, result['retMsg'])
                    elif 'message' in result:
                        print u'%s查询失败，返回信息%s' %(self.name, result['message'])
                    return None



class HistoryDataEngine(object):
    """CTA模块用的历史数据引擎"""

    #----------------------------------------------------------------------
    def __init__(self):
        """Constructor"""
        host, port = loadMongoSetting()
        
        self.dbClient = pymongo.MongoClient(host, port)
        self.datayesClient = DatayesClient()


    #----------------------------------------------------------------------
    def lastTradeDate(self):
        """获取最近交易日（只考虑工作日，无法检查国内假期）"""
        today = datetime.now()
        oneday = timedelta(1)
        
        if today.weekday() == 5:
            today = today - oneday
        elif today.weekday() == 6:
            today = today - oneday*2        
        
        return today.strftime('%Y%m%d')


    #----------------------------------------------------------------------   
    def downloadEquitySymbol(self, tradeDate=''):
        """下载所有股票的代码"""
        if not tradeDate:
            tradeDate = self.lastTradeDate()
            print str(tradeDate)
        
        self.dbClient[SETTING_DB_NAME]['EquitySymbol'].ensure_index([('symbol', pymongo.ASCENDING)], 
                                                                       unique=True)
        

        path = 'api/market/getMktEqud.json'
        
        params = {}
        params['tradeDate'] = tradeDate
        
        data = self.datayesClient.downloadData(path, params)
        
        if data:
            for d in data:
                symbolDict = {}
                symbolDict['symbol'] = d['ticker']
                flt = {'symbol': d['ticker']}
                
                self.dbClient[SETTING_DB_NAME]['EquitySymbol'].update_one(flt, {'$set':symbolDict}, 
                                                                           upsert=True)
            print u'股票代码下载完成'
        else:
            print u'股票代码下载失败'


    #----------------------------------------------------------------------   
    def downloadFuturesSymbol(self, tradeDate=''):
        """下载所有期货的代码"""
        if not tradeDate:
            tradeDate = self.lastTradeDate()
        
        self.dbClient[SETTING_DB_NAME]['FuturesSymbol'].ensure_index([('symbol', pymongo.ASCENDING)], 
                                                                       unique=True)
        

        path = 'api/market/getMktMFutd.json'
        
        params = {}
        params['tradeDate'] = tradeDate
        
        data = self.datayesClient.downloadData(path, params)
        
        if data:
            for d in data:
                symbolDict = {}
                symbolDict['symbol'] = d['ticker']
                symbolDict['productSymbol'] = d['contractObject']
                flt = {'symbol': d['ticker']}
                
                self.dbClient[SETTING_DB_NAME]['FuturesSymbol'].update_one(flt, {'$set':symbolDict}, 
                                                                           upsert=True)
            print u'期货合约代码下载完成'
        else:
            print u'期货合约代码下载失败'


    #----------------------------------------------------------------------   
    def downloadEquityDailyBar(self, symbol):
        """
        下载股票的日行情，symbol是股票代码
        """
        print u'开始下载%s日行情' %symbol
        
        # 查询数据库中已有数据的最后日期
        cl = self.dbClient[DAILY_DB_NAME][symbol]
        cx = cl.find(sort=[('datetime', pymongo.DESCENDING)])
        if cx.count():
            last = cx[0]
        else:
            last = ''
        
        # 开始下载数据
        path = 'api/market/getMktEqud.json'
        
        params = {}
        params['ticker'] = symbol
        if last:
            params['beginDate'] = last['date']
        
        data = self.datayesClient.downloadData(path, params)
        
        if data:
            # 创建datetime索引
            self.dbClient[DAILY_DB_NAME][symbol].ensure_index([('datetime', pymongo.ASCENDING)], 
                                                                unique=True)                

            for d in data:
                bar = CtaBarData()
                bar.vtSymbol = symbol
                bar.symbol = symbol
                try:
                    bar.exchange = DATAYES_TO_VT_EXCHANGE.get(d.get('exchangeCD', ''), '')
                    bar.open = d.get('openPrice', 0)
                    bar.high = d.get('highestPrice', 0)
                    bar.low = d.get('lowestPrice', 0)
                    bar.close = d.get('closePrice', 0)
                    bar.date = d.get('tradeDate', '').replace('-', '')
                    bar.time = ''
                    bar.datetime = datetime.strptime(bar.date, '%Y%m%d')
                    bar.volume = d.get('turnoverVol', 0)
                except KeyError:
                    print d
                
                flt = {'datetime': bar.datetime}
                self.dbClient[DAILY_DB_NAME][symbol].update_one(flt, {'$set':bar.__dict__}, upsert=True)            
            
            print u'%s下载完成' %symbol
        else:
            print u'找不到合约%s' %symbol    


    #----------------------------------------------------------------------   
    def downloadAllEquityDailyBar(self):
        """下载所有股票的日行情"""
    	for item in self.dbClient[SETTING_DB_NAME]['EquitySymbol'].find({}):
    		self.downloadEquityDailyBar(item["symbol"])


    #----------------------------------------------------------------------   
    def downloadFuturesDailyBar(self, symbol):
        """
        下载期货合约的日行情，symbol是合约代码，
        若最后四位为0000（如IF0000），代表下载连续合约。
        """
        print u'开始下载%s日行情' %symbol
        
        # 查询数据库中已有数据的最后日期
        cl = self.dbClient[DAILY_DB_NAME][symbol]
        cx = cl.find(sort=[('datetime', pymongo.DESCENDING)])
        if cx.count():
            last = cx[0]
        else:
            last = ''
        
        # 主力合约
        if '0000' in symbol:
            path = 'api/market/getMktMFutd.json'
            
            params = {}
            params['contractObject'] = symbol.replace('0000', '')
            params['mainCon'] = 1
            if last:
                params['startDate'] = last['date']
        # 交易合约
        else:
            path = 'api/market/getMktFutd.json'
            
            params = {}
            params['ticker'] = symbol
            if last:
                params['startDate'] = last['date']
        
        # 开始下载数据
        data = self.datayesClient.downloadData(path, params)
        
        if data:
            # 创建datetime索引
            self.dbClient[DAILY_DB_NAME][symbol].ensure_index([('datetime', pymongo.ASCENDING)], 
                                                                      unique=True)                

            for d in data:
                print d
                bar = CtaBarData()
                bar.vtSymbol = symbol
                bar.symbol = symbol
                try:
                    bar.exchange = DATAYES_TO_VT_EXCHANGE.get(d.get('exchangeCD', ''), '')
                    bar.open = d.get('openPrice', 0)
                    bar.high = d.get('highestPrice', 0)
                    bar.low = d.get('lowestPrice', 0)
                    bar.close = d.get('closePrice', 0)
                    bar.date = d.get('tradeDate', '').replace('-', '')
                    bar.time = ''
                    bar.datetime = datetime.strptime(bar.date, '%Y%m%d')
                    bar.volume = d.get('turnoverVol', 0)
                    bar.openInterest = d.get('openInt', 0)
                except KeyError:
                    print d
                
                flt = {'datetime': bar.datetime}
                self.dbClient[DAILY_DB_NAME][symbol].update_one(flt, {'$set':bar.__dict__}, upsert=True)            
            
            print u'%s下载完成' %symbol
        else:
            print u'找不到合约%s' %symbol


    #----------------------------------------------------------------------
    def downloadAllFuturesDailyBar(self):
        """下载所有期货的主力合约日行情"""
        for item in self.dbClient[SETTING_DB_NAME]['FuturesSymbol'].find({}):
    		self.downloadFuturesDailyBar(item["productSymbol"] + '0000')





if __name__ == '__main__':

    e = HistoryDataEngine()
    #e.downloadEquitySymbol()
    #e.downloadFuturesSymbol()

    e.downloadAllEquityDailyBar()
    #e.downloadAllFuturesDailyBar()

    ## 简单的测试脚本可以写在这里
    #from time import sleep
    #e = HistoryDataEngine()
    #sleep(1)
    #e.downloadEquityDailyBar('000001')
    
    # 这里将项目中包含的股指日内分钟线csv导入MongoDB，作者电脑耗时大约3分钟
    #loadMcCsv('IF0000_1min.csv', MINUTE_DB_NAME, 'IF0000')
