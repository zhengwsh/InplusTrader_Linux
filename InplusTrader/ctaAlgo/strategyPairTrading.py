# encoding: UTF-8

"""
created by vinson zheng
"""

from ctaBase import *
from ctaTemplate import CtaTemplate
import numpy as np


########################################################################
class strategyPairTrading(CtaTemplate):
    """期货配对交易策略Demo"""
    className = 'strategyPairTrading'
    author = u'Vinson Zheng'
    
    # 策略参数
    initDays = 10   # 初始化数据所用的天数
    ratio = 15   # 对冲手数,通过研究历史数据进行价格序列回归得到该值
    entry_score = 2   # 入场临界值
    window = 60  # 滚动窗口
    
    # 策略变量
    bar_a = None
    bar_b = None
    barMinute_a = EMPTY_STRING
    barMinute_b = EMPTY_STRING
    counter = 0    # 每日开盘前将计数器清零
    up_cross_up_limit = False
    down_cross_down_limit = False
    bars_a = [] # 记录当日分钟bar
    bars_b = []
    price_a = 0
    price_b = 0
    
    pos = {}  # 各合约持仓情况, 通过vtSymbol映射！！！ pos['cu1704']["long"]
    # 同时继承Template共有变量值串了，搞死人啊，bug要爆炸

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbols',
                 'ratio',
                 'entry_score',
                 'window']
    
    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos',
               'counter',
               'price_a',
               'price_b',
               'up_cross_up_limit',
               'down_cross_down_limit']

    #----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        super(strategyPairTrading, self).__init__(ctaEngine, setting)
        
        # 注意策略类中的可变对象属性（通常是list和dict等），在策略初始化时需要重新创建，
        # 否则会出现多个策略实例之间数据共享的情况，有可能导致潜在的策略逻辑错误风险，
        # 策略类中的这些可变对象属性可以选择不写，全都放在__init__下面，写主要是为了阅读
        # 策略时方便（更多是个编程习惯的选择）
        # operator------------------------------------
        # 所有的委托均以K线收盘价委托（这里有一个实盘中无法成交的风险，考虑添加对模拟市价单类型的支持）
        #self.buy(vtSymbol, bar.close, 1) #做多
        #self.cover(vtSymbol, bar.close, 1) #平空
        #self.short(vtSymbol, bar.close, 1) #做空
        #self.sell(vtSymbol, bar.close, 1) #平多

        
    #----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        self.writeCtaLog(u'配对交易演示策略初始化')
        self.putEvent()
    
    #----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        self.trading = True
        self.writeCtaLog(u'配对交易演示策略启动')
        self.putEvent()
    
    #----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        self.writeCtaLog(u'配对交易演示策略停止')
        self.trading = False
        self.putEvent()
        
    #----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        #print 'tickSymbol:'+tick.vtSymbol+' tickDateTime:'+tick.date+' '+tick.time+' tickClose:'+str(tick.lastPrice)

        # 计算分钟K线
        tickMinute = tick.datetime.minute

        if tick.vtSymbol == self.vtSymbols[0]:
            if tickMinute != self.barMinute_a:    
                if self.bar_a:
                    self.onBar(self.bar_a)
                
                bar_a = CtaBarData()              
                bar_a.vtSymbol = tick.vtSymbol
                bar_a.symbol = tick.symbol
                bar_a.exchange = tick.exchange
                
                bar_a.open = tick.lastPrice
                bar_a.high = tick.lastPrice
                bar_a.low = tick.lastPrice
                bar_a.close = tick.lastPrice
                
                bar_a.date = tick.date
                bar_a.time = tick.time
                bar_a.datetime = tick.datetime    # K线的时间设为第一个Tick的时间
                
                # 实盘中用不到的数据可以选择不算，从而加快速度
                #bar_a.volume = tick.volume
                #bar_a.openInterest = tick.openInterest
                
                self.bar_a = bar_a                  # 这种写法为了减少一层访问，加快速度
                self.barMinute_a = tickMinute     # 更新当前的分钟
                
            else:                               # 否则继续累加新的K线
                bar_a = self.bar_a                  # 写法同样为了加快速度
                
                bar_a.high = max(bar_a.high, tick.lastPrice)
                bar_a.low = min(bar_a.low, tick.lastPrice)
                bar_a.close = tick.lastPrice
        
        elif tick.vtSymbol == self.vtSymbols[1]:
            if tickMinute != self.barMinute_b:    
                if self.bar_b:
                    self.onBar(self.bar_b)
                
                bar_b = CtaBarData()              
                bar_b.vtSymbol = tick.vtSymbol
                bar_b.symbol = tick.symbol
                bar_b.exchange = tick.exchange
                
                bar_b.open = tick.lastPrice
                bar_b.high = tick.lastPrice
                bar_b.low = tick.lastPrice
                bar_b.close = tick.lastPrice
                
                bar_b.date = tick.date
                bar_b.time = tick.time
                bar_b.datetime = tick.datetime    # K线的时间设为第一个Tick的时间
                
                # 实盘中用不到的数据可以选择不算，从而加快速度
                #bar_b.volume = tick.volume
                #bar_b.openInterest = tick.openInterest
                
                self.bar_b = bar_b                  # 这种写法为了减少一层访问，加快速度
                self.barMinute_b = tickMinute     # 更新当前的分钟
                
            else:                               # 否则继续累加新的K线
                bar_b = self.bar_b                  # 写法同样为了加快速度
                
                bar_b.high = max(bar_b.high, tick.lastPrice)
                bar_b.low = min(bar_b.low, tick.lastPrice)
                bar_b.close = tick.lastPrice

    #----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        print 'barSymbol:'+bar.vtSymbol+' barDateTime:'+bar.date+' '+bar.time+' barClose:'+str(bar.close)
        print self.vtSymbols[0] + " pos long : " + str(self.pos[self.vtSymbols[0]]["long"]) + " pos short : " + str(self.pos[self.vtSymbols[0]]["short"])
        print self.vtSymbols[1] + " pos long : " + str(self.pos[self.vtSymbols[1]]["long"]) + " pos short : " + str(self.pos[self.vtSymbols[1]]["short"])
        """
        # testing
        if self.trading:
            if bar.vtSymbol == self.vtSymbols[0]:
                self.buy(bar.vtSymbol, bar.close, 1)
            if bar.vtSymbol == self.vtSymbols[1]:
                self.short(bar.vtSymbol, bar.close, 1)
        """

        
        if bar.vtSymbol == self.vtSymbols[0]:
            self.price_a = bar.close
        if bar.vtSymbol == self.vtSymbols[1]:
            self.price_b = bar.close

        # 当累积满一定数量的bar数据时候,进行交易逻辑的判断
        if self.counter > 2 * self.window:

            # 获取当天历史分钟线价格队列
            price_array_a = np.array(self.bars_a[-self.window:])
            price_array_b = np.array(self.bars_b[-self.window:])

            # 计算价差序列、其标准差、均值、上限、下限
            spread_array = price_array_a - self.ratio * price_array_b
            std = np.std(spread_array)
            mean = np.mean(spread_array)
            up_limit = mean + self.entry_score * std
            down_limit = mean - self.entry_score * std

            # 获取各合约当前bar对应合约的收盘价格并计算价差
            # 获取各合约仓位
            if bar.vtSymbol == self.vtSymbols[0]:
                self.price_a = bar.close
                pabq = self.pos[bar.vtSymbol]["long"]  # 多头持仓
                pasq = -self.pos[bar.vtSymbol]["short"] # 空头持仓
            
            if bar.vtSymbol == self.vtSymbols[1]:
                self.price_b = bar.close
                pbbq = self.pos[bar.vtSymbol]["long"]  # 多头持仓
                pbsq = -self.pos[bar.vtSymbol]["short"] # 空头持仓
            
            spread = self.price_a - self.ratio * self.price_b

            # 如果价差低于预先计算得到的下限,则为建仓信号,'买入'价差合约
            if spread <= down_limit and not self.down_cross_down_limit:
                print ('spread: {}, mean: {}, down_limit: {}'.format(spread, mean, down_limit))
                print ('创建买入价差中...')

                # 获取当前剩余的应建仓的数量
                qty_a = 1 - pabq
                qty_b = self.ratio - pbsq

                # 由于存在成交不超过下一bar成交量25%的限制,所以可能要通过多次发单成交才能够成功建仓
                if qty_a > 0:
                    self.buy(self.vtSymbols[0], bar.close, qty_a) #做多
                if qty_b > 0:
                    self.short(self.vtSymbols[1], bar.close, qty_b) #做空
                if qty_a == 0 and qty_b == 0:
                    # 已成功建立价差的'多仓'
                    self.down_cross_down_limit = True
                    print ('买入价差仓位创建成功!')

            # 如果价差向上回归移动平均线,则为平仓信号
            if spread >= mean and self.down_cross_down_limit:
                print ('spread: {}, mean: {}, down_limit: {}'.format(spread, mean, down_limit))
                print ('对买入价差仓位进行平仓操作中...')

                # 由于存在成交不超过下一bar成交量25%的限制,所以可能要通过多次发单成交才能够成功建仓
                qty_a = pabq
                qty_b = pbsq
                if qty_a > 0:
                    self.sell(self.vtSymbols[0], bar.close, qty_a) #平多
                if qty_b > 0:
                    self.cover(self.vtSymbols[1], bar.close, qty_b) #平空
                if qty_a == 0 and qty_b == 0:
                    self.down_cross_down_limit = False
                    print ('买入价差仓位平仓成功!')

            # 如果价差高于预先计算得到的上限,则为建仓信号,'卖出'价差合约
            if spread >= up_limit and not self.up_cross_up_limit:
                print ('spread: {}, mean: {}, up_limit: {}'.format(spread, mean, up_limit))
                print ('创建卖出价差中...')
                qty_a = 1 - pasq
                qty_b = self.ratio - pbbq
                if qty_a > 0:
                    self.short(self.vtSymbols[0], bar.close, qty_a) #做空
                if qty_b > 0:
                    self.buy(self.vtSymbols[1], bar.close, qty_b) #做多
                if qty_a == 0 and qty_b == 0:
                    self.up_cross_up_limit = True
                    print ('卖出价差仓位创建成功')

            # 如果价差向下回归移动平均线,则为平仓信号
            if spread < mean and self.up_cross_up_limit:
                print ('spread: {}, mean: {}, up_limit: {}'.format(spread, mean, up_limit))
                print ('对卖出价差仓位进行平仓操作中...')
                qty_a = pasq
                qty_b = pbbq
                if qty_a > 0:
                    self.cover(self.vtSymbols[0], bar.close, qty_a) #平空
                if qty_b > 0:
                    self.sell(self.vtSymbols[1], bar.close, qty_b) #平多
                if qty_a == 0 and qty_b == 0:
                    self.up_cross_up_limit = False
                    print ('卖出价差仓位平仓成功!')
        
        if bar.vtSymbol == self.vtSymbols[0]:
            self.bars_a.append(bar.close)
        if bar.vtSymbol == self.vtSymbols[1]:
            self.bars_b.append(bar.close)

        self.counter += 1

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
        pass
    