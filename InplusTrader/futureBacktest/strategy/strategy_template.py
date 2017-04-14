from rqalpha.api import *
import pandas as pd
import numpy as np
import talib


# 在这个方法中编写任何的初始化逻辑。context对象将会在你的算法策略的任何方法之间做传递。
def init(context):
    # 在context中保存全局变量
    context.s1 = "000001.XSHE"
    # 实时打印日志
    logger.info("RunInfo: {}".format(context.run_info))

# before_trading此函数会在每天策略交易开始前被调用，当天只会被调用一次
def before_trading(context):
    logger.info("开盘前执行before_trading函数")

# 你选择的证券的数据更新将会触发此段逻辑，例如日或分钟历史数据切片或者是实时数据切片更新
def handle_bar(context, bar_dict):
    logger.info("每一个Bar执行")
    logger.info("打印Bar数据：")
    logger.info(bar_dict[context.s1])

# after_trading函数会在每天交易结束后被调用，当天只会被调用一次
def after_trading(context):
    logger.info("收盘后执行after_trading函数")