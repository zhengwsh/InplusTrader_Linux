# encoding: UTF-8
import sys,os
from PyQt4 import QtGui,QtCore
from pymongo import MongoClient
import matplotlib.dates as mpd
sys.path.append('..')
from vtConstantMid import *
import datetime as dt          
import pytz
from ui.uiCrosshair import Crosshair
"""mid
读取保存在mongodb中的tick数据并图形化，以方便观察某个阶段的tick细节
"""
class TickMonitor(pg.PlotWidget):
    #----------------------------------------------------------------------
    def __init__(self,host,port,dbName,symbolName,startDatetimeStr,endDatetimeStr):
        super(TickMonitor, self).__init__()
        self.crosshair = Crosshair(self)        #mid 实现crosshair功能
        tickMonitor = self.plot(clear=False,pen=(255, 255, 255), name="tickTimeLine")
        self.addItem(tickMonitor)  

        #mid 加载数据
        tickDatetimeNums,tickPrices = self.__loadTicksFromMongo(host,port,dbName,symbolName,startDatetimeStr,endDatetimeStr)
        #mid 显示数据
        tickMonitor.setData(tickDatetimeNums,tickPrices,clear=True,)  
        
    #----------------------------------------------------------------------
    def __loadTicksFromMongo(self,host,port,dbName,symbolName,startDatetimeStr,endDatetimeStr):
        """mid
        加载mongodb数据转换并返回数字格式的时间及价格
        """
        mongoConnection = MongoClient( host=host,port=port)
        collection = mongoConnection[dbName][symbolName]   

        startDate = dt.datetime.strptime(startDatetimeStr, '%Y-%m-%d %H:%M:%S')
        endDate = dt.datetime.strptime(endDatetimeStr, '%Y-%m-%d %H:%M:%S')  
        cx = collection.find({'datetime': {'$gte': startDate, '$lte': endDate}})    
        
        tickDatetimeNums = []
        tickPrices = []
        for d in cx:
            tickDatetimeNums.append(mpd.date2num(d['datetime']))
            tickPrices.append(d['lastPrice'])
        return tickDatetimeNums,tickPrices
    
    #----------------------------------------------------------------------
    def getTickDatetimeByXPosition(self,xAxis):
        """mid
        根据传入的x轴坐标值，返回其所代表的时间
        """
        tickDatetimeRet = xAxis
        minYearDatetimeNum = mpd.date2num(dt.datetime(1900,1,1))
        if(xAxis > minYearDatetimeNum):
            tickDatetime = mpd.num2date(xAxis).astimezone(pytz.timezone('utc'))
            if(tickDatetime.year >=1900):
                tickDatetimeRet = tickDatetime 
        return tickDatetimeRet   
    
if __name__ == "__main__":  
    app = QtGui.QApplication(sys.argv)
    
    #mid 历史tick加载参数
    host = '192.168.0.212'
    port = 27017
    dbName = 'VnTrader_Tick_Db'
    symbolName = "EUR.USD.IDEALPRO"         
    if(True):
        startDatetimeStr='2016-11-07 17:40:00'
        endDatetimeStr = '2016-11-07 18:25:00'    
    if(False):
        startDatetimeStr='2016-11-07 17:49:00'
        endDatetimeStr = '2016-11-07 17:55:00'      

    main = TickMonitor(host,port,dbName,symbolName,startDatetimeStr,endDatetimeStr)
    
    main.show()
    sys.exit(app.exec_())    








