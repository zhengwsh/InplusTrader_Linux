# -*- coding:utf-8 -*- 
"""
Create on 2017/01/18
@author: vinson zheng
@group: inpluslab
@contact: 1530820222@qq.com
"""

import time
import json
import lxml.html
from lxml import etree
import datetime
import pandas as pd
import numpy as np
import cons as ct
import re
import dateu as du
from pandas.compat import StringIO
from urllib2 import urlopen, Request


def loadMongoSetting():
    """载入MongoDB数据库的配置"""
    fileName = 'Db_setting.json'
    try:
        f = file(fileName)
        setting = json.load(f)
        host = setting['mongoHost']
        port = setting['mongoPort']
    except:
        host = 'localhost'
        port = 27017
    return host, port



#----------------------------info-----------------------------------------------------
def get_stock_basics_data(date=None):
    """
        获取沪深上市公司基本情况
    Parameters
    date:日期YYYY-MM-DD，默认为上一个交易日，目前只能提供2016-08-09之后的历史数据
    Return
    --------
    DataFrame
               code,代码
               name,名称
               industry,细分行业
               area,地区
               pe,市盈率
               outstanding,流通股本
               totals,总股本(万)
               totalAssets,总资产(万)
               liquidAssets,流动资产
               fixedAssets,固定资产
               reserved,公积金
               reservedPerShare,每股公积金
               eps,每股收益
               bvps,每股净资
               pb,市净率
               timeToMarket,上市日期
    """
    wdate = du.last_tddate() if date is None else date
    wdate = wdate.replace('-', '')
    if wdate < '20160809':
        return None
    datepre = '' if date is None else wdate[0:4] + wdate[4:6] + '/'
    request = Request(ct.ALL_STOCK_BASICS_FILE%(datepre, '' if date is None else wdate))
    text = urlopen(request, timeout=10).read()
    text = text.decode('GBK')
    text = text.replace('--', '')
    df = pd.read_csv(StringIO(text), dtype={'code':'object'})
    df = df.set_index('code')
    return df

def get_stock_timeToMarket(code):
    """
    获取上市日期
    """
    df = get_stock_basics_data()
    date = df.ix[code]['timeToMarket'] #上市日期YYYYMMDD
    date = datetime.datetime.strptime(str(date), '%Y%m%d')
    return date.strftime("%Y-%m-%d")


#----------------------------daily-----------------------------------------------------
def get_stock_daily_data(code, start=None, end=None, autype=None,
               index=False, retry_count=100000, pause=0.1, drop_factor=True):
    '''
    获取历史daily数据
    Parameters
    ------
      code:string
                  股票代码 e.g. 600048
      start:string
                  开始日期 format：YYYY-MM-DD 为空时取上市日期
      end:string
                  结束日期 format：YYYY-MM-DD 为空时取当前日期
      autype:string
                  复权类型，qfq-前复权 hfq-后复权 None-不复权，默认为None
      retry_count : int, 默认 10000
                  如遇网络等问题重复执行的次数 
      pause : int, 默认 0.1
                重复请求数据过程中暂停的秒数，防止请求间隔时间太短出现的问题
      drop_factor : bool, 默认 True
                是否移除复权因子，在分析过程中可能复权因子意义不大，但是如需要先储存到数据库之后再分析的话，有该项目会更加灵活
    return
    -------
      DataFrame
          date 交易日期 (index)
          open 开盘价
          high  最高价
          close 收盘价
          low 最低价
          volume 成交量
          amount 成交金额
    '''

    start = get_stock_timeToMarket(code) if start is None else start
    #print str(start)
    end = du.today() if end is None else end
    qs = du.get_quarts(start, end)
    qt = qs[0]
    #ct._write_head()
    data = _parse_fq_data(_get_index_url(index, code, qt), index,
                          retry_count, pause)
    if data is None:
        data = pd.DataFrame()
    if len(qs)>1:
        for d in range(1, len(qs)):
            qt = qs[d]
            #ct._write_console()
            df = _parse_fq_data(_get_index_url(index, code, qt), index,
                                retry_count, pause)
            if df is None:  # 可能df为空，退出循环
                break
            else:
                data = data.append(df, ignore_index=True)
    if len(data) == 0 or len(data[(data.date>=start)&(data.date<=end)]) == 0:
        return None
    data = data.drop_duplicates('date')
    if index:
        data = data[(data.date>=start) & (data.date<=end)]
        data = data.set_index('date')
        data = data.sort_index(ascending=False)
        return data
    if autype == 'hfq':
        if drop_factor:
            data = data.drop('factor', axis=1)
        data = data[(data.date>=start) & (data.date<=end)]
        for label in ['open', 'high', 'close', 'low']:
            data[label] = data[label].map(ct.FORMAT)
            data[label] = data[label].astype(float)
        data = data.set_index('date')
        data = data.sort_index(ascending = False)
        return data
    else:
        if autype == 'qfq':
            if drop_factor:
                data = data.drop('factor', axis=1)
            df = _parase_fq_factor(code, start, end)
            df = df.drop_duplicates('date')
            df = df.sort('date', ascending=False)
            firstDate = data.head(1)['date']
            frow = df[df.date == firstDate[0]]
            rt = get_realtime_quotes(code)
            if rt is None:
                return None
            if ((float(rt['high']) == 0) & (float(rt['low']) == 0)):
                preClose = float(rt['pre_close'])
            else:
                if du.is_holiday(du.today()):
                    preClose = float(rt['price'])
                else:
                    if (du.get_hour() > 9) & (du.get_hour() < 18):
                        preClose = float(rt['pre_close'])
                    else:
                        preClose = float(rt['price'])
            
            rate = float(frow['factor']) / preClose
            data = data[(data.date >= start) & (data.date <= end)]
            for label in ['open', 'high', 'low', 'close']:
                data[label] = data[label] / rate
                data[label] = data[label].map(ct.FORMAT)
                data[label] = data[label].astype(float)
            data = data.set_index('date')
            data = data.sort_index(ascending = False)
            return data
        else:
            for label in ['open', 'high', 'close', 'low']:
                data[label] = data[label] / data['factor']
            if drop_factor:
                data = data.drop('factor', axis=1)
            data = data[(data.date>=start) & (data.date<=end)]
            for label in ['open', 'high', 'close', 'low']:
                data[label] = data[label].map(ct.FORMAT)
            data = data.set_index('date')
            data = data.sort_index(ascending = False)
            data = data.astype(float)
            return data

def _parase_fq_factor(code, start, end):
    symbol = _code_to_symbol(code)
    request = Request(ct.HIST_FQ_FACTOR_URL%(ct.P_TYPE['http'],
                                             ct.DOMAINS['vsf'], symbol))
    text = urlopen(request, timeout=10).read()
    text = text[1:len(text)-1]
    text = text.replace('{_', '{"')
    text = text.replace('total', '"total"')
    text = text.replace('data', '"data"')
    text = text.replace(':"', '":"')
    text = text.replace('",_', '","')
    text = text.replace('_', '-')
    text = json.loads(text)
    df = pd.DataFrame({'date':list(text['data'].keys()), 'factor':list(text['data'].values())})
    df['date'] = df['date'].map(_fun_except) # for null case
    if df['date'].dtypes == np.object:
        df['date'] = df['date'].astype(np.datetime64)
    df = df.drop_duplicates('date')
    df['factor'] = df['factor'].astype(float)
    return df

def _parse_fq_data(url, index, retry_count, pause):
    for _ in range(retry_count):
        time.sleep(pause)
        try:
            request = Request(url)
            text = urlopen(request, timeout=10).read()
            text = text.decode('GBK')
            html = lxml.html.parse(StringIO(text))
            res = html.xpath('//table[@id=\"FundHoldSharesTable\"]')
            
            sarr = [etree.tostring(node) for node in res]
            sarr = ''.join(sarr)
            if sarr == '':
                return None
            df = pd.read_html(sarr, skiprows = [0, 1])[0]
            if len(df) == 0:
                return pd.DataFrame()
            if index:
                df.columns = ct.HIST_FQ_COLS[0:7]
            else:
                df.columns = ct.HIST_FQ_COLS
            if df['date'].dtypes == np.object:
                df['date'] = df['date'].astype(np.datetime64)
            df = df.drop_duplicates('date')
        except ValueError as e:
            # 时间较早，已经读不到数据
            return None
        except Exception as e:
            print(e)
        else:
            return df
    raise IOError(ct.NETWORK_URL_ERROR_MSG)

def _get_index_url(index, code, qt):
    if index:
        url = ct.HIST_INDEX_URL%(ct.P_TYPE['http'], ct.DOMAINS['vsf'],
                              code, qt[0], qt[1])
    else:
        url = ct.HIST_FQ_URL%(ct.P_TYPE['http'], ct.DOMAINS['vsf'],
                              code, qt[0], qt[1])
    return url


#----------------------------tick-----------------------------------------------------
def get_stock_tick_data(code=None, date=None, retry_count=100000, pause=0.1):
    """
    获取分笔数据
    Parameters
    ------
        code:string
                  股票代码 e.g. 600048
        date:string
                  日期 format：YYYY-MM-DD
        retry_count : int, 默认 10000
                  如遇网络等问题重复执行的次数
        pause : int, 默认 0.1
                  重复请求数据过程中暂停的秒数，防止请求间隔时间太短出现的问题
     return
     -------
        DataFrame 当日所有股票交易数据(DataFrame)
              属性:成交时间、成交价格、价格变动，成交手、成交金额(元)，买卖类型
    """
    if code is None or len(code) != 6 or date is None:
        return None
    symbol = _code_to_symbol(code)
    for _ in range(retry_count):
        time.sleep(pause)
        try:
            # http://market.finance.sina.com.cn/downxls.php?date=2016-10-28&symbol=600048
            #print str(ct.TICK_PRICE_URL % (ct.P_TYPE['http'], ct.DOMAINS['sf'], ct.PAGES['dl'],
            #                    date, symbol))
            re = Request(ct.TICK_PRICE_URL % (ct.P_TYPE['http'], ct.DOMAINS['sf'], ct.PAGES['dl'],
                                date, symbol))
            
            lines = urlopen(re, timeout=10).read()
            lines = lines.decode('GBK')
            if len(lines) < 20:
                return None
            df = pd.read_table(StringIO(lines), names=ct.TICK_COLUMNS, skiprows=[0])      
        except Exception as e:
            print(e)
        else:
            return df
    raise IOError(ct.NETWORK_URL_ERROR_MSG)


#----------------------------min-----------------------------------------------------
def get_stock_min_data(code=None, date=None, ktype=1, retry_count=100000, pause=0.1):
    """
    获取分钟数据
    Parameters
    ------
        code:string
                  股票代码 e.g. 600048
        date:string
                  日期 format：YYYY-MM-DD
        retry_count : int, 默认 10000
                  如遇网络等问题重复执行的次数
        pause : int, 默认 0.1
                  重复请求数据过程中暂停的秒数，防止请求间隔时间太短出现的问题
     return
     -------
        DataFrame 当日所有股票交易数据(DataFrame)
              属性:成交日期、成交时间、open、high、low、close、成交手、成交金额(元)
    """
    if code is None or len(code) != 6 or date is None:
        return None
    # 获取股票的tick数据。
    # 数据属性分别为：时间、价格、价格变动，成交量、成交额和成交类型。
    df = get_stock_tick_data(code, date)
    if df.shape[0] == 3: # 当天没有数据
        return None

    # 数据清洗和准备
    # 将时间列加上日期，然后转换成datetime类型，并将其设置为index。
    df['time'] = date + ' ' + df['time']
    df['time'] = pd.to_datetime(df['time'])
    df = df.set_index('time')

    # 从一行行TICK的价格数据转化成开盘、最高、最低和收盘4个数据项。
    # 需要用到pandas的resample方法，并通过ohlc函数实现自动合成。
    min_type = str(ktype) + 'min'
    price_df = df['price'].resample(min_type).ohlc()
    price_df = price_df.dropna()

    # 成交量和成交额计算
    # 成交量和成交额是本分钟内的所有量的总和，所以会用到resample的sum函数。
    vols = df['volume'].resample(min_type).sum()
    vols = vols.dropna()
    vol_df = pd.DataFrame(vols, columns=['volume'])

    amounts = df['amount'].resample(min_type).sum()
    amounts = amounts.dropna()
    amount_df = pd.DataFrame(amounts, columns=['amount'])

    # 数据合并
    # 将价格数据与成交量成交额合并成一个完整的DataFrame。
    newdf = price_df.merge(vol_df, left_index=True, right_index=True).merge(amount_df, left_index=True, right_index=True)
    return newdf

    '''
    # 1分钟转N分钟
    d_dict = {
        'open':'first',
        'high':'max',
        'close':'last',
        'low':'min',
        'volume':'sum',
        'amount':'sum'
    }

    new = pd.DataFrame()
    for col in newdf.columns:
        new[col] = newdf[col].resample('5min', how=d_dict[col])
    '''




# ----------------------------help functions-----------------------------------------
def _random(n=13):
    from random import randint
    start = 10**(n-1)
    end = (10**n)-1
    return str(randint(start, end))


def _code_to_symbol(code):
    """
        生成symbol代码标志
    """
    if code in ct.INDEX_LABELS:
        return ct.INDEX_LIST[code]
    else:
        if len(code) != 6 :
            return ''
        else:
            return 'sh%s'%code if code[:1] in ['5', '6', '9'] else 'sz%s'%code


def get_trade_cal():
    '''
        交易日历
        isOpen=1是交易日，isOpen=0为休市
    '''
    df = pd.read_csv(ct.ALL_CAL_FILE)
    return df


def is_holiday(date):
    '''
        判断是否为交易日，返回True or False
    '''
    df = get_trade_cal()
    holiday = df[df.isOpen == 0]['calendarDate'].values
    if isinstance(date, str):
        today = datetime.datetime.strptime(date, '%Y-%m-%d')

    if today.isoweekday() in [6, 7] or date in holiday:
        return True
    else:
        return False

def downloadData(self, path, params):
        """下载数据"""
        if not self.settingLoaded:
            print u'%s配置未载入' % self.name
            return None
        else:
            url = '/'.join([self.domain, self.version, path])
            r = requests.get(url=url, headers=self.header, params=params)
            
            if r.status_code != HTTP_OK:
                print u'%shttp请求失败，状态代码%s' %(self.name, r.status_code)
                return None
            else:
                result = r.json()
                if 'retMsg' in result and result['retMsg'] == 'Success':
                    return result['data']
                else:
                    if 'retMsg' in result:
                        print u'%s查询失败，返回信息%s' %(self.name, result['retMsg'])
                    elif 'message' in result:
                        print u'%s查询失败，返回信息%s' %(self.name, result['message'])
                    return None