# encoding: UTF-8
import sys,os
import matplotlib.dates as mpd
from time import sleep
import pytz
vtConstantMidPath = os.path.abspath(os.path.join(os.path.dirname(__file__),os.pardir,os.pardir))
sys.path.append(vtConstantMidPath)
from vtConstantMid import *
import pyqtgraph as pg
import datetime as dt          

xpower = os.path.abspath(os.path.join(os.path.dirname(__file__),os.pardir,os.pardir,os.pardir,'vnpyMidLongShort'))
sys.path.append(xpower)
from vtConstantMid import *
from eventTypeMid import *
from pyqtgraph.Qt import QtGui, QtCore

class Crosshair(object):
    """
    此类给pg.PlotWidget()添加crossHair功能
    PlotWidget实例需要初始化时传入
    根据PlotWidget的x坐标刻度依据，需要定义一个getTickDatetimeByXPosition方法
    """
    #----------------------------------------------------------------------
    def __init__(self,parent):
        """Constructor"""
        self.__view = parent
        
        super(Crosshair, self).__init__()
        self.__vLine = pg.InfiniteLine(angle=90, movable=False)
        self.__hLine = pg.InfiniteLine(angle=0, movable=False)
        self.__textPrice = pg.TextItem('price')
        self.__textDate = pg.TextItem('date')
        
        #mid 在y轴动态跟随最新价显示最新价和最新时间
        self.__textLastPrice = pg.TextItem('lastTickPrice')    
        
        view = self.__view
        
        view.addItem(self.__textDate, ignoreBounds=True)
        view.addItem(self.__textPrice, ignoreBounds=True)        
        view.addItem(self.__vLine, ignoreBounds=True)
        view.addItem(self.__hLine, ignoreBounds=True)    
        view.addItem(self.__textLastPrice, ignoreBounds=True)     
        self.proxy = pg.SignalProxy(view.scene().sigMouseMoved, rateLimit=60, slot=self.__mouseMoved)        
        
    #----------------------------------------------------------------------
    def __mouseMoved(self,evt):
        pos = evt[0]  ## using signal proxy turns original arguments into a tuple
        view = self.__view
        if not view.sceneBoundingRect().contains(pos):
            return
        mousePoint = view.plotItem.vb.mapSceneToView(pos)        
        xAxis = mousePoint.x()
        yAxis = mousePoint.y()    
        
        #mid 1)set contents to price and date lable
        self.__vLine.setPos(xAxis)
        self.__hLine.setPos(yAxis)      
        
        getTickDatetimeByXPosition = None
        if(hasattr(view, 'getTickDatetimeByXPosition')):
            getTickDatetimeByXPosition = getattr(view, 'getTickDatetimeByXPosition')
        else:
            getTickDatetimeByXPosition = self.__getTickDatetimeByXPosition

        if(not getTickDatetimeByXPosition):
            return
        tickDatetime = getTickDatetimeByXPosition(xAxis) 
        if(isinstance(tickDatetime,dt.datetime)):
            tickDatetimeStr = "%s" % (dt.datetime.strftime(tickDatetime,'%Y-%m-%d %H:%M:%S.%f'))          
        elif(isinstance(tickDatetime,float)):
            tickDatetimeStr = "%.10f" % (tickDatetime)
            #print tickDatetimeStr
        elif(isinstance(tickDatetime,str)):
            tickDatetimeStr = tickDatetime
        else:
            tickDatetime = "wrong value."
            
        
        if(True):
            self.plotLastTickLable(xAxis, yAxis, tickDatetime, yAxis)        
            
        #--------------------
        self.__textPrice.setHtml(
                            '<div style="text-align: center">\
                                <span style="color: red; font-size: 10pt;">\
                                  %0.5f\
                                </span>\
                            </div>'\
                                % (yAxis))   
        self.__textDate.setHtml(
                            '<div style="text-align: center">\
                                <span style="color: red; font-size: 10pt;">\
                                  %s\
                                </span>\
                            </div>'\
                                % (tickDatetimeStr))   
        #mid 2)get position environments
        #mid 2.1)client area rect
        rect = view.sceneBoundingRect()
        leftAxis = view.getAxis('left')
        bottomAxis = view.getAxis('bottom')            
        rectTextDate = self.__textDate.boundingRect()         
        #mid 2.2)leftAxis width,bottomAxis height and textDate height.
        leftAxisWidth = leftAxis.width()
        bottomAxisHeight = bottomAxis.height()
        rectTextDateHeight = rectTextDate.height()
        #print leftAxisWidth,bottomAxisHeight
        #mid 3)set positions of price and date lable
        topLeft = view.plotItem.vb.mapSceneToView(QtCore.QPointF(rect.left()+leftAxisWidth,rect.top()))
        bottomRight = view.plotItem.vb.mapSceneToView(QtCore.QPointF(rect.width(),rect.bottom()-(bottomAxisHeight+rectTextDateHeight)))
        self.__textDate.setPos(xAxis,bottomRight.y())
        self.__textPrice.setPos(topLeft.x(),yAxis)
        
    #----------------------------------------------------------------------
    def __getTickDatetimeByXPosition(self,xAxis):
        """mid
        默认计算方式，用datetimeNum标记x轴
        根据某个view中鼠标所在位置的x坐标获取其所在tick的time，xAxis可以是index，也可是一datetime转换而得到的datetimeNum
        return:str
        """        
        tickDatetimeRet = xAxis
        minYearDatetimeNum = mpd.date2num(dt.datetime(1900,1,1))
        if(xAxis > minYearDatetimeNum):
            tickDatetime = mpd.num2date(xAxis).astimezone(pytz.timezone('utc'))
            if(tickDatetime.year >=1900):
                tickDatetimeRet = tickDatetime 
        return tickDatetimeRet       
    
    #----------------------------------------------------------------------
    def plotLastTickLable(self,x,y,lasttime,lastprice):        
        """mid
        被嵌入的plotWidget在需要的时候通过调用此方法显示lastprice和lasttime
        比如，在每个tick到来的时候
        """
        tickDatetime,yAxis = lasttime,lastprice
        
        if(isinstance(tickDatetime,dt.datetime)):
            dateText = dt.datetime.strftime(tickDatetime,'%Y-%m-%d')
            timeText = dt.datetime.strftime(tickDatetime,'%H:%M:%S.%f')
        else:
            dateText = "not set."
            timeText = "not set."
        if(isinstance(yAxis,float)):
            priceText = "%.5f" % yAxis
        else:
            priceText = "not set."
            
        self.__textLastPrice.setHtml(
                            '<div style="text-align: center">\
                                <span style="color: red; font-size: 10pt;">\
                                  %s\
                                </span>\
                                <br>\
                                <span style="color: red; font-size: 10pt;">\
                                %s\
                                </span>\
                                <br>\
                                <span style="color: red; font-size: 10pt;">\
                                %s\
                                </span>\
                            </div>'\
                                % (priceText,timeText,dateText))             
        
        self.__textLastPrice.setPos(x,y)           

if __name__ == "__main__":  
    app = QtGui.QApplication(sys.argv)
    
    view = pg.PlotWidget()
    view.show()
    viewWithCrosshair = Crosshair(view)
    
    sys.exit(app.exec_())    
