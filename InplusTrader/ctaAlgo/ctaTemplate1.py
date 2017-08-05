# encoding: UTF-8

'''
本文件包含了CTA引擎中的策略开发用模板，开发策略时需要继承CtaTemplate类。
'''
import datetime
import copy
from ctaBase import *
from vtConstant import *
from vtGateway import *


########################################################################
class CtaTemplate1(object):
    """CTA策略模板"""

    # 策略类的名称和作者
    name = EMPTY_UNICODE  # 策略实例名称
    className = 'CtaTemplate1'
    author = EMPTY_UNICODE

    # MongoDB数据库的名称，K线数据库默认为1分钟
    tickDbName = TICK_DB_NAME
    barDbName = MINUTE_DB_NAME

    productClass = EMPTY_STRING  # 产品类型（只有IB接口需要）
    currency = EMPTY_STRING  # 货币（只有IB接口需

    # 策略的基本参数
    vtSymbol = EMPTY_STRING  # 交易的合约vt系统代码
    vtSymbol1 = EMPTY_STRING  # 交易的合约2vt系统代码

    # 策略的基本变量，由引擎管理
    inited = False  # 是否进行了初始化
    trading = False  # 是否启动交易，由引擎管理
    backtesting = False  # 回测模式

    pos = 0  # 总投机方向
    pos1 = 0  # 总投机方向

    tpos0L = 0  # 今持多仓
    tpos0S = 0  # 今持空仓
    ypos0L = 0  # 昨持多仓
    ypos0S = 0  # 昨持空仓

    tpos1L = 0  # 今持多仓
    tpos1S = 0  # 今持空仓
    ypos1L = 0  # 昨持多仓
    ypos1S = 0  # 昨持空仓

    # 参数列表，保存了参数的名称
    paramList = ['name',
                 'className',
                 'author',
                 'vtSymbol',
                 'vtSymbol1']

    # 变量列表，保存了变量的名称
    varList = ['inited',
               'trading',
               'pos']

    # ----------------------------------------------------------------------
    def __init__(self, ctaEngine, setting):
        """Constructor"""
        self.ctaEngine = ctaEngine

        # 策略的基本变量，由引擎管理
        self.inited = False  # 是否进行了初始化
        self.trading = False  # 是否启动交易，由引擎管理
        self.backtesting = False  # 回测模式

        self.pos = 0  # 总投机方向
        self.pos1 = 0  # 总投机方向

        self.tpos0L = 0  # 今持多仓
        self.tpos0S = 0  # 今持空仓
        self.ypos0L = 0  # 昨持多仓
        self.ypos0S = 0  # 昨持空仓

        self.tpos1L = 0  # 今持多仓
        self.tpos1S = 0  # 今持空仓
        self.ypos1L = 0  # 昨持多仓
        self.ypos1S = 0  # 昨持空仓

        # 设置策略的参数
        if setting:
            d = self.__dict__
            for key in self.paramList:
                if key in setting:
                    d[key] = setting[key]

    # ----------------------------------------------------------------------
    def onInit(self):
        """初始化策略（必须由用户继承实现）"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def onUpdate(self, setting):
        """刷新策略"""
        if setting:
            d = self.__dict__
            for key in self.paramList:
                if key in setting:
                    d[key] = setting[key]

    # ----------------------------------------------------------------------
    def onStart(self):
        """启动策略（必须由用户继承实现）"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def onStop(self):
        """停止策略（必须由用户继承实现）"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def confSettle(self, vtSymbol):
        """确认结算信息"""
        self.ctaEngine.confSettle(vtSymbol)

    # ----------------------------------------------------------------------
    def onTick(self, tick):
        """收到行情TICK推送（必须由用户继承实现）"""
        if not self.backtesting:
            hour = datetime.datetime.now().hour
            if hour >= 16 and hour <= 19:
                return
            if hour >= 2 and hour <= 7:
                return
            if hour >= 12 and hour <= 12:
                return
            if tick.datetime.hour == 20 and tick.datetime.minute == 59:
                self.output(u'开始确认结算信息')
                self.confSettle(self.vtSymbol)
        if tick.datetime.hour == 20 and tick.datetime.minute == 59:
            self.ypos0L += self.tpos0L
            self.tpos0L = 0
            self.ypos0S += self.tpos0S
            self.tpos0S = 0
            self.ypos1L += self.tpos1L
            self.tpos1L = 0
            self.ypos1S += self.tpos1S
            self.tpos1S = 0

    # ----------------------------------------------------------------------
    def onBar(self, bar):
        """收到Bar推送（必须由用户继承实现）"""
        raise NotImplementedError

    # ----------------------------------------------------------------------
    def onOrder(self, order):
        """收到委托变化推送（必须由用户继承实现）"""
        pass

    # ----------------------------------------------------------------------
    def onTrade(self, trade):
        """收到成交推送（必须由用户继承实现）"""
        # 对于无需做细粒度委托控制的策略，可以忽略onOrder
        # CTA委托类型映射
        if trade != None and trade.direction == u'多':
            if trade.vtSymbol == self.vtSymbol:
                self.pos += trade.volume
            elif trade.vtSymbol == self.vtSymbol1:
                self.pos1 += trade.volume
        if trade != None and trade.direction == u'空':
            if trade.vtSymbol == self.vtSymbol:
                self.pos -= trade.volume
            elif trade.vtSymbol == self.vtSymbol1:
                self.pos1 -= trade.volume
        if trade != None and trade.direction == u'多' and trade.offset == u'开仓':
            if trade.vtSymbol == self.vtSymbol:
                self.tpos0L += trade.volume
            elif trade.vtSymbol == self.vtSymbol1:
                self.tpos1L += trade.volume
        elif trade != None and trade.direction == u'空' and trade.offset == u'开仓':
            if trade.vtSymbol == self.vtSymbol:
                self.tpos0S += trade.volume
            elif trade.vtSymbol == self.vtSymbol1:
                self.tpos1S += trade.volume
        elif trade != None and trade.direction == u'多' and trade.offset == u'平仓':
            if trade.vtSymbol == self.vtSymbol:
                self.ypos0S -= trade.volume
            elif trade.vtSymbol == self.vtSymbol1:
                self.ypos1S -= trade.volume
        elif trade != None and trade.direction == u'多' and trade.offset == u'平今':
            if trade.vtSymbol == self.vtSymbol:
                self.tpos0S -= trade.volume
            elif trade.vtSymbol == self.vtSymbol1:
                self.tpos1S -= trade.volume
        elif trade != None and trade.direction == u'多' and trade.offset == u'平昨':
            if trade.vtSymbol == self.vtSymbol:
                self.ypos0S -= trade.volume
            elif trade.vtSymbol == self.vtSymbol1:
                self.ypos1S -= trade.volume
        elif trade != None and trade.direction == u'空' and trade.offset == u'平仓':
            if trade.vtSymbol == self.vtSymbol:
                self.ypos0L -= trade.volume
            elif trade.vtSymbol == self.vtSymbol1:
                self.ypos1L -= trade.volume
        elif trade != None and trade.direction == u'空' and trade.offset == u'平今':
            if trade.vtSymbol == self.vtSymbol:
                self.tpos0L -= trade.volume
            elif trade.vtSymbol == self.vtSymbol1:
                self.tpos1L -= trade.volume
        elif trade != None and trade.direction == u'空' and trade.offset == u'平昨':
            if trade.vtSymbol == self.vtSymbol:
                self.ypos0L -= trade.volume
            elif trade.vtSymbol == self.vtSymbol1:
                self.ypos1L -= trade.volume

    # ----------------------------------------------------------------------
    def buy(self, price, volume, stop=False):
        """买开"""
        return self.sendOrder(CTAORDER_BUY, price, volume, stop)

    # ----------------------------------------------------------------------
    def sell(self, price, volume, stop=False):
        """卖平"""
        t_vol = 0
        y_vol = 0
        t_vol = min(volume, self.tpos0L)
        y_vol = volume - t_vol
        orderId = None
        orderId1 = None
        orderIds = []
        if t_vol > 0:
            orderId = self.sendOrder(CTAORDER_SELL_TODAY, price, t_vol, stop)
        if t_vol == 0 and y_vol > 0:
            orderId1 = self.sendOrder(CTAORDER_SELL, price, y_vol, stop)
        if orderId:
            orderIds.append(orderId)
        if orderId1:
            orderIds.append(orderId1)
        return orderIds

    # ----------------------------------------------------------------------
    def sell_y(self, price, volume, stop=False):
        """卖平"""
        return self.sendOrder(CTAORDER_SELL, price, volume, stop)

    def sell_t(self, price, volume, stop=False):
        """卖平"""
        return self.sendOrder(CTAORDER_SELL_TODAY, price, volume, stop)

    # ----------------------------------------------------------------------
    def sell1_y(self, price, volume, stop=False):
        """卖平"""
        return self.sendOrder1(CTAORDER_SELL, price, volume, stop)

    def sell1_t(self, price, volume, stop=False):
        """卖平"""
        return self.sendOrder1(CTAORDER_SELL_TODAY, price, volume, stop)

    # ----------------------------------------------------------------------
    def short(self, price, volume, stop=False):
        """卖开"""
        return self.sendOrder(CTAORDER_SHORT, price, volume, stop)

    # ----------------------------------------------------------------------
    def cover(self, price, volume, stop=False):
        """买平"""
        t_vol = 0
        y_vol = 0
        t_vol = min(volume, self.tpos0S)
        y_vol = volume - t_vol
        orderId = None
        orderId1 = None
        orderIds = []
        if t_vol > 0:
            orderId = self.sendOrder(CTAORDER_COVER_TODAY, price, t_vol, stop)
        if t_vol == 0 and y_vol > 0:
            orderId1 = self.sendOrder(CTAORDER_COVER, price, y_vol, stop)
        if orderId:
            orderIds.append(orderId)
        if orderId1:
            orderIds.append(orderId1)
        return orderIds

    # ----------------------------------------------------------------------
    def cover_y(self, price, volume, stop=False):
        """买平"""
        return self.sendOrder(CTAORDER_COVER, price, volume, stop)

    # ----------------------------------------------------------------------
    def cover_t(self, price, volume, stop=False):
        """买平"""
        return self.sendOrder(CTAORDER_COVER_TODAY, price, volume, stop)

    # ----------------------------------------------------------------------
    def cover1_y(self, price, volume, stop=False):
        """买平"""
        return self.sendOrder1(CTAORDER_COVER, price, volume, stop)

    # ----------------------------------------------------------------------
    def cover1_t(self, price, volume, stop=False):
        """买平"""
        return self.sendOrder1(CTAORDER_COVER_TODAY, price, volume, stop)

    # ----------------------------------------------------------------------
    def buy_fok(self, price, volume, stop=False):
        """买开"""
        return self.sendOrderFOK(CTAORDER_BUY, price, volume, stop)

    # ----------------------------------------------------------------------
    def sell_fok(self, price, volume, stop=False):
        """卖平"""
        t_vol = 0
        y_vol = 0
        t_vol = min(volume, self.tpos0L)
        y_vol = volume - t_vol
        orderId = None
        orderId1 = None
        orderIds = []
        if t_vol > 0:
            orderId = self.sendOrderFOK(CTAORDER_SELL_TODAY, price, t_vol, stop)
        if t_vol == 0 and y_vol > 0:
            orderId1 = self.sendOrderFOK(CTAORDER_SELL, price, y_vol, stop)
        if orderId:
            orderIds.append(orderId)
        if orderId1:
            orderIds.append(orderId1)
        return orderIds

    # ----------------------------------------------------------------------
    def short_fok(self, price, volume, stop=False):
        """卖开"""
        return self.sendOrderFOK(CTAORDER_SHORT, price, volume, stop)

    # ----------------------------------------------------------------------
    def cover_fok(self, price, volume, stop=False):
        """买平"""
        t_vol = 0
        y_vol = 0
        t_vol = min(volume, self.tpos0S)
        y_vol = volume - t_vol
        if t_vol <= 0 and y_vol <= 0:
            self.output("买平出错")
        orderId = None
        orderId1 = None
        orderIds = []
        if t_vol > 0:
            orderId = self.sendOrderFOK(CTAORDER_COVER_TODAY, price, t_vol, stop)
        if t_vol == 0 and y_vol > 0:
            orderId1 = self.sendOrderFOK(CTAORDER_COVER, price, y_vol, stop)
        if orderId:
            orderIds.append(orderId)
        if orderId1:
            orderIds.append(orderId1)
        return orderIds

    # ----------------------------------------------------------------------
    def buy_fak(self, price, volume, stop=False):
        """买开"""
        return self.sendOrderFAK(CTAORDER_BUY, price, volume, stop)

    # ----------------------------------------------------------------------
    def sell_fak(self, price, volume, stop=False):
        """卖平"""
        t_vol = 0
        y_vol = 0
        t_vol = min(volume, self.tpos0L)
        y_vol = volume - t_vol
        if t_vol <= 0 and y_vol <= 0:
            self.output("卖平出错")
        orderId = None
        orderId1 = None
        orderIds = []
        if t_vol > 0:
            orderId = self.sendOrderFAK(CTAORDER_SELL_TODAY, price, t_vol, stop)
        if t_vol == 0 and y_vol > 0:
            orderId1 = self.sendOrderFAK(CTAORDER_SELL, price, y_vol, stop)
        if orderId:
            orderIds.append(orderId)
        if orderId1:
            orderIds.append(orderId1)
        return orderIds

    # ----------------------------------------------------------------------
    def short_fak(self, price, volume, stop=False):
        """卖开"""
        return self.sendOrderFAK(CTAORDER_SHORT, price, volume, stop)

    # ----------------------------------------------------------------------
    def cover_fak(self, price, volume, stop=False):
        """买平"""
        t_vol = 0
        y_vol = 0
        t_vol = min(volume, self.tpos0S)
        y_vol = volume - t_vol
        if t_vol <= 0 and y_vol <= 0:
            self.output("买平出错")
        orderId = None
        orderId1 = None
        orderIds = []
        if t_vol > 0:
            orderId = self.sendOrder_FAK(CTAORDER_COVER_TODAY, price, t_vol, stop)
        if t_vol == 0 and y_vol > 0:
            orderId1 = self.sendOrder_FAK(CTAORDER_COVER, price, y_vol, stop)
        if orderId:
            orderIds.append(orderId)
        if orderId1:
            orderIds.append(orderId1)
        return orderIds

    # ----------------------------------------------------------------------
    def sendOrder(self, orderType, price, volume, stop=False):
        """发送委托"""
        if self.trading:
            # 如果stop为True，则意味着发本地停止单
            if stop:
                vtOrderID = self.ctaEngine.sendStopOrder(self.vtSymbol, orderType, price, volume, self)
            else:
                vtOrderID = self.ctaEngine.sendOrder(self.vtSymbol, orderType, price, volume, self)
            return vtOrderID
        else:
            return ''

        # ----------------------------------------------------------------------

    def sendOrderFOK(self, orderType, price, volume, stop=False):
        """发送委托"""
        if self.trading:
            # 如果stop为True，则意味着发本地停止单
            if stop:
                vtOrderID = self.ctaEngine.sendStopOrder(self.vtSymbol, orderType, price, volume, self)
            else:
                vtOrderID = self.ctaEngine.sendOrderFOK(self.vtSymbol, orderType, price, volume, self)
            return vtOrderID
        else:
            return ''

        # ----------------------------------------------------------------------

    def sendOrderFAK(self, orderType, price, volume, stop=False):
        """发送委托"""
        if self.trading:
            # 如果stop为True，则意味着发本地停止单
            if stop:
                vtOrderID = self.ctaEngine.sendStopOrder(self.vtSymbol, orderType, price, volume, self)
            else:
                vtOrderID = self.ctaEngine.sendOrderFAK(self.vtSymbol, orderType, price, volume, self)
            return vtOrderID
        else:
            return ''


        # ----------------------------------------------------------------------

    def buy1(self, price, volume, stop=False):
        """买开"""
        return self.sendOrder1(CTAORDER_BUY, price, volume, stop)

    # ----------------------------------------------------------------------
    def sell1(self, price, volume, stop=False):
        """卖平"""
        t_vol = 0
        y_vol = 0
        t_vol = min(volume, self.tpos1L)
        y_vol = volume - t_vol
        orderId = None
        orderId1 = None
        orderIds = []
        if t_vol > 0:
            orderId = self.sendOrder1(CTAORDER_SELL_TODAY, price, t_vol, stop)
        if t_vol == 0 and y_vol > 0:
            orderId1 = self.sendOrder1(CTAORDER_SELL, price, y_vol, stop)
        if orderId:
            orderIds.append(orderId)
        if orderId1:
            orderIds.append(orderId1)
        return orderIds

    # ----------------------------------------------------------------------
    def short1(self, price, volume, stop=False):
        """卖开"""
        return self.sendOrder1(CTAORDER_SHORT, price, volume, stop)

    # ----------------------------------------------------------------------
    def cover1(self, price, volume, stop=False):
        """买平"""
        t_vol = 0
        y_vol = 0
        t_vol = min(volume, self.tpos1S)
        y_vol = volume - t_vol
        orderId = None
        orderId1 = None
        orderIds = []
        if t_vol > 0:
            orderId = self.sendOrder1(CTAORDER_COVER_TODAY, price, t_vol, stop)
        if t_vol == 0 and y_vol > 0:
            orderId1 = self.sendOrder1(CTAORDER_COVER, price, y_vol, stop)
        if orderId:
            orderIds.append(orderId)
        if orderId1:
            orderIds.append(orderId1)
        return orderIds

    # ----------------------------------------------------------------------
    def buy1_fok(self, price, volume, stop=False):
        """买开"""
        return self.sendOrder1FOK(CTAORDER_BUY, price, volume, stop)

    # ----------------------------------------------------------------------
    def sell1_fok(self, price, volume, stop=False):
        """卖平"""
        t_vol = 0
        y_vol = 0
        t_vol = min(volume, self.tpos1L)
        y_vol = volume - t_vol
        orderId = None
        orderId1 = None
        orderIds = []
        if t_vol > 0:
            orderId = self.sendOrder1FOK(CTAORDER_SELL_TODAY, price, t_vol, stop)
        if t_vol == 0 and y_vol > 0:
            orderId1 = self.sendOrder1FOK(CTAORDER_SELL, price, y_vol, stop)
        if orderId:
            orderIds.append(orderId)
        if orderId1:
            orderIds.append(orderId1)
        return orderIds

    # ----------------------------------------------------------------------
    def short1_fok(self, price, volume, stop=False):
        """卖开"""
        return self.sendOrder1FOK(CTAORDER_SHORT, price, volume, stop)

    # ----------------------------------------------------------------------
    def cover1_fok(self, price, volume, stop=False):
        """买平"""
        t_vol = 0
        y_vol = 0
        t_vol = min(volume, self.tpos1S)
        y_vol = volume - t_vol
        orderId = None
        orderId1 = None
        orderIds = []
        if t_vol > 0:
            orderId = self.sendOrder1FOK(CTAORDER_COVER_TODAY, price, t_vol, stop)
        if t_vol == 0 and y_vol > 0:
            orderId1 = self.sendOrder1FOK(CTAORDER_COVER, price, y_vol, stop)
        if orderId:
            orderIds.append(orderId)
        if orderId1:
            orderIds.append(orderId1)
        return orderIds

    # ----------------------------------------------------------------------
    def buy1_fak(self, price, volume, stop=False):
        """买开"""
        return self.sendOrder1FAK(CTAORDER_BUY, price, volume, stop)

    # ----------------------------------------------------------------------
    def sell1_fak(self, price, volume, stop=False):
        """卖平"""
        t_vol = 0
        y_vol = 0
        t_vol = min(volume, self.tpos1L)
        y_vol = volume - t_vol
        orderId = None
        orderId1 = None
        orderIds = []
        if t_vol > 0:
            orderId = self.sendOrder1FAK(CTAORDER_SELL_TODAY, price, t_vol, stop)
        if t_vol == 0 and y_vol > 0:
            orderId1 = self.sendOrder1FAK(CTAORDER_SELL, price, y_vol, stop)
        if orderId:
            orderIds.append(orderId)
        if orderId1:
            orderIds.append(orderId1)
        return orderIds

    # ----------------------------------------------------------------------
    def short1_fak(self, price, volume, stop=False):
        """卖开"""
        return self.sendOrder1FAK(CTAORDER_SHORT, price, volume, stop)

    # ----------------------------------------------------------------------
    def cover1_fak(self, price, volume, stop=False):
        """买平"""
        t_vol = 0
        y_vol = 0
        t_vol = min(volume, self.tpos1S)
        y_vol = volume - t_vol
        orderId = None
        orderId1 = None
        orderIds = []
        if t_vol > 0:
            orderId = self.sendOrder1FAK(CTAORDER_COVER_TODAY, price, t_vol, stop)
        if t_vol == 0 and y_vol > 0:
            orderId1 = self.sendOrder1FAK(CTAORDER_COVER, price, y_vol, stop)
        if orderId:
            orderIds.append(orderId)
        if orderId1:
            orderIds.append(orderId1)
        return orderIds

    # ----------------------------------------------------------------------
    def sendOrder1(self, orderType, price, volume, stop=False):
        """发送委托"""
        if self.trading:
            # 如果stop为True，则意味着发本地停止单
            if stop:
                vtOrderID = self.ctaEngine.sendStopOrder(self.vtSymbol1, orderType, price, volume, self)
            else:
                vtOrderID = self.ctaEngine.sendOrder(self.vtSymbol1, orderType, price, volume, self)
            return vtOrderID
        else:
            return ''

        # ----------------------------------------------------------------------

    def sendOrder1FOK(self, orderType, price, volume, stop=False):
        """发送委托"""
        if self.trading:
            # 如果stop为True，则意味着发本地停止单
            if stop:
                vtOrderID = self.ctaEngine.sendStopOrder(self.vtSymbol1, orderType, price, volume, self)
            else:
                vtOrderID = self.ctaEngine.sendOrderFOK(self.vtSymbol1, orderType, price, volume, self)
            return vtOrderID
        else:
            return ''

        # ----------------------------------------------------------------------

    def sendOrder1FAK(self, orderType, price, volume, stop=False):
        """发送委托"""
        if self.trading:
            # 如果stop为True，则意味着发本地停止单
            if stop:
                vtOrderID = self.ctaEngine.sendStopOrder(self.vtSymbol1, orderType, price, volume, self)
            else:
                vtOrderID = self.ctaEngine.sendOrderFAK(self.vtSymbol1, orderType, price, volume, self)
            return vtOrderID
        else:
            return ''


        # ----------------------------------------------------------------------

    def cancelOrder(self, vtOrderID):
        """撤单"""
        return self.ctaEngine.cancelOrder(vtOrderID)

    # if STOPORDERPREFIX in vtOrderID:
    #    return self.ctaEngine.cancelStopOrder(vtOrderID)
    # else:
    #    return self.ctaEngine.cancelOrder(vtOrderID)

    # ----------------------------------------------------------------------
    def insertTick(self, tick):
        """向数据库中插入tick数据"""
        self.ctaEngine.insertData(self.tickDbName, self.vtSymbol, tick)

    # ----------------------------------------------------------------------
    def insertBar(self, bar):
        """向数据库中插入bar数据"""
        self.ctaEngine.insertData(self.barDbName, self.vtSymbol, bar)

    # ----------------------------------------------------------------------
    def loadTick(self, days):
        """读取tick数据"""
        return self.ctaEngine.loadTick(self.tickDbName, self.vtSymbol, days)

    # ----------------------------------------------------------------------
    def loadBar(self, days):
        """读取bar数据"""
        return self.ctaEngine.loadBar(self.barDbName, self.vtSymbol, days)

    # ----------------------------------------------------------------------
    def writeCtaLog(self, content):
        """记录CTA日志"""
        content = self.name + ':' + content
        self.ctaEngine.writeCtaLog(content)

    # ----------------------------------------------------------------------
    def putEvent(self):
        """发出策略状态变化事件"""
        self.ctaEngine.putStrategyEvent(self.name)
