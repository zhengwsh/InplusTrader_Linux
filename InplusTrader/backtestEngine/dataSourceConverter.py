import bcolz
import pickle
import pandas as pd
import numpy as np
import pymongo
import json
from rqalpha.data.risk_free_helper import YIELD_CURVE_TENORS
from rqalpha.data.converter import FutureDayBarConverter, StockBarConverter, IndexBarConverter, FundDayBarConverter
from rqalpha import update_bundle


"""DataBase Info"""
data_root_path = 'C:\\Users\\12\\.rqalpha\\bundle\\'
conn = pymongo.MongoClient("172.18.181.119", 27017)

futures_days_db = conn.InplusTrader_Futures_Day_Db
stocks_days_db = conn.InplusTrader_Stocks_Day_Db
indexes_days_db = conn.InplusTrader_Indexes_Day_Db
funds_days_db = conn.InplusTrader_Funds_Day_Db
instruments_db = conn.InplusTrader_Instruments_Db
adjusted_dividends_db = conn.InplusTrader_Adjusted_Dividents_Db
original_dividends_db = conn.InplusTrader_Original_Dividents_Db
trading_dates_db = conn.InplusTrader_Trading_Dates_Db
yield_curve_db = conn.InplusTrader_Yield_Curve_Db
st_stock_days_db = conn.InplusTrader_St_Stocks_Day_Db
suspend_days_db = conn.InplusTrader_Suspend_Day_Db


def bar_toMongo(bar_file_name, converter_name, db_name):
    _converter = converter_name
    _table = bcolz.open(data_root_path + bar_file_name, 'r')
    _index = _table.attrs['line_map']
    _fields = _table.names
    _order_book_id = _index.keys()
    
    for code in _order_book_id:
        s, e = _index[code]
        result = pd.DataFrame()
        for f in _fields:
            result[f] = _converter.convert(f, _table.cols[f][s:e])
        db_name[code].insert(json.loads(result.to_json(orient='records')))


def instrument_toMongo():
    with open(data_root_path + 'instruments.pk', 'rb') as store:
        d = pickle.load(store)
    instruments_db["instruments"].insert(d)


def divident_toMongo(divident_name, db_name):
    _table = bcolz.open(data_root_path + divident_name, 'r')
    _index = _table.attrs['line_map']
    _order_book_id = _index.keys()

    for code in _order_book_id:
        s, e = _index[code]
        dividends = _table[s:e]

        for d in dividends:
            result = {
                'book_closure_date': str(d['closure_date']),
                'ex_dividend_date': str(d['ex_date']),
                'payable_date': str(d['payable_date']),
                'dividend_cash_before_tax': d['cash_before_tax'] / 10000.0,
                'round_lot': int(d['round_lot']),
                'announcement_date': str(d['announcement_date'])
            }
            db_name[code].insert(result)
            

def trading_dates_toMongo():
    for d in bcolz.open(data_root_path + 'trading_dates.bcolz', 'r'):
        trading_dates_db["tradingDates"].insert({"trading date" : str(d)})


def yield_curve_toMongo():
    _table = bcolz.open(data_root_path + 'yield_curve.bcolz', 'r')
    _dates = _table.cols['date'][:]
    for d in _dates:
        yield_curve_db["dates"].insert({"date" : str(d)})
    
    for d in YIELD_CURVE_TENORS.values():
        d = d[-1] + d[:-1]
        for dd in range(len(_table.cols[d][:])):
            yield_curve_db[d].insert({"date" : str(_dates[dd]), "data" : _table.cols[d][dd]})


def st_suspend_toMongo(dateset_name, db_name):
    _dates = bcolz.open(data_root_path + dateset_name, 'r')
    _index = _dates.attrs['line_map']
    _order_book_id = _index.keys()
    
    for code in _order_book_id:
        s, e = _index[code]
        for d in _dates[s:e]:
            db_name[code].insert({"date" : str(d)})
        
        
        
        

if __name__ =="__main__":
    """update bundle data"""
    #update_bundle()

    """bar to mongo"""
    bar_file_name = ["stocks.bcolz", "indexes.bcolz", "futures.bcolz", "funds.bcolz"]
    converter_name = [StockBarConverter, IndexBarConverter, FutureDayBarConverter, FundDayBarConverter]
    db_name = [stocks_days_db, indexes_days_db, futures_days_db, funds_days_db]
    
    for i in range(len(bar_file_name)):
        bar_toMongo(bar_file_name[i], converter_name[i], db_name[i])


    """instrument to mongo"""
    instrument_toMongo()


    """divident to mongo"""
    divident_name = ['adjusted_dividends.bcolz', 'original_dividends.bcolz']
    db_name = [adjusted_dividends_db, original_dividends_db]
    for i in range(len(divident_name)):
        divident_toMongo(divident_name[i], db_name[i])

    
    """trading dates to mongo"""
    trading_dates_toMongo()
    
    
    """yield dates to mongo"""
    yield_curve_toMongo()
    
    
    """st / suspend to mongo"""    
    dateset_name = ['st_stock_days.bcolz', 'suspended_days.bcolz']
    db_name = [st_stock_days_db, suspend_days_db]
    for i in range(len(dateset_name)):
        st_suspend_toMongo(dateset_name[i], db_name[i])
    
    
    #df = pd.read_csv()
    #ct = bcolz.c_table.fromdataframe(df, rootdir='dataframe.bcolz')
    #df = _table.todataframe()
    