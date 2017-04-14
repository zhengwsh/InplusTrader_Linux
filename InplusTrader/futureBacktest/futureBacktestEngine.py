# encoding: UTF-8

from rqalpha.backtestEngine import BacktestEngine
from vtGateway import VtSubscribeReq, VtOrderReq, VtCancelOrderReq, VtLogData
from eventEngine import *
from vtConstant import *
from strategy import STRATEGY_PATH

class FutureBacktestEngine(BacktestEngine):
    """期货回测引擎"""

    # ----------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine):
        """Constructor"""
        super(FutureBacktestEngine, self).__init__()

        self.mainEngine = mainEngine
        self.eventEngine = eventEngine

        # 保存策略实例的字典
        # key为策略名称，value为策略位置，注意策略名称不允许重复
        self.strategyDict = {}

    # ----------------------------------------------------------------------
    def loadStrategy(self):
        """读取策略位置"""
        self.strategyDict = STRATEGY_PATH

    # ----------------------------------------------------------------------
    def writeBktLog(self, content):
        """快速发出回测模块日志事件"""
        log = VtLogData()
        log.logContent = content
        event = Event(type_=EVENT_BKT_LOG)
        event.dict_['data'] = log
        self.eventEngine.put(event)