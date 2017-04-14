# encoding: UTF-8

'''
功能：定时下载，如每小时下载     onTimeDownloadHisData()
      自动下载全部历史数据       downLoadAllDataManager()

使用方法：把这个模块加载到 vtEngine 中，即可运行。每一秒会触发本模块的 processTimerChecker()

建议：策略启动前先把全部历史数据补全，
      策略运行中，以收到的 tick 合成即可。

最新思路：
在ctaEngine中载入策略时，同时触发该品种补全历史数据的事件。把vtSymbol和对应的合约存入事件中。
此引擎收到该事件后即下载并存入数据库。
等下策略初始化时就从库中读取历史数据了。
实盘中，策略自己生成K线。即，策略只在初始化时从库中读入一次。以后自己生成。

最好还是考虑在初始化之时先把数据库补全。运行过程中就直接自己聚合。
防止拉取不到历史数据导致死循环。

'''

import json
import os
import copy
from collections import OrderedDict
from datetime import datetime, timedelta
from time import sleep

from eventEngine import *
from vtGateway import VtSubscribeReq, VtLogData


from vtFunction import todayDate

from myFunction import *            # 常见函数
from hisBase import *               # K 线类，属性
from myConstant import *            # 常量

from threading import Thread        # 请求历史数据要发出线程才不会卡死。
from random import randint



########################################################################
class HisDataEngine(object):
    """历史数据引擎
        自动维护本地历史数据
        自动把本地的历史数据维护到最新状态
    """
    
    settingFileName = 'hisData_setting.json'
    settingFileName = os.getcwd() + '/historicalData/' + settingFileName

    #----------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine):
        """Constructor"""
        self.mainEngine = mainEngine                # 指向主引擎
        self.eventEngine = eventEngine              # 指向事件引擎
        
        # 当前日期
        self.today = todayDate()
        
        # 主力合约代码映射字典，key为具体的合约代码（如IF1604），value为主力合约代码（如IF0000）
        self.activeSymbolDict = {}

        # 合约代码映射字典，key为vtSymbol（如IF1604），value为字典对象，包括该vtSymbol的各种属性以及生成后的合约对象
        # {'EUR.USD':{'currency':'USD','contract':contract   }}
        #
        self.vtSymbolContractDict = {}          #  vtSymbol 和合约对照表，载入时生成  key 为 vtSymbol,value为列表，合约和历史数据接口


        # Tick对象字典
        self.tickDict = {}
        
        # K线对象字典
        self.barDict = {}

        # Timer计时器
        self.sbTimerCount = 0
        self.sbTimerTrigger = 60             # 每秒都会收到一次Timer事件，60秒检查一次
        self.minute_timer_counter = 0

        # 每一次加载模块

        self.pre_minute = 0
        self.pre_hour = 0
        self.pre_day = 0               # 当前day变化。也要同时检查一下EST 的day 是不是也变了。

        self.initForStrategyDays = 5       # 策略载入时，自动下载 5 天数据给策略初始化。
        self.fromStrategyInit  =  True     #  是否来自策略请求，是：只处理该合约，否则处理全部json的合约

        # tickerId下载对应的参数
        self.tickerIdKwargsDict = {}        # 请求历史数据时把 tickerId及参数存入此字典中。回调收到后再删除。最后再检查一下是否还有内容。如有则表示下载不成功。
        self.missingDataReDownloadTimes = 0 #


        # 载入设置，生成合约
        self.loadSetting()     # 历史数据不必订阅，因为不需要实时行情


        # 补全json中设置合约的历史数据
        thread = Thread(target=self.downLoadAllDataManager,   kwargs=({'days': 500, }))         #补全最近500天的。只要补一次就行，平时策略启动就自动补5天
        thread.start()
        
    #----------------------------------------------------------------------
    def loadSetting(self):
        """载入设置"""
        with open(self.settingFileName) as f:
            drSetting = json.load(f)
            
            # 如果working设为False则不启动行情记录功能
            working = drSetting['working']
            if not working:
                return

            if 'bar' in drSetting:
                l = drSetting['bar']
                
                for setting in l:
                    vtSymbol = setting.get('vtSymbol')
                    hisGatewayName = setting.get('hisGatewayName')

                    if vtSymbol:
                        contract = self.mainEngine.getContract(vtSymbol)
                        if not contract:
                            print  u'请先手动订阅成功一次'

                    req = VtSubscribeReq()
                    req.symbol = contract.symbol
                    req.currency = contract.currency
                    req.exchange = contract.exchange
                    req.productClass = contract.productClass


                    if vtSymbol in self.vtSymbolContractDict:
                        pass
                    else:
                        l = {}
                        self.vtSymbolContractDict[vtSymbol] = l
                        l['hisGatewayName'] = hisGatewayName
                        l['contract'] = req

            # 注册事件监听
            self.registerEvent()            

    #----------------------------------------------------------------------
    def procecssTickEvent(self, event):
        """处理行情推送"""
        tick = event.dict_['data']
        vtSymbol = tick.vtSymbol

        # 转化Tick格式
        drTick = DrTickData()
        d = drTick.__dict__
        for key in d.keys():
            if key != 'datetime':
                d[key] = tick.__getattribute__(key)
        drTick.datetime = datetime.strptime(' '.join([tick.date, tick.time]), '%Y%m%d %H:%M:%S.%f')            
        
        # 更新Tick数据
        if vtSymbol in self.tickDict:
            self.insertData(TICK_DB_NAME, vtSymbol, drTick)
            
            if vtSymbol in self.activeSymbolDict:
                activeSymbol = self.activeSymbolDict[vtSymbol]
                self.insertData(TICK_DB_NAME, activeSymbol, drTick)
            
            # 发出日志
            self.writeDrLog(u'记录Tick数据%s，时间:%s, last:%s, bid:%s, ask:%s' 
                            %(drTick.vtSymbol, drTick.time, drTick.lastPrice, drTick.bidPrice1, drTick.askPrice1))
            
        # 更新分钟线数据
        if vtSymbol in self.barDict:
            bar = self.barDict[vtSymbol]
            
            # 如果第一个TICK或者新的一分钟
            if not bar.datetime or bar.datetime.minute != drTick.datetime.minute:    
                if bar.vtSymbol:
                    newBar = copy.copy(bar)
                    self.insertData(MINUTE_DB_NAME, vtSymbol, newBar)
                    
                    if vtSymbol in self.activeSymbolDict:
                        activeSymbol = self.activeSymbolDict[vtSymbol]
                        self.insertData(MINUTE_DB_NAME, activeSymbol, newBar)                    
                    
                    self.writeDrLog(u'记录分钟线数据%s，时间:%s, O:%s, H:%s, L:%s, C:%s' 
                                    %(bar.vtSymbol, bar.time, bar.open, bar.high, 
                                      bar.low, bar.close))
                         
                bar.vtSymbol = drTick.vtSymbol
                bar.symbol = drTick.symbol
                bar.exchange = drTick.exchange
                
                bar.open = drTick.lastPrice
                bar.high = drTick.lastPrice
                bar.low = drTick.lastPrice
                bar.close = drTick.lastPrice
                
                bar.date = drTick.date
                bar.time = drTick.time
                bar.datetime = drTick.datetime
                bar.volume = drTick.volume
                bar.openInterest = drTick.openInterest        
            # 否则继续累加新的K线
            else:                               
                bar.high = max(bar.high, drTick.lastPrice)
                bar.low = min(bar.low, drTick.lastPrice)
                bar.close = drTick.lastPrice            

    #----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        #self.eventEngine.register(EVENT_TICK, self.procecssTickEvent)

        # 下面自己加的
        #self.eventEngine.register(EVENT_HIS_DATA, self.processHistoricalDataEvent)                # 处理历史数据
        self.eventEngine.register(EVENT_HIS_DATA, self.processHistoricalDataEvent)
        self.eventEngine.register(EVENT_HIS_DATA_DOWNLOAD_FINISHED, self.processHistoricalDataDownloadFinished)  # 处理接收到的历史数据
        self.eventEngine.register(EVENT_TIMER, self.processTimerChecker)                          # 处理策略周期事件
        self.eventEngine.register(EVENT_STR_INIT_DATA, self.processStrategyInitDataEvent)         # 处理策略初始化所需的数据，在 ctaEngine载入策略时，就把 vtSymbol, contract存入事件中。

    # --------------------------------------------------------------------
    def test(self,event):
        print 'test for historical data',event

    #----------------------------------------------------------------------
    def insertData(self, dbName, collectionName, data):
        """插入数据到数据库（这里的data可以是CtaTickData或者CtaBarData）"""
        self.mainEngine.dbInsert(dbName, collectionName, data.__dict__)
        
    #----------------------------------------------------------------------
    def writeDrLog(self, content):
        """快速发出日志事件"""
        log = VtLogData()
        log.logContent = content
        event = Event(type_=EVENT_DATARECORDER_LOG)
        event.dict_['data'] = log
        self.eventEngine.put(event)   


    #############################################################################
        # 本模块主要是自动维护本地历史数据为最新状态
        # processHistoricalDataEvent  处理返回的历史数据
        # processStrategyInitDataEvent  策略启动时触发这个函数，用于下载策略的合约的最近5天的历史数据
        # missingDataReDownload     补下丢失的数据 主循环完成后，再从self.tickerIdKwargsDict中检查是否还有，有则继续循环10次。
        # processHistoricalDataDownloadFinished 该次数据下载完成的标记，开始下载时把tickerId存入self.tickerIdKwargsDict中，当收到 finished时，再从此表中删除
        # ibHistoricalDownLoad      IB 下载的主循环
        #   saveToLocalDatabase     转化之后存入本地数据库
        #   processTimerChecker     处理计时器事件，60秒处理一次，用于定时从网上下载数据，如每隔一小时自动下载一次之类的
        #
        #
    # ----------------------------------------------------------------------   # 自己增加的
    def processHistoricalDataEvent(self, event):
        """收到推送来的历史数据"""
        #print '收到历史数据'

        bar = event.dict_['data']

        # 推送tick到对应的策略实例进行处理
        if bar.vtSymbol in self.vtSymbolContractDict:
            # 将vtBarData数据转化为ctaBarData
            hisBar = HisBarData()

            d = hisBar.__dict__
            for key in d.keys():
                d[key] = bar.__getattribute__(key)      # 只获取那些 HisBarData有的字段，其它丢掉。

            # 送去保存
            self.saveToLocalDatabase(bar=hisBar)

    def saveToLocalDatabase(self, bar=None, tick=None):
        """存入本地数据中"""
        newBar = copy.copy(bar)
        barsize = newBar.barsize
        dbName = BARSIZE_DBNAME_DICT.get(barsize)
        if not dbName:
            print '找不到对应的数据库'
            return
        vtSymbol = newBar.vtSymbol
        #key = '.'.join([vtSymbol, str(barsize)])  # 品种.周期
        self.mainEngine.updateDbData(dbName=dbName, collectionName=vtSymbol, data=newBar)

    def processStrategyInitDataEvent(self,event):
        """处理策略初始化所需的历史数据
        策略载入时即把 vtSymbol传递到事件中，
        这里接收到后即开始下载最近几天的数据，以后策略直接从库中读取
        """
        print '策略载入时，处理相关数据'
        vtSymbol = event.dict_['data']

        if vtSymbol in self.vtSymbolContractDict:
            # 载入历史数据  vtSymbol=None, contract=None, days=30, onlyLastDay=False
            thread = Thread(target=self.downLoadAllDataManager,
                            kwargs=({  'vtSymbol' : vtSymbol,   'fromStrategyInit':True,    'onlyLastDay':True, 'delayTime':1  }))
            thread.start()
            #thread.join()      不能 join()，否则事件处理函数收不到事件。
        else:
            print  u'找不到品种的对应合约，请在 hisData_setting.json 中添加， 历史数据接口跟交易接口不一定相同'

    #----------------------------------------------------------------------
    def processTimerChecker(self, event):
        # 处理 Timer事件
        # 每秒推送来一次
        # 每隔 60秒 检查一次，是否要发出历史数据请求
        return

        self.sbTimerCount += 1                  # 定时器是 一秒 一次

        if self.sbTimerCount < self.sbTimerTrigger:
            return
        else:
            self.sbTimerCount = 0

        # 时间到了就自动下载历史数据
        # self.autoDownloadHisData()        # 每小时下载一次
        # self.downLoadAllDataManager       # 自动下载全部

    # ----------------------------------------------------------------------
    def onTimeDownloadHisData(self):
        """ 定时从网上拉取历史数据 """

        if not self.vtSymbolContractDict:   # 没有合约，就不用下载。直接返回
            return

        # 一些需要每隔几分钟计算一次的事件
        self.minute_timer_counter += 1  # 每次自己加1分钟，

        # 先判断时间和周期
        # 每 15分钟取一次 15周期的数据
        # 每 60分钟取一次，60分钟和日线数据

        now = datetime.now()

        if now.minute%5 ==0:       # 5分钟周期
            barsize = 8
            for key in self.vtSymbolContractDict.keys():
                if self.vtSymbolContractDict[key].get('gatewayName') == 'IB':              # IB 接口
                    contract = self.vtSymbolContractDict[key].get('contract')
                    thread = Thread(target=self.ibHistoricalData, kwargs=({ 'contract':contract,'barSizeSetting': barsize, 'delayTime': 1 }))
                    thread.start()
                    thread.join()

                if self.vtSymbolContractDict[key].get('gatewayName') == 'datayes':              #  联通接口, 没写好
                    pass

        if now.minute%15 ==0:       # 15分钟周期
            barsize = 9
            for key in self.vtSymbolContractDict.keys():
                if self.vtSymbolContractDict[key].get('gatewayName') == 'IB':              # IB 接口
                    contract = self.vtSymbolContractDict[key].get('contract')
                    thread = Thread(target=self.ibHistoricalData, kwargs=({ 'contract':contract,'barSizeSetting': barsize, 'delayTime': 1 }))
                    thread.start()
                    thread.join()

                if self.vtSymbolContractDict[key].get('gatewayName') == 'datayes':              #  联通接口, 没写好
                    pass

        if now.hour != self.pre_hour:       #  小时周期， 同时取日线数据
            self.pre_hour = now.hour
            for key in self.vtSymbolContractDict.keys():
                if self.vtSymbolContractDict[key].get('gatewayName') == 'IB':              # IB 接口
                    contract = self.vtSymbolContractDict[key].get('contract')
                    # 先取小时线数据
                    barsize = 11
                    thread = Thread(target=self.ibHistoricalDownLoad, kwargs=({ 'contract':contract,'barSizeSetting': barsize, 'delayTime': 2, 'onlyLastDay':True  }))   #取小时线
                    thread.start()
                    thread.join()
                    # 同时取日线数据
                    barsize = 12
                    thread = Thread(target=self.ibHistoricalDownLoad, kwargs=({ 'contract':contract,'barSizeSetting': barsize, 'delayTime': 30 ,'onlyLastDay':True  }))   #取日线
                    thread.start()
                    thread.join()

                if self.vtSymbolContractDict[key].get('gatewayName') == 'datayes':              #  联通接口, 没写好
                    pass

        self.pre_minute = now.minute
        return
        # 交易时间
        if not isTradeTime():  # 非交易时间就返回
            self.minute_timer_counter = 0  # 休盘时间清零


    def downLoadAllDataManager(self, vtSymbol = None, contract=None, days=30, onlyLastDay=False , fromStrategyInit = False, **kwargs   ):
        """自动下载所有合约
        先找出合约，再逐个周期下载
        需要传一个 vtSymbol,在这里自动生成合约。
        """

        vtSymbol = vtSymbol
        # 有字典参数的，以字典参数为准
        if kwargs:
            if kwargs.get('vtSymbol'):                                # 是否只下载最近几天的
                vtSymbol = kwargs.get('vtSymbol')
            if kwargs.get('contract'):                                # 是否只下载最近几天的
                contract = kwargs.get('contract')
            if kwargs.get('fromStrategyInit'):                      # 是否来自策略请求
                fromStrategyInit = kwargs.get('fromStrategyInit')
            if kwargs.get('onlyLastDay'):                             # 是否只下载最近几天的
                onlyLastDay = kwargs.get('onlyLastDay')
            if kwargs.get('delayTime'):                               # 是否只下载最近几天的
                delayTime = kwargs.get('delayTime')

        barSizeSetting = [12,11,9,5]              # 哪个周期的列表，存在里面。逐个下载。
        days = days

        if fromStrategyInit == True:            # 如果只是来自策略的请求，则只处理该合约，否则全部。
            if self.vtSymbolContractDict[vtSymbol].get('hisGatewayName') == 'IB':  # IB 接口
                # 先检查这个接口有没有联接
                if not self.mainEngine.gatewayDict['IB'].connected:
                    self.mainEngine.gatewayDict['IB'].connect()
                # 处理合约
                if not contract:    # 优先使用传来的合约，否则去 字典提取
                    contract = self.vtSymbolContractDict[vtSymbol].get('contract')
                # 取出各个周期
                for barsize in barSizeSetting:
                    thread = Thread(target=self.ibHistoricalDownLoad, kwargs=(
                    {'contract':contract, 'barSizeSetting': barsize, 'days': days, 'onlyLastDay': onlyLastDay,
                     'delayTime': 2}))
                    thread.start()
                    thread.join()  # 等线程返回再执行下载下一个周期

            else:
                print '其它接口还没写好'
                return
        else:
            if self.vtSymbolContractDict.keys():                          #  不是来自策略，则先看有没有合约
                for key in self.vtSymbolContractDict.keys():   # 所有合约逐个下载
                    if self.vtSymbolContractDict[key].get('hisGatewayName') == 'IB':              # IB 接口
                        # 先检查这个接口有没有联接
                        if not self.mainEngine.gatewayDict['IB'].connected:
                            self.mainEngine.gatewayDict['IB'].connect()
                        # 处理合约
                        if not contract:  # 如果有传来合约，否则去 字典提取
                            contract = self.vtSymbolContractDict[key].get('contract')
                        # 取出各个周期
                        # 先取小时线数据
                        for barsize in barSizeSetting:  # 取出各个周期
                            thread = Thread(target=self.ibHistoricalDownLoad, kwargs=({ 'contract':contract,'barSizeSetting': barsize, 'days':days , 'onlyLastDay':onlyLastDay, 'delayTime': 2 }))
                            thread.start()
                            thread.join()       # 等线程返回再执行下载下一个周期
                    else:
                        print u'其它接口还没写好'
                        return

    def missingDataReDownload(self):
        """
        没有下载到的数据，还会有10次重新下载的机会
        """
        if self.tickerIdKwargsDict:
            self.missingDataReDownloadTimes += 1
            if self.missingDataReDownloadTimes > 10:    # 10次重新下载的机会
                print   u'正在下载丢失的数据 ', self.tickerIdKwargsDict
                return

            for key in self.tickerIdKwargsDict.keys():
                try:
                    tickerIdValue = self.tickerIdKwargsDict.get(key)
                    if tickerIdValue:
                        print  u'reinstall', tickerIdValue.get('vtSymbol')
                        contract = tickerIdValue.get('contractReq' )
                        endDateTime = tickerIdValue.get('endDateTime')
                        barSizeSetting = tickerIdValue.get('barSizeSetting')
                        whatToShow = tickerIdValue.get('whatToShow')
                        del self.tickerIdKwargsDict[key]                    # to re install must dele the old one
                        self.ibHistoricalDownLoad(  contract=contract, endDateTime=endDateTime,barSizeSetting=barSizeSetting,   whatToShow=whatToShow     )
                except:
                    pass



    def processHistoricalDataDownloadFinished( self, event):
        """收到下载成功的信息后，跟表比较，如果有则表示该ID下载成功，则删除之    tickerIdKwargsDict  """
        #  tickerIdKwargsDict
        tickerId = event.dict_['data']
        if tickerId in self.tickerIdKwargsDict:
            del self.tickerIdKwargsDict[tickerId]


    def ibHistoricalDownLoad(self, contract=None, endDateTime=None,barSizeSetting=None, onlyLastDay=False,  days=None, whatToShow='MIDPOINT' , **kwargs):
        """补全历史数据
        建议收盘之后再操作
        传递进来 4 个参数：
        合约：下载哪个合约；
        下载时间长度：要下载多久的数据，
        周期：下载哪个周期的。
        onlyLastDay 是否只下载最新的数据， 只下最新的则 日线2天，其它周期一天
        参数以字典为准。
        读取数据量限制：1min 1D; 5 mins:1W; 15 mins: 2W;  1 hour: 1M; 1 day : 1Y;
        """
        # 有字典参数的，以字典参数为准
        if kwargs:
            if kwargs.get('contract'):
                contract = kwargs.get('contract')                   # 要下载的合约
            if kwargs.get('barSizeSetting'):
                barSizeSetting = kwargs.get('barSizeSetting')       # 要下载的周期， 通过这个参数，还要判断每次下载几天的。
            if kwargs.get('endDateTime'):
                endDateTime = kwargs.get('endDateTime')  # 要下载的周期， 通过这个参数，还要判断每次下载几天的。
            if kwargs.get('days'):                                  # 下载多久的
                days = kwargs.get('days')
            if kwargs.get('onlyLastDay'):                           # 是否只下载最近几天的
                onlyLastDay = kwargs.get('onlyLastDay')
            if kwargs.get('delayTime'):                           # 是否只下载最近几天的
                delayTime = kwargs.get('delayTime')
            if kwargs.get('whatToShow'):                           # 要拉取什么样的价格回来
                whatToShow = kwargs.get('whatToShow')


        # 需要总共下载多少天数据
        if days:
            days = days                 # 天数
        else:
            days = 30                   # 默认为 30天

        if onlyLastDay:                 # 只下5天，onlyLastDay通常用于策略的初始化的历史数据
            days = self.initForStrategyDays

        if not endDateTime:     #
            beginDateTime = toESTtime() - timedelta(days=days)      # 计算开始日期
        else:
            beginDateTime = toESTtime(estdatetime=endDateTime)  - timedelta(days=days)


        whatToShow = whatToShow

        if barSizeSetting == 11:      # 如果是小时线
            deltaday = 29
            durationStr = '1 M'
        elif barSizeSetting == 9:     # 如果是15分钟
            deltaday = 13
            durationStr = '2 W'
        elif  barSizeSetting == 12:   # 如果是日线
            deltaday = 360
            durationStr = '1 Y'
        elif  barSizeSetting == 5:   # 如果是 1分钟线
            deltaday = 1
            durationStr = '1 D'
        else:
            print u'周期没法识别。返回'
            return
        tickerId = 10000        # 请求历史数据的tickerId，从10000以上，以免跟其它的混。
        counter = 0
        firstDate = toESTtime()
        while True:
            # 计算结束日期
            if counter > 0:             # 循环一次以上，日期递减
                endDateTime = endDateTime - timedelta(days=deltaday)
            elif counter == 0:                      # 第一次循环，
                if not endDateTime:
                    endDateTime = firstDate          # 没有传入结束日期，则以今天算起
                elif endDateTime:
                    endDateTime = endDateTime        # 有传入的结束日期，则以传入的日期来算

            if endDateTime < beginDateTime :
                if self.tickerIdKwargsDict:   #有内容则代表有一些没有下载成功。
                    print  u'现在开始重新下载刚才丢失的数据',self.tickerIdKwargsDict
                    self.missingDataReDownloadTimes = 0
                    self.missingDataReDownload()
                else:
                    print u'下载载完成', endDateTime, u'合约：', contract.symbol, u'K线周期：', BARSIZE_DICT.get(barSizeSetting), u'每次请求长度：', durationStr, u'此次下载长度：', days
                return True
            else:
                print  u'本地时间：', datetime.now(), u'endDateTime:', endDateTime


            tickerId += 1
            endDateTimeStr = toESTtime(estdatetime=endDateTime, returnStr=True)
            # 把相关参数存入表中，到时候检查会不会遗漏数据
            self.tickerIdKwargsDict[tickerId]={
                                                'vtSymbol':contract.symbol,
                                                'contractReq': contract,
                                                'endDateTime': endDateTime,
                                                'durationStr': durationStr,
                                                'barSizeSetting': barSizeSetting,
                                                'whatToShow': whatToShow
                                                                        }

            self.mainEngine.reqHistoricalData(gatewayName='IB', tickerId = tickerId, contractReq=contract,
                                          endDateTimeStr=endDateTimeStr, durationStr=durationStr,
                                          barSizeSetting=barSizeSetting, whatToShow=whatToShow
                                          )

            counter += 1        # 本合约所有周期的计数
            sleep(12)  # 按10分钟可以下载60次来计算，10秒可以下1次。

