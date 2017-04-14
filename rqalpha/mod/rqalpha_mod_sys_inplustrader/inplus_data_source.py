# -*- coding: utf-8 -*-

import six
import os, sys
import pandas as pd
import numpy as np
import datetime
import pymongo
try:
    # For Python 2 兼容
    from functools import lru_cache
except Exception as e:
    from fastcache import lru_cache

from rqalpha.environment import Environment
#from rqalpha.interface import AbstractDataSource
from rqalpha.data.base_data_source import BaseDataSource
from rqalpha.data.future_info_cn import CN_FUTURE_INFO
from rqalpha.utils.datetime_func import convert_date_to_int, convert_int_to_date
from rqalpha.model.instrument import Instrument
from rqalpha.data import risk_free_helper
from rqalpha.data.risk_free_helper import YIELD_CURVE_TENORS
from data_types import getType


class DataSource(BaseDataSource):
    def __init__(self, path):
        """
        数据源接口。 通过 :class:`DataProxy` 进一步进行了封装，向上层提供更易用的接口。
        在扩展模块中，可以通过调用 ``env.set_data_source`` 来替换默认的数据源。可参考 :class:`BaseDataSource`。
        """
        self._env = Environment.get_instance()
        self.conn = pymongo.MongoClient(path, 27017)

        # Day DB
        self.stocks_days_db = self.conn.InplusTrader_Stocks_Day_Db
        self.indexes_days_db = self.conn.InplusTrader_Indexes_Day_Db
        self.futures_days_db = self.conn.InplusTrader_Futures_Day_Db
        self.funds_days_db = self.conn.InplusTrader_Funds_Day_Db
        # Minute DB
        self.stocks_mins_db = self.conn.InplusTrader_Stocks_Min_Db
        self.futures_mins_db = self.conn.InplusTrader_Futures_Min_Db
        # Tick DB
        self.stocks_tick_db = self.conn.InplusTrader_Stocks_Tick_Db
        self.futures_tick_db = self.conn.InplusTrader_Futures_Tick_Db

        self.instruments_db = self.conn.InplusTrader_Instruments_Db
        self.adjusted_dividends_db = self.conn.InplusTrader_Adjusted_Dividents_Db
        self.original_dividends_db = self.conn.InplusTrader_Original_Dividents_Db
        self.trading_dates_db = self.conn.InplusTrader_Trading_Dates_Db
        self.yield_curve_db = self.conn.InplusTrader_Yield_Curve_Db
        self.st_stock_days_db = self.conn.InplusTrader_St_Stocks_Day_Db
        self.suspend_days_db = self.conn.InplusTrader_Suspend_Day_Db

        self._day_bars = [self.stocks_days_db, self.indexes_days_db, self.futures_days_db, self.funds_days_db]
        self._min_bars = [self.stocks_mins_db, self.futures_mins_db]
        self._tick_bars = [self.stocks_tick_db, self.futures_tick_db]
        self._instruments = self.instruments_db
        self._adjusted_dividends = self.adjusted_dividends_db
        self._original_dividends = self.original_dividends_db
        self._trading_dates = self.trading_dates_db
        self._yield_curve = self.yield_curve_db
        self._st_stock_days = self.st_stock_days_db
        self._suspend_days = self.suspend_days_db

    def get_dividend(self, order_book_id, adjusted=True):
        """
        获取股票/基金分红信息

        :param str order_book_id: 合约名
        :param bool adjusted: 是否经过前复权处理
        :return:
        """
        def fetchData(adjusted):
            if adjusted:
                mongo_data = self._adjusted_dividends[order_book_id].find({}, {"_id":0})
            else:
                mongo_data = self._original_dividends[order_book_id].find({}, {"_id":0})
            return mongo_data

        result = pd.DataFrame({
            'book_closure_date': pd.Index(pd.Timestamp(d['book_closure_date']) for d in fetchData(adjusted)),
            'ex_dividend_date': pd.Index(pd.Timestamp(d['ex_dividend_date']) for d in fetchData(adjusted)),
            'payable_date': pd.Index(pd.Timestamp(d['payable_date']) for d in fetchData(adjusted)),
            'dividend_cash_before_tax': [d['dividend_cash_before_tax'] for d in fetchData(adjusted)],
            'round_lot': [d['round_lot'] for d in fetchData(adjusted)]
        }, index = pd.Index(pd.Timestamp(d['announcement_date']) for d in fetchData(adjusted)))

        return result

    def get_trading_minutes_for(self, order_book_id, trading_dt):
        """

        获取证券某天的交易时段，用于期货回测

        :param instrument: 合约对象
        :type instrument: :class:`~Instrument`

        :param datetime.datetime trading_dt: 交易日。注意期货夜盘所属交易日规则。

        :return: list[`datetime.datetime`]
        """
        raise NotImplementedError

    def get_trading_calendar(self):
        """
        获取交易日历

        :return: list[`pandas.Timestamp`]
        """
        mongo_data = self._trading_dates["tradingDates"].find({}, {"_id":0})
        result = pd.Index(pd.Timestamp(str(d["trading date"])) for d in mongo_data)
        return result

    def get_all_instruments(self):
        """
        获取所有Instrument。

        :return: list[:class:`~Instrument`]
        """
        mongo_data = self._instruments["instruments"].find({}, {"_id":0})
        return [Instrument(i) for i in mongo_data]

    def is_suspended(self, order_book_id, dt):
        if isinstance(dt, (int, np.int64, np.uint64)):
            if dt > 100000000:
                dt //= 1000000
        else:
            dt = dt.year*10000 + dt.month*100 + dt.day

        result =set(np.uint32(d["date"]) for d in self._suspend_days[order_book_id].find({}, {"_id":0}))
        return dt in result

    def is_st_stock(self, order_book_id, dt):
        if isinstance(dt, (int, np.int64, np.uint64)):
            if dt > 100000000:
                dt //= 1000000
        else:
            dt = dt.year*10000 + dt.month*100 + dt.day

        result = set(np.uint32(d["date"]) for d in self._st_stock_days[order_book_id].find({}, {"_id":0}))
        return dt in result

    INSTRUMENT_TYPE_MAP = {
        'CS': 0, # 股票
        'INDX': 1, #指数
        'Future': 2, #期货
        'ETF': 3, #ETF
        'LOF': 3, #LOF
        'FenjiA': 3, #分级A基金
        'FenjiB': 3, #分级B基金
        'FenjiMu': 3, #分级母基金
    }

    def _index_of(self, instrument):
        return self.INSTRUMENT_TYPE_MAP[instrument.type]

    @lru_cache(None)
    def _all_day_bars_of(self, instrument):
        i = self._index_of(instrument)
        mongo_data = self._day_bars[i][instrument.order_book_id].find({}, {"_id": 0})
        fields = mongo_data[0].keys()
        fields.remove('date')

        result = []
        dtype = np.dtype(getType(i))
        result = np.empty(shape=(mongo_data.count(),), dtype=dtype)

        for f in fields:
            bar_attr = []
            mongo_data = self._day_bars[i][instrument.order_book_id].find({}, {"_id": 0})
            for bar in mongo_data:
                bar_attr.append(bar[f])
            result[f] = np.array(bar_attr)

        bar_attr = []
        mongo_data = self._day_bars[i][instrument.order_book_id].find({}, {"_id": 0})
        for bar in mongo_data:
            bar_attr.append(np.array(bar['date']).astype(np.uint64) * 1000000)
        result['datetime'] = np.array(bar_attr)
        return result

    @lru_cache(None)
    def _filtered_day_bars(self, instrument):
        bars = self._all_day_bars_of(instrument)
        if bars is None:
            return None
        return bars[bars['volume'] > 0]

    def get_bar(self, instrument, dt, frequency):
        """
        根据 dt 来获取对应的 Bar 数据

        :param instrument: 合约对象
        :type instrument: :class:`~Instrument`

        :param datetime.datetime dt: calendar_datetime

        :param str frequency: 周期频率，`1d` 表示日周期, `1m` 表示分钟周期

        :return: `numpy.ndarray` | `dict`
        """
        if frequency != '1d':
            raise NotImplementedError

        bars = self._all_day_bars_of(instrument)
        if bars is None:
            return
        dt = convert_date_to_int(dt)
        pos = bars['datetime'].searchsorted(dt)
        if pos >= len(bars) or bars['datetime'][pos] != dt:
            return None

        return bars[pos]

    def get_settle_price(self, instrument, date):
        """
        获取期货品种在 date 的结算价

        :param instrument: 合约对象
        :type instrument: :class:`~Instrument`

        :param datetime.date date: 结算日期

        :return: `str`
        """
        bar = self.get_bar(instrument, date, '1d')
        if bar is None:
            return np.nan
        return bar['settlement']

    @staticmethod
    def _are_fields_valid(fields, valid_fields):
        if fields is None:
            return True
        if isinstance(fields, six.string_types):
            return fields in valid_fields
        for field in fields:
            if field not in valid_fields:
                return False
        return True

    def get_yield_curve(self, start_date, end_date, tenor=None):
        """
        获取国债利率

        :param pandas.Timestamp str start_date: 开始日期
        :param pandas.Timestamp end_date: 结束日期
        :param str tenor: 利率期限

        :return: pandas.DataFrame, [start_date, end_date]
        """
        mongo_dates = self._yield_curve['dates'].find({}, {"_id":0}).sort('date', pymongo.ASCENDING)
        _dates = np.array([np.uint32(d['date']) for d in mongo_dates])

        d1 = start_date.year * 10000 + start_date.month * 100 + start_date.day
        d2 = end_date.year * 10000 + end_date.month * 100 + end_date.day
        s = _dates.searchsorted(d1)
        e = _dates.searchsorted(d2, side='right')
        if e == len(_dates):
            e -= 1
        if _dates[e] == d2:
            # 包含 end_date
            e += 1
        if e < s:
            return None

        df = pd.DataFrame()
        for d in YIELD_CURVE_TENORS.values():
            mongo_data = self._yield_curve[d].find({}, {"_id":0}).sort('date', pymongo.ASCENDING)
            df[d] = [k['data'] for k in mongo_data]

        mongo_data = self._yield_curve['dates'].find({}, {"_id":0}).sort('date', pymongo.ASCENDING)
        df.index = pd.Index(pd.Timestamp(str(d['date'])) for d in mongo_data)

        df.rename(columns=lambda n: n[1:] + n[0], inplace=True)
        if tenor is not None:
            return df[tenor]
        return df

    def get_risk_free_rate(self, start_date, end_date):
        mongo_dates = self._yield_curve['dates'].find({}, {"_id":0}).sort('date', pymongo.ASCENDING)
        _dates = np.array([np.uint32(d['date']) for d in mongo_dates])

        tenor = risk_free_helper.get_tenor_for(start_date, end_date)
        tenor = tenor[-1] + tenor[:-1]
        mongo_data = self._yield_curve[tenor].find({}, {"_id":0})
        _table = np.array([d['data'] for d in mongo_data])

        d = start_date.year * 10000 + start_date.month * 100 + start_date.day
        pos = _dates.searchsorted(d)
        if pos > 0 and (pos == len(_dates) or _dates[pos] != d):
            pos -= 1
        while pos >= 0 and np.isnan(_table[pos]):
            # data is missing ...
            pos -= 1

        return _table[pos]

    def current_snapshot(self, instrument, frequency, dt):
        """
        获得当前市场快照数据。只能在日内交易阶段调用，获取当日调用时点的市场快照数据。
        市场快照数据记录了每日从开盘到当前的数据信息，可以理解为一个动态的day bar数据。
        在目前分钟回测中，快照数据为当日所有分钟线累积而成，一般情况下，最后一个分钟线获取到的快照数据应当与当日的日线行情保持一致。
        需要注意，在实盘模拟中，该函数返回的是调用当时的市场快照情况，所以在同一个handle_bar中不同时点调用可能返回的数据不同。
        如果当日截止到调用时候对应股票没有任何成交，那么snapshot中的close, high, low, last几个价格水平都将以0表示。

        :param instrument: 合约对象
        :type instrument: :class:`~Instrument`

        :param str frequency: 周期频率，`1d` 表示日周期, `1m` 表示分钟周期
        :param datetime.datetime dt: 时间

        :return: :class:`~Snapshot`
        """
        raise NotImplementedError

    def get_split(self, order_book_id):
        """
        获取拆股信息

        :param str order_book_id: 合约名

        :return: `pandas.DataFrame`
        """
        return None

    def available_data_range(self, frequency):
        """
        此数据源能提供数据的时间范围

        :param str frequency: 周期频率，`1d` 表示日周期, `1m` 表示分钟周期

        :return: (earliest, latest)
        """
        if frequency == '1d':
            mongo_data = self._day_bars[self.INSTRUMENT_TYPE_MAP['INDX']]['000001.XSHG'].find({}, {"_id":0}).sort('date', pymongo.ASCENDING)
            mongo_data = list(mongo_data)
            s, e = np.uint32(mongo_data[0]['date']), np.uint32(mongo_data[-1]['date'])
            return convert_int_to_date(s).date(), convert_int_to_date(e).date()

        if frequency == '1m':
            raise NotImplementedError

    def history_bars(self, instrument, bar_count, frequency, fields, dt, skip_suspended=True, include_now=False):
        """
        获取历史数据

        :param instrument: 合约对象
        :type instrument: :class:`~Instrument`

        :param int bar_count: 获取的历史数据数量
        :param str frequency: 周期频率，`1d` 表示日周期, `1m` 表示分钟周期
        :param str fields: 返回数据字段

        =========================   ===================================================
        fields                      字段名
        =========================   ===================================================
        datetime                    时间戳
        open                        开盘价
        high                        最高价
        low                         最低价
        close                       收盘价
        volume                      成交量
        total_turnover              成交额
        datetime                    int类型时间戳
        open_interest               持仓量（期货专用）
        basis_spread                期现差（股指期货专用）
        settlement                  结算价（期货日线专用）
        prev_settlement             结算价（期货日线专用）
        =========================   ===================================================

        :param datetime.datetime dt: 时间

        :param bool skip_suspended: 是否跳过停牌日

        :return: `numpy.ndarray`

        """
        if frequency != '1d':
            raise NotImplementedError

        if skip_suspended and instrument.type == 'CS':
            bars = self._filtered_day_bars(instrument)
        else:
            bars = self._all_day_bars_of(instrument)

        if bars is None or not self._are_fields_valid(fields, bars.dtype.names):
            return None

        dt = convert_date_to_int(dt)
        i = bars['datetime'].searchsorted(dt, side='right')
        left = i - bar_count if i >= bar_count else 0
        if fields is None:
            return bars[left:i]
        else:
            return bars[left:i][fields]


    def get_future_info(self, instrument, hedge_type):
        """
        获取期货合约手续费、保证金等数据

        :param str order_book_id: 合约名
        :param HEDGE_TYPE hedge_type: 枚举类型，账户对冲类型
        :return: dict
        """
        return CN_FUTURE_INFO[instrument.underlying_symbol][hedge_type.value]


    def get_ticks(self, order_book_id, date):
        raise NotImplementedError
