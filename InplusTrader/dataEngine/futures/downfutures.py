from storage2 import *
import pandas as pd
import os


dc = DBConfig()
api = PyApi(Config())
mc = MongodController(dc, api)

mc._collNames['futTicker'] = mc._allFutTickers()
print '[MONGOD]: Future tickers collected.'

mc._ensure_index()
print '[MONGOD]: Future index ensured.'

# construct
#mc.download_future_D1('20150101','20170220')
#print '[MONGOD]: Future D1 downloaded.'


#update
#mc.update_future_D1()
