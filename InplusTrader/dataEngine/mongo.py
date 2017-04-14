# -*- coding: utf-8 -*-
"""
Create on 2017/01/18
@author: vinson zheng
@group: inpluslab
@contact: 1530820222@qq.com
"""

import os, sys
import json
import time
import datetime
import threading
import pandas as pd
from bson import ObjectId
import pymongo
from pymongo import MongoClient
from multiprocessing.pool import ThreadPool
import func as fc
import dateu as du

reload(sys)
sys.setdefaultencoding("utf-8")


class DataEngine(object):
	"""历史数据引擎"""
	# multiThreading version
	# 建立Mongodb数据库StockDB
	# 含历史bar/tick行情数据
	# 分别建立历史日线、分钟线、分时的数据库
	# 一支股票为一个集合collection
	# 为每支股票信息收集建立一个线程

	#----------------------------------------------------------------------
	def __init__(self):
		host, port = fc.loadMongoSetting()
		print str(host) + '   ' + str(port) 
		self.dbClient = pymongo.MongoClient(host, port)
		self.Daily_Db = self.dbClient.ifTrader_Daily_Db
		self.OneMin_Db = self.dbClient.ifTrader_1Min_Db
		self.Tick_Db = self.dbClient.ifTrader_Tick_Db
		self.Symbol_Db = self.dbClient.ifTrader_Symbol_Db


	def get_symbol(self):
		# 下载股票基本信息
		df = fc.get_stock_basics_data()
		for row in range(0, df.shape[0]):
			item = {
				'code' : str(df.index[row]),
				'name' : str(df.iat[row, 0]),
				'industry' : str(df.iat[row, 1]),
				'area' : str(df.iat[row, 2]),
				'timeToMarket' : str(df.iat[row, 14])
			}
			try:
				self.Symbol_Db['equity'].insert(item)
			except:
				pass
		self.Symbol_Db['equity'].ensure_index([('code', pymongo.ASCENDING)])


	def parse(self, code, inDate, ktype):
		# 由接收tick数据并转分钟线数据
		print u'开始下载%s %s日内分时行情' %(code, str(inDate))
		# time  price  change  volume  amount  type
		df = fc.get_stock_tick_data(code, inDate)
		if df is None or df.shape[0] < 20: 
			return
		#df.to_csv(str(code)+str(inDate)+"tick.csv")
		for row in range(0, df.shape[0]) : 
			# tick data
			tickbar = {
				'date' : str(inDate),
				'time' : str(df.iat[row, 0]),
				'price' : str(df.iat[row, 1]),
				'change' : str(df.iat[row, 2]),
				'volume' : str(df.iat[row, 3]),
				'amount' : str(df.iat[row, 4]),
				'type' : str(df.iat[row, 5])
			}
			try:
				self.Tick_Db[code].insert(tickbar)
			except:
				pass
			
		print u'开始下载%s %s日内分钟行情' %(code, str(inDate))
		# date   time	open	high	low	 close	volume	amount
		newdf = fc.get_stock_min_data(code, inDate, ktype)
		if newdf is None  or newdf.shape[0] < 20: 
			return
		#newdf.to_csv(str(code)+str(inDate)+str(ktype) + "min.csv")
		for row in range(0, newdf.shape[0]) :
			#  minute data
			minbar = {
				'date' : str(newdf.index[row].date()),
				'time' : str(newdf.index[row].time()),
				'open' : str(newdf.iat[row, 0]),
				'high' : str(newdf.iat[row, 1]),
				'low' : str(newdf.iat[row, 2]),
				'close' : str(newdf.iat[row, 3]),
				'volume' : str(newdf.iat[row, 4]),
				'amount' : str(newdf.iat[row, 5])
			}
			try:
				self.OneMin_Db[code].insert(minbar)
			except:
				pass
		

	def get_range_min_tick_data(self, code, start=None, end=None, ktype=1):
		start = str(fc.get_stock_timeToMarket(code)) if start is None else start
		end = str(datetime.datetime.today().date()) if end is None else end

		startD = datetime.datetime.strptime(start, '%Y-%m-%d')
		endD = datetime.datetime.strptime(end, '%Y-%m-%d')

		delta = datetime.timedelta(days=1)
		inDate = endD - delta

		while inDate >= startD:
			self.parse(code, inDate.strftime("%Y-%m-%d"), ktype)
			inDate -= delta
		

	def get_range_daily_data(self, code, start=None, end=None):
		print u'开始下载%s日内行情' %code
		# date    open  high  close   low      volume       amount
		df = fc.get_stock_daily_data(code, start, end) 
		if df is None: 
			return
		#df.to_csv(str(code)+ "daily.csv")
		for row in range(0, df.shape[0]) :
			# daily data 
			dailybar = {
				'date' : str(df.index[row].date()),
				'open' : str(df.iat[row, 0]),
				'high' : str(df.iat[row, 1]),
				'low' : str(df.iat[row, 3]),
				'close' : str(df.iat[row, 2]),
				'volume' : str(df.iat[row, 4]),
				'amount' : str(df.iat[row, 5])
			}
			try:
				self.Daily_Db[code].insert(dailybar)
			except:
				pass
		self.Daily_Db[code].ensure_index([('date', pymongo.DESCENDING)])


	def downloadEquityAllData(self, code):
		start = self.Symbol_Db['equity'].find({"code" : code})[0]['timeToMarket']
		try:
			start = datetime.datetime.strptime(str(start), '%Y%m%d')
		except:
			return
		start = start.strftime("%Y-%m-%d")

		self.get_range_daily_data(code, start) #default上市以来
		self.get_range_min_tick_data(code, start)
		# 添加index，大幅加快查询速度
		self.Tick_Db[code].ensure_index([('date', pymongo.DESCENDING)])
		self.OneMin_Db[code].ensure_index([('date', pymongo.DESCENDING)])


	def multiDownload(self):
		#这里也测试了线程池，但可能由于下载函数中涉及较多的数据格
		#式转换，CPU开销较大，多线程效率并无显著改变。
		starttime = datetime.datetime.now()

		"""查询所有产品代码"""
		self.get_symbol()
		cx = self.Symbol_Db['equity'].find()
		symbolSet = set([d['code'] for d in cx])  # 这里返回的是集合
		p = ThreadPool(100)
		p.map(self.downloadEquityAllData, symbolSet)
		p.close()
		p.join()

		endtime = datetime.datetime.now()
		print "用时: " + str(endtime - starttime)


	def updateEquityAllData(self, code):
		# find the latest timestamp in collection.
		latest = self.Daily_Db[code].find_one(sort=[('date', pymongo.DESCENDING)])['date']
		latest = datetime.datetime.strptime(str(latest), '%Y-%m-%d')
		start = datetime.datetime.strftime(latest + timedelta(days=1), '%Y-%m-%d')
		
		self.get_range_daily_data(code, start) #default上市以来
		self.get_range_min_tick_data(code, start)


	def multiUpdate(self):
		starttime = datetime.datetime.now()

		"""查询所有产品代码"""
		self.get_symbol()
		cx = self.Symbol_Db['equity'].find()
		symbolSet = set([d['code'] for d in cx])  # 这里返回的是集合
		p = ThreadPool(100)
		p.map(self.updateEquityAllData, symbolSet)
		p.close()
		p.join()

		endtime = datetime.datetime.now()
		print "用时: " + str(endtime - starttime)


	def test(self):
		cx = self.Symbol_Db['equity'].find()
		symbolSet = set([d['code'] for d in cx])
		for code in symbolSet:
			start = self.Symbol_Db['equity'].find({"code" : code})[0]['timeToMarket']
			try:
				start = datetime.datetime.strptime(str(start), '%Y%m%d')
			except :
				print code
			
			start = start.strftime("%Y-%m-%d")
			print start
		return 


	#----------------------------------------------------------------------
	def loadMcCsv(self, fileName, dbName, symbol):
		"""将Multicharts导出的csv格式的历史数据插入到Mongo数据库中"""
		import csv

		start = time()
		print u'开始读取CSV文件%s中的数据插入到%s的%s中' %(fileName, dbName, symbol)

		# 锁定集合，并创建索引
		host, port = loadMongoSetting()

		client = pymongo.MongoClient(host, port)    
		collection = client[dbName][symbol]
		collection.ensure_index([('datetime', pymongo.ASCENDING)], unique=True)   

		# 读取数据和插入到数据库
		reader = csv.DictReader(file(fileName, 'r'))
		for d in reader:
			bar = CtaBarData()
			bar.vtSymbol = symbol
			bar.symbol = symbol
			bar.open = float(d['Open'])
			bar.high = float(d['High'])
			bar.low = float(d['Low'])
			bar.close = float(d['Close'])
			bar.date = datetime.strptime(d['Date'], '%Y/%m/%d').strftime('%Y%m%d')
			bar.time = d['Time']
			bar.datetime = datetime.strptime(bar.date + ' ' + bar.time, '%Y%m%d %H:%M:%S')
			bar.volume = d['TotalVolume']

			flt = {'datetime': bar.datetime}
			collection.update_one(flt, {'$set':bar.__dict__}, upsert=True)  
			print bar.date, bar.time

		print u'插入完毕，耗时：%s' % (time()-start)



if __name__ == '__main__':
	de = DataEngine()

	if argv[1] == 'download':
		de.multiDownload()
	else if argv[1] == 'update':
		de.multiUpdate()
	else:
		print 'No such operation!'