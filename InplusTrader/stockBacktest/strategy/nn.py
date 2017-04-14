# 可以自己import我们平台支持的第三方python模块，比如pandas、numpy等。
from rqalpha.api import *
import pandas as pd
import numpy as np
from datetime import timedelta
from pybrain.datasets import SequentialDataSet
from pybrain.tools.shortcuts import buildNetwork
from pybrain.structure.networks import Network
from pybrain.structure.modules import LSTMLayer
from pybrain.supervised import RPropMinusTrainer


# 训练trainX和trainY，并返回神经网络net
def train(context, trainX, trainY):
    ds = SequentialDataSet(4, 1)
    for dataX, dataY in zip(trainX, trainY):
        ds.addSample(dataX, dataY)
    net = buildNetwork(4, 1, 1, hiddenclass=LSTMLayer, outputbias=False, recurrent=True)
    trainer = RPropMinusTrainer(net, dataset=ds)
    EPOCHS_PER_CYCLE = 5
    CYCLES = 5
    for i in range(CYCLES):
        trainer.trainEpochs(EPOCHS_PER_CYCLE)
    return net, trainer.testOnData()


# 更新数据集data
def load(context, ticker):
    close = history(90, '1d', 'close')[ticker]
    high = history(90, '1d', 'high')[ticker]
    low = history(90, '1d', 'low')[ticker]
    volume = history(90, '1d', 'volume')[ticker]
    data = pd.DataFrame({'close': close.values,
                         'high': high.values,
                         'low': low.values,
                         'volume': volume.values}, index=close.index)
    context.position_ratio.append([data['close'].mean(),
                                   data['high'].mean(),
                                   data['low'].mean(),
                                   data['volume'].mean()])
    context.shape_ratio.append([data['close'].std(),
                                data['high'].std(),
                                data['low'].std(),
                                data['volume'].std()])
    data['close'] = (data['close'] - context.position_ratio[-1][0]) / context.shape_ratio[-1][0]
    data['high'] = (data['high'] - context.position_ratio[-1][1]) / context.shape_ratio[-1][1]
    data['low'] = (data['low'] - context.position_ratio[-1][2]) / context.shape_ratio[-1][2]
    data['volume'] = (data['volume'] - context.position_ratio[-1][3]) / context.shape_ratio[-1][3]

    return data


# 剔除情况特殊的黑名单股，只看策略效果，排除个体问题
def filter_blacklist(context, stock_list):
    return [ticker for ticker in stock_list if ticker not in context.blacklist]


def filter_stlist(stock_list):
    return [ticker for ticker in stock_list if not is_st_stock(ticker)]


# 建模，每3个月运行一次，用过去6个月训练
def modelize(context, bar_dict):
    if context.every_3_months % 3 != 0:
        context.every_3_months += 1
        return 0
    print('-' * 65)
    print('------' + '{:-^59}'.format('modelizing'))
    context.position_ratio = []
    context.shape_ratio = []
    context.data = []
    context.net = []
    context.list = []
    templist = list(get_fundamentals(query(fundamentals.eod_derivative_indicator.market_cap)
                                     .order_by(fundamentals.eod_derivative_indicator.market_cap.asc())
                                     .limit(context.num * 5)).columns)
    context.list = filter_blacklist(context, filter_stlist(templist))[:context.num]
    names = []
    scores = []
    for ticker in context.list:
        names.append('{:<11}'.format(ticker))
        data = load(context, ticker)
        trainX = data.ix[:-1, :].values
        trainY = data.ix[1:, 0].values
        net, mse = train(context, trainX, trainY)
        context.data.append(data)
        context.net.append(net)
        scores.append('{:<11}'.format(str(mse)[:6]))
        if np.isnan(mse):
            context.blacklist.append(ticker)
            context.mflag = 0
            return 0
    context.pct = [0] * context.num
    print('------' + '{:-^59}'.format('finished'))
    print('-' * 65)
    print(' nm | ' + ' '.join(names))
    print('mse | ' + ' '.join(scores))

    context.mflag = 1  # 标记已经建模
    context.tflag = 0
    context.every_3_months += 1


def mkt_panic():
    # 连续两天大盘跌破3个点，或者大盘跌破5个点
    mkt = history(3, '1d', 'close')['000001.XSHG']
    panic = (mkt[-1] / mkt[-2] < 0.97 and mkt[-2] / mkt[-3] < 0.97) or mkt[-1] / mkt[-2] < 0.95
    if panic:
        print('!!!!!!' + '{:!^59}'.format('panic'))
        return 1
    return 0


# 最后利用每3个月更新的模型，每天进行交易，预测涨幅超过a就买入，预测跌幅超过b则卖出
def trade(context, bar_dict):
    while context.mflag == 0: modelize(context, bar_dict)

    trash_bin = [ticker for ticker in context.portfolio.positions if ticker not in context.list]
    for ticker in trash_bin: order_target_percent(ticker, 0)

    actual_close = []
    actual_high = []
    actual_low = []
    actual_vol = []
    actual_open = []
    actual_data = []
    predict_close = []

    for i in range(context.num):
        actual_close.append(
            (history(1, '1d', 'close')[context.list[i]][0] - context.position_ratio[i][0]) / context.shape_ratio[i][0])
        actual_high.append(
            (history(1, '1d', 'high')[context.list[i]][0] - context.position_ratio[i][1]) / context.shape_ratio[i][1])
        actual_low.append(
            (history(1, '1d', 'low')[context.list[i]][0] - context.position_ratio[i][2]) / context.shape_ratio[i][2])
        actual_vol.append(
            (history(1, '1d', 'volume')[context.list[i]][0] - context.position_ratio[i][3]) / context.shape_ratio[i][3])
        actual_open.append(
            (history(1, '1m', 'close')[context.list[i]][0] - context.position_ratio[i][0]) / context.shape_ratio[i][0])
        actual_data.append([actual_close[i], actual_high[i], actual_low[i], actual_vol[i]])
        predict_close.append(context.net[i].activate(actual_data[i])[0])

    if context.tflag == 0:
        context.temp_pc = predict_close

    r = [float((pc * shape_ratio[0] + position_ratio[0]) / (ao * shape_ratio[0] + position_ratio[0]) - 1) for
         pc, ao, shape_ratio, position_ratio in
         zip(predict_close, actual_open, context.shape_ratio, context.position_ratio)]

    temp_r = [float((pc * shape_ratio[0] + position_ratio[0]) / (tpc * shape_ratio[0] + position_ratio[0]) - 1) for
              pc, tpc, shape_ratio, position_ratio in
              zip(predict_close, context.temp_pc, context.shape_ratio, context.position_ratio)]

    # The essence of this strategy
    hybrid_r = [max(ri, temp_ri, ri + temp_ri) for ri, temp_ri in zip(r, temp_r)]
    bad_hybrid_signal = sum([x <= 0 for x in hybrid_r])
    a, b = 0.00, -0.01
    panic = mkt_panic()
    for i in range(context.num):
        if panic or 0 < context.post_panic < 22 * context.num:
            context.pct[i] = 0
            context.post_panic = (1 - panic) * (context.post_panic + 1) + panic
        elif hybrid_r[i] > a:
            context.pct[i] = min(context.pct[i] + .5 / context.num, 2 / context.num)
            context.post_panic = 0
        elif hybrid_r[i] < b or bad_hybrid_signal > 3 * context.num // 5:
            context.pct[i] = max(context.pct[i] - .5 / context.num, 0)
            context.post_panic = 0

    if context.tflag == 1: print(' ac | ' + ' '.join(['{:<11}'.format(str(ac)[:6]) for ac in actual_close]))
    print('-' * 65)
    print(' ao | ' + ' '.join(['{:<11}'.format(str(ao)[:6]) for ao in actual_open]))
    print(' pc | ' + ' '.join(['{:<11}'.format(str(pc)[:6]) for pc in predict_close]))
    print('  r | ' + ' '.join(['{:<11}'.format(str(ri)[:6]) for ri in hybrid_r]))
    pct = sum([context.portfolio.positions[ticker].market_value for ticker in context.portfolio.positions]) / (
    context.portfolio.market_value + context.portfolio.cash)
    tot_pct = max(sum(context.pct), 1)
    context.pct = list(map(lambda x: x / tot_pct, context.pct))
    print('  % | ' + ' '.join(['{:<11}'.format(str(p)[:6]) for p in context.pct]))
    plot('total position', pct * 100)
    for i in range(context.num): order_target_percent(context.list[i], context.pct[i])
    context.tflag = 1
    context.temp_pc = predict_close


# 在这个方法中编写任何的初始化逻辑。context对象将会在你的算法策略的任何方法之间做传递。
def init(context):
    context.temp_pc = []
    context.every_3_months = 0
    context.tflag = 0
    context.mflag = 0
    context.position_ratio = []
    context.shape_ratio = []
    context.num = 20
    context.list = []
    context.pct = [0] * context.num
    context.net = []
    context.data = []
    context.post_panic = 0
    context.blacklist = [
        '000004.XSHE', '000546.XSHE',
        '000594.XSHE', '002352.XSHE',
        '300176.XSHE', '300260.XSHE',
        '300372.XSHE', '600137.XSHG',
        '600306.XSHG', '600656.XSHG',
    ]
    scheduler.run_monthly(modelize, 1)
    scheduler.run_daily(trade, time_rule=market_open(minute=1))


# before_trading此函数会在每天交易开始前被调用，当天只会被调用一次
def before_trading(context):
    pass


# 你选择的证券的数据更新将会触发此段逻辑，例如日或分钟历史数据切片或者是实时数据切片更新
def handle_bar(context, bar_dict):
    pass