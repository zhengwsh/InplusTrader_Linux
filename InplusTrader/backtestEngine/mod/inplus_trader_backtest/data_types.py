
StockBar_Dict = [('datetime', '<u8'), ('open', '<f8'), ('close', '<f8'), ('high', '<f8'), ('low', '<f8'), ('volume', '<u8'), ('total_turnover', '<u8'), ('limit_up', '<f8'), ('limit_down', '<f8')]
FutureDayBar_Dict = [('datetime', '<u8'), ('open', '<f8'), ('close', '<f8'), ('high', '<f8'), ('low', '<f8'), ('volume', '<u8'), ('total_turnover', '<u8'), ('settlement', '<f8'), ('prev_settlement', '<f8'), ('open_interest', '<u4'), ('basis_spread', '<f8'), ('limit_up', '<f8'), ('limit_down', '<f8')]
FundDayBar_Dict = []
IndexBar_Dict = [('datetime', '<u8'), ('open', '<f8'), ('close', '<f8'), ('high', '<f8'), ('low', '<f8'), ('volume', '<u8'), ('total_turnover', '<u8')]

order_list = [StockBar_Dict, IndexBar_Dict, FutureDayBar_Dict, FundDayBar_Dict]

def getType(i):
    return order_list[i]
