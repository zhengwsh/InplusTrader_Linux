# encoding: UTF-8
import numpy as np
import pandas as pd
import pymongo
import xgboost as xgb
import matplotlib.pyplot as plt
from statsmodels.tsa.stattools import coint

conn = pymongo.MongoClient()
db = conn.InplusTrader_Futures_Min_Db
coll = db.CU88
coll2 = db.ZN88
beginDate = "2017-06-01 21:01:00"
date = []
date2 = []
cu88 = []
zn88 = []
df = pd.DataFrame()
df2 = pd.DataFrame()
N = 60 # 窗口
Skewness = 0 # 偏度
Kurtosis = 2.0 # 峰度

data = coll.find({'datetime': {'$gte': beginDate}})
for item in data:
    date.append(item['datetime'])
    cu88.append(item['close'])
df['datetime'] = date
df['close'] = cu88

data2 = coll2.find({'datetime': {'$gte': beginDate}})
for item in data2:
    date2.append(item['datetime'])
    zn88.append(item['close'])
df2['datetime'] = date2
df2['close'] = zn88

# df.plot(x='datetime', y='close', kind='line')
# df2.plot(x='datetime', y='close', kind='line')
z=pd.concat([df['close'],df2['close']],axis=1)
z.columns=['cu88','zn88']
# z.plot()
# plt.show()

# 协整性检验
x = np.array(df['close'])
y = np.array(df2['close'])
a,pvalue,b = coint(x,y)
print "p-value: " + str(pvalue)

# 价差
mean = (df['close']-df2['close']).rolling(window=N, center=False).mean()
std = (df['close']-df2['close']).rolling(window=N, center=False).std()
# mean=(df['close']-df2['close']).mean()
# std=(df['close']-df2['close']).std()
# print "mean: " + str(mean)
# print "std: " + str(std)
# print "upper: " + str(mean+std)
# print "lower: " + str(mean-std)
s1=pd.Series(mean)
s2=pd.Series(mean+std/(Kurtosis/3)-Skewness)
s3=pd.Series(mean-std/(Kurtosis/3)-Skewness)
# s1=pd.Series(mean,index=range(len(df['close'])))
# s2=pd.Series(mean+std,index=range(len(df['close'])))
# s3=pd.Series(mean-std,index=range(len(df['close'])))
data3=pd.concat([df['close']-df2['close'],s1,s2,s3],axis=1)
data3.columns=['spread price','mean','upper','lower']
data3.set_index(df['datetime'])
data3.plot(x=df['datetime'])
plt.show()
