# encoding: UTF-8

"""
这里的Demo是一个最简单的策略实现，并未考虑太多实盘中的交易细节，如：
1. 委托价格超出涨跌停价导致的委托失败
2. 委托未成交，需要撤单后重新委托
3. 断网后恢复交易状态
4. 等等
这些点是作者选择特意忽略不去实现，因此想实盘的朋友请自己多多研究CTA交易的一些细节，
做到了然于胸后再去交易，对自己的money和时间负责。
也希望社区能做出一个解决了以上潜在风险的Demo出来。
"""


from ctaBase import *
from ctaTemplate2 import CtaTemplate


import talib as ta
import numpy as np
import datetime

########################################################################
class tradeTest(CtaTemplate):
    """策略"""
    className = 'tradeTest'
    author = u'hw'


    # 策略参数
    initDays = 0   # 初始化数据所用的天数


    # 策略变量
    bar = {}
    closelist={}
    barMinute = {}
    lasttick={}

    bartime={}
    signal={}

    longsymbol=EMPTY_STRING
    shortsymbol=EMPTY_STRING
    poslimit=1
    posstate={}
    postoday={}         #今日持仓
    poslastday={}       #昨日持仓
    tradestate={}       #交易状态
    tradeid=EMPTY_STRING
    cdnum=0
    

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'fastK',
                 'slowK']    
    
    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'poslimit',
               'posstate',
               'postoday',
               'poslastday']

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(tradeTest, self).__init__(ctaEngine, setting)
        if setting :
            self.longsymbol=setting['longSymbol']
            self.shortsymbol=setting['shortSymbol']
        for vts in self.vtSymbol :
            self.tradestate[vts]=0
            self.postoday[vts]=0
            self.poslastday[vts]=0
            self.posstate[vts]=0

        self.lastOrder = None
        
    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        if self.initDays==0:
            return
        self.writeCtaLog(u'策略初始化')
        for vtsymbol in self.vtSymbol:
            initData = self.loadTick(self.initDays,vtsymbol)
            for tick in initData:
                self.onTick(tick)
        
        self.putEvent()
        
    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'策略启动')
        self.putEvent()
    
    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'macdpbx策略停止')
        self.putEvent()
    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        self.lastOrder=order


    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        # 计算K线

        tickMinute = tick.datetime.minute   #by hw

        if tick.vtSymbol in self.barMinute.keys():  #by hw
            barMinute=  self.barMinute[tick.vtSymbol]
        else:
            barMinute=EMPTY_STRING
        self.lasttick[tick.vtSymbol]=tick
        dt=datetime.datetime.strftime(tick.datetime, '%Y-%m-%d %H:%M:%S')
        #if tick.askPrice1 - tick.bidPrice1 >1:
        #    print dt,tick.vtSymbol,tick.lastPrice,tick.bidPrice1,tick.askPrice1
        #撤单判断与执行,待修改


        if tickMinute != barMinute:
            if tick.vtSymbol in self.bar.keys():      #by hw
                self.onBar(self.bar[tick.vtSymbol])    #by hw
            
            bar = CtaBarData()              
            bar.vtSymbol = tick.vtSymbol
            bar.symbol = tick.symbol
            bar.exchange = tick.exchange
            
            bar.open = tick.lastPrice
            bar.high = tick.lastPrice
            bar.low = tick.lastPrice
            bar.close = tick.lastPrice
            
            bar.date = tick.date
            bar.time = tick.time
            bar.datetime = tick.datetime    # K线的时间设为第一个Tick的时间
            
            # 实盘中用不到的数据可以选择不算，从而加快速度
            #bar.volume = tick.volume
            #bar.openInterest = tick.openInterest
            
            self.bar[tick.vtSymbol] = bar                  # 这种写法为了减少一层访问，加快速度 by hw
            self.barMinute[tick.vtSymbol] = tickMinute     # 更新当前的分钟 by hw
            self.bartime[tick.vtSymbol] = tick.datetime
        else:                               # 否则继续累加新的K线
            bar = self.bar[tick.vtSymbol]                  # 写法同样为了加快速度
            
            bar.high = max(bar.high, tick.lastPrice)
            bar.low = min(bar.low, tick.lastPrice)
            bar.close = tick.lastPrice
        
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""

        #计算基础变量macd，pbx .by hw
        vtsymbol=bar.vtSymbol
        if vtsymbol in self.closelist.keys():
            l=self.closelist[vtsymbol]
        else:
            l=[]
            self.closelist[vtsymbol]=l

        l.append(bar.close)


        self.writeCtaLog(u'symbol:%s' %bar.vtSymbol)
        #策略信号
        longsignal=False
        shortsignal=False
        sellsignal=False
        coversignal=False

        for vts in self.vtSymbol :
            print 'signal:',vts,self.vtSymbol,self.bar[vts].datetime.hour,self.longsymbol,self.shortsymbol, self.postoday[vts], self.bar[vts].datetime.minute
            if self.postoday[vts]== 0 and cmp(vts,self.longsymbol)   and self.bar[vts].datetime.hour >=14 and self.bar[vts].datetime.minute <50 :
                longsignal=True
                #print longsignal
            if self.postoday[vts]== 0 and vts==self.shortsymbol and self.bar[vts].datetime.hour >=14 and self.bar[vts].datetime.minute <50:
                shortsignal=True

            if self.postoday[vts]== 1 and vts==self.longsymbol and self.bar[vts].datetime.hour >=14 and self.bar[vts].datetime.minute >50 :
                sellsignal=True

            if self.postoday[vts]== -1 and vts==self.shortsymbol and self.bar[vts].datetime.hour >=14 and self.bar[vts].datetime.minute >50 :
                coversignal=True

        # 金叉和死叉的条件是互斥
        # 所有的委托均以K线收盘价委托（这里有一个实盘中无法成交的风险，考虑添加对模拟市价单类型的支持）
        print longsignal,shortsignal,self.postoday[self.longsymbol],self.postoday[self.shortsymbol],self.tradestate[self.longsymbol],self.tradestate[self.shortsymbol]
        if sellsignal and self.postoday[self.longsymbol]==1 and self.tradestate[self.longsymbol]<> -1 :

            self.tradeid=self.sell(self.bar[self.longsymbol].close, 1,self.longsymbol)
            self.tradestate[self.longsymbol]=-1
            print 'trade 1'
        if coversignal and self.postoday[self.shortsymbol]==-1 and self.tradestate[self.shortsymbol]<> 1  :

            self.tradeid=self.cover(self.bar[self.shortsymbol].close, 1,self.shortsymbol)
            self.tradestate[self.shortsymbol]=1
            print 'trade 2'
        if longsignal and self.tradestate[self.longsymbol]<>1 :

            self.tradeid=self.buy(self.bar[self.longsymbol].close, 1,self.longsymbol)
            self.tradestate[self.longsymbol]=1
            print 'trade 3'
        if shortsignal and self.tradestate[self.shortsymbol]<>-1   :

            self.tradeid=self.short(self.bar[self.shortsymbol].close, 1,self.shortsymbol)
            self.tradestate[self.shortsymbol]=-1
            print 'trade 4'


                
        # 发出状态更新事件
        self.putEvent()

    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        pass
    
    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder

        self.postoday[trade.vtSymbol]=self.postoday[trade.vtSymbol]+self.tradestate[trade.vtSymbol]
        self.tradestate[trade.vtSymbol]=0
        print 'trade',trade.vtSymbol,self.postoday[trade.vtSymbol],self.tradestate[trade.vtSymbol]
    
########################################################################################
class OrderManagementDemo(CtaTemplate):
    """基于tick级别细粒度撤单追单测试demo"""
    
    className = 'OrderManagementDemo'
    author = u'用Python的交易员'
    
    # 策略参数
    initDays = 10   # 初始化数据所用的天数
    
    # 策略变量
    bar = None
    barMinute = EMPTY_STRING
    
    
    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol']
    
    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos']

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(OrderManagementDemo, self).__init__(ctaEngine, setting)
                
        self.lastOrder = None
        self.orderType = ''
        
    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双EMA演示策略初始化')
        
        initData = self.loadBar(self.initDays)
        for bar in initData:
            self.onBar(bar)
        
        self.putEvent()
        
    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双EMA演示策略启动')
        self.putEvent()
    
    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'双EMA演示策略停止')
        self.putEvent()
        
    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""

        # 建立不成交买单测试单        
        if self.lastOrder == None:
            self.buy(tick.lastprice - 10.0, 1)

        # CTA委托类型映射
        if self.lastOrder != None and self.lastOrder.direction == u'多' and self.lastOrder.offset == u'开仓':
            self.orderType = u'买开'

        elif self.lastOrder != None and self.lastOrder.direction == u'多' and self.lastOrder.offset == u'平仓':
            self.orderType = u'买平'

        elif self.lastOrder != None and self.lastOrder.direction == u'空' and self.lastOrder.offset == u'开仓':
            self.orderType = u'卖开'

        elif self.lastOrder != None and self.lastOrder.direction == u'空' and self.lastOrder.offset == u'平仓':
            self.orderType = u'卖平'
                
        # 不成交，即撤单，并追单
        if self.lastOrder != None and self.lastOrder.status == u'未成交':

            self.cancelOrder(self.lastOrder.vtOrderID)
            self.lastOrder = None
        elif self.lastOrder != None and self.lastOrder.status == u'已撤销':
        # 追单并设置为不能成交
            
            self.sendOrder(self.orderType, self.tick.lastprice - 10, 1)
            self.lastOrder = None
            
    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        pass
    
    #----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        self.lastOrder = order
    
    #----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        pass
