# encoding: UTF-8

import psutil

from uiBasicWidget import *
from ctaAlgo.uiCtaWidget import CtaEngineManager
from futureBacktest.uiFutureBktWidget import FutureBacktestEngineManager
from stockBacktest.uiStockBktWidget import StockBacktestEngineManager
from dataRecorder.uiDrWidget import DrEngineManager
from riskManager.uiRmWidget import RmEngineManager

########################################################################
class MainWindow(QtGui.QMainWindow):
    """主窗口"""
    signalStatusBar = QtCore.pyqtSignal(type(Event()))

    #----------------------------------------------------------------------
    def __init__(self, mainEngine, eventEngine):
        """Constructor"""
        super(MainWindow, self).__init__()
        
        self.mainEngine = mainEngine
        self.eventEngine = eventEngine
        
        self.widgetDict = {}    # 用来保存子窗口的字典
        
        self.initUi()
        self.loadWindowSettings('custom')
        
    #----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setWindowTitle('InplusTrader')
        self.initCentral()
        self.initMenu()
        self.initStatusBar()
        
    #----------------------------------------------------------------------
    def initCentral(self):
        """初始化中心区域"""
        widgetTradingW, dockTradingW = self.createDock(TradingWidget, u'交易', QtCore.Qt.LeftDockWidgetArea)

        widgetMarketM, dockMarketM = self.createDock(MarketMonitor, u'行情', QtCore.Qt.RightDockWidgetArea)
        widgetOrderM, dockOrderM = self.createDock(OrderMonitor, u'委托', QtCore.Qt.RightDockWidgetArea)
        widgetPriceW, dockPriceW = self.createDock(PriceWidget, u'实时图', QtCore.Qt.RightDockWidgetArea)

        widgetLogM, dockLogM = self.createDock(LogMonitor, u'日志', QtCore.Qt.BottomDockWidgetArea)
        widgetErrorM, dockErrorM = self.createDock(ErrorMonitor, u'错误', QtCore.Qt.BottomDockWidgetArea)
        widgetTradeM, dockTradeM = self.createDock(TradeMonitor, u'成交', QtCore.Qt.BottomDockWidgetArea)

        widgetPositionM, dockPositionM = self.createDock(PositionMonitor, u'持仓', QtCore.Qt.BottomDockWidgetArea)
        widgetAccountM, dockAccountM = self.createDock(AccountMonitor, u'资金', QtCore.Qt.BottomDockWidgetArea)

        widgetDAILYM, dockDAILYM = self.createDock(DAILYMonitor, u'日行情', QtCore.Qt.BottomDockWidgetArea)
        widgetMINM, dockMINM = self.createDock(MINMonitor, u'分钟行情', QtCore.Qt.BottomDockWidgetArea)
        widgetTICKM, dockTICKM = self.createDock(TICKMonitor, u'分时行情', QtCore.Qt.BottomDockWidgetArea)

        self.tabifyDockWidget(dockMarketM, dockOrderM)
        self.tabifyDockWidget(dockMarketM, dockPriceW)

        self.tabifyDockWidget(dockTradeM, dockErrorM)
        self.tabifyDockWidget(dockTradeM, dockLogM)

        self.tabifyDockWidget(dockPositionM, dockAccountM)

        self.tabifyDockWidget(dockDAILYM, dockMINM)
        self.tabifyDockWidget(dockDAILYM, dockTICKM)

        dockMarketM.raise_()
        dockTradeM.raise_()
        dockPositionM.raise_()
        dockDAILYM.raise_()
    
        # 连接组件之间的信号
        widgetPositionM.itemDoubleClicked.connect(widgetTradingW.closePosition)
        widgetPositionM.itemDoubleClicked.connect(widgetPriceW.updateView)
        widgetTradingW.lineSymbol.returnPressed.connect(widgetPriceW.updateView)

        # 保存默认设置
        self.saveWindowSettings('default')

    #----------------------------------------------------------------------
    def initMenu(self):
        """初始化菜单"""
        # 创建菜单
        menubar = self.menuBar()
        
        # 接口数据库相关
        sysMenu = menubar.addMenu(u'系统')
        sysMenu.addAction(self.createAction(u'连接CTP', self.openLoginCTP))
        #self.addConnectAction(sysMenu, 'CTP')
        sysMenu.addSeparator()
        sysMenu.addAction(self.createAction(u'连接数据库', self.openMongo))
        #sysMenu.addAction(self.createAction(u'连接数据库', self.mainEngine.dbConnect))
        sysMenu.addSeparator()
        sysMenu.addAction(self.createAction(u'退出', self.close))

        # 数据相关
        dataMenu = menubar.addMenu(u'数据')
        dataMenu.addAction(self.createAction(u'行情记录', self.openDr))

        # 算法相关
        algoMenu = menubar.addMenu(u'实盘')
        algoMenu.addAction(self.createAction(u'CTA策略', self.openCta))
        
        # 回测相关
        backtestMenu = menubar.addMenu(u'回测')
        backtestMenu.addAction(self.createAction(u'期货回测', self.openFBacktest))
        backtestMenu.addAction(self.createAction(u'股票回测', self.openSBacktest))

        # 风控相关
        riskMenu = menubar.addMenu(u'风控')
        riskMenu.addAction(self.createAction(u'风控管理', self.openRm))

        # In智投
        inAdvisorMenu = menubar.addMenu(u'In智投')
        inAdvisorMenu.addAction(self.createAction(u'In智投', self.openAI)) # to be implemented

        # 其他功能
        functionMenu = menubar.addMenu(u'其他功能')
        functionMenu.addAction(self.createAction(u'查询合约', self.openContract))

        # 帮助
        helpMenu = menubar.addMenu(u'帮助')
        helpMenu.addAction(self.createAction(u'还原', self.restoreWindow))
        helpMenu.addAction(self.createAction(u'关于', self.openAbout))
        helpMenu.addAction(self.createAction(u'测试', self.test))
    
    #----------------------------------------------------------------------
    def initStatusBar(self):
        """初始化状态栏"""
        self.statusLabel = QtGui.QLabel()
        self.statusLabel.setAlignment(QtCore.Qt.AlignLeft)
        
        self.statusBar().addPermanentWidget(self.statusLabel)
        self.statusLabel.setText(self.getCpuMemory())
        
        self.sbCount = 0
        self.sbTrigger = 10     # 10秒刷新一次
        self.signalStatusBar.connect(self.updateStatusBar)
        self.eventEngine.register(EVENT_TIMER, self.signalStatusBar.emit)

    #----------------------------------------------------------------------
    def updateStatusBar(self, event):
        """在状态栏更新CPU和内存信息"""
        self.sbCount += 1
        
        if self.sbCount == self.sbTrigger:
            self.sbCount = 0
            self.statusLabel.setText(self.getCpuMemory())
    
    #----------------------------------------------------------------------
    def getCpuMemory(self):
        """获取CPU和内存状态信息"""
        cpuPercent = psutil.cpu_percent()
        memoryPercent = psutil.virtual_memory().percent
        return u'CPU使用率：%d%%   内存使用率：%d%%' % (cpuPercent, memoryPercent)        

    def addConnectAction(self, menu, gatewayName, displayName=''):
        """增加连接功能"""
        if gatewayName not in self.mainEngine.getAllGatewayNames():
            return
        
        def connect():
            self.mainEngine.connect(gatewayName)
        
        if not displayName:
            displayName = gatewayName
        actionName = u'连接' + displayName
        
        menu.addAction(self.createAction(actionName, connect))
        
    #----------------------------------------------------------------------
    def createAction(self, actionName, function):
        """创建操作功能"""
        action = QtGui.QAction(actionName, self)
        action.triggered.connect(function)
        return action
        
    #----------------------------------------------------------------------
    def test(self):
        """测试按钮用的函数"""
        # 有需要使用手动触发的测试函数可以写在这里
        pass

    #----------------------------------------------------------------------
    def openAbout(self):
        """打开关于"""
        try:
            self.widgetDict['aboutW'].show()
        except KeyError:
            self.widgetDict['aboutW'] = AboutWidget(self)
            self.widgetDict['aboutW'].show()

    #----------------------------------------------------------------------
    def openLoginCTP(self):
        """打开CTP登录界面"""
        try:
            self.widgetDict['loginCTP'].show()
        except KeyError:
            self.widgetDict['loginCTP'] = LoginCTPWidget(self.mainEngine)
            self.widgetDict['loginCTP'].show()

    #----------------------------------------------------------------------
    def openMongo(self):
        """打开Mongodb连接界面"""
        try:
            self.widgetDict['connMongo'].show()
        except KeyError:
            self.widgetDict['connMongo'] = MongoWidget(self.mainEngine)
            self.widgetDict['connMongo'].show()

    #----------------------------------------------------------------------
    def openContract(self):
        """打开合约查询"""
        try:
            self.widgetDict['contractM'].show()
        except KeyError:
            self.widgetDict['contractM'] = ContractMonitor(self.mainEngine)
            self.widgetDict['contractM'].show()

    #----------------------------------------------------------------------
    def openCta(self):
        """打开CTA组件"""
        try:
            self.widgetDict['ctaM'].showMaximized()
        except KeyError:
            self.widgetDict['ctaM'] = CtaEngineManager(self.mainEngine.ctaEngine, self.eventEngine)
            self.widgetDict['ctaM'].showMaximized()
    
    #----------------------------------------------------------------------
    def openFBacktest(self):
        """打开期货回测组件"""
        try:
            self.widgetDict['fBktM'].showMaximized()
        except KeyError:
            self.widgetDict['fBktM'] = FutureBacktestEngineManager(self.mainEngine.futureBacktestEngine, self.eventEngine)
            self.widgetDict['fBktM'].showMaximized()

    # ----------------------------------------------------------------------
    def openSBacktest(self):
        """打开股票回测组件"""
        try:
            self.widgetDict['sBktM'].showMaximized()
        except KeyError:
            self.widgetDict['sBktM'] = StockBacktestEngineManager(self.mainEngine.stockBacktestEngine, self.eventEngine)
            self.widgetDict['sBktM'].showMaximized()

    #----------------------------------------------------------------------
    def openDr(self):
        """打开行情数据记录组件"""
        try:
            self.widgetDict['drM'].showMaximized()
        except KeyError:
            self.widgetDict['drM'] = DrEngineManager(self.mainEngine.drEngine, self.mainEngine, self.eventEngine)
            self.widgetDict['drM'].showMaximized()

    #----------------------------------------------------------------------
    def openRm(self):
        """打开风控组件"""
        try:
            self.widgetDict['rmM'].show()
        except KeyError:
            self.widgetDict['rmM'] = RmEngineManager(self.mainEngine.rmEngine, self.eventEngine)
            self.widgetDict['rmM'].show()      
    
    #----------------------------------------------------------------------
    def openAI(self, event):
        info = QtGui.QMessageBox.question(self, u'InAdvisor',
                                           u'To be implemented', QtGui.QMessageBox.Ok)

    #----------------------------------------------------------------------
    def closeEvent(self, event):
        """关闭事件"""
        reply = QtGui.QMessageBox.question(self, u'退出',
                                           u'确认退出?', QtGui.QMessageBox.Yes | 
                                           QtGui.QMessageBox.No, QtGui.QMessageBox.No)

        if reply == QtGui.QMessageBox.Yes: 
            for widget in self.widgetDict.values():
                widget.close()
            self.saveWindowSettings('custom')
            
            self.mainEngine.exit()
            event.accept()
        else:
            event.ignore()

    #----------------------------------------------------------------------
    def createDock(self, widgetClass, widgetName, widgetArea):
        """创建停靠组件"""
        widget = widgetClass(self.mainEngine, self.eventEngine)
        dock = QtGui.QDockWidget(widgetName)
        dock.setWidget(widget)
        dock.setObjectName(widgetName)
        dock.setFeatures(dock.DockWidgetFloatable|dock.DockWidgetMovable)
        self.addDockWidget(widgetArea, dock)
        return widget, dock
    
    #----------------------------------------------------------------------
    def saveWindowSettings(self, settingName):
        """保存窗口设置"""
        settings = QtCore.QSettings('InplusTrader', settingName)
        settings.setValue('state', self.saveState())
        settings.setValue('geometry', self.saveGeometry())

    #----------------------------------------------------------------------
    def loadWindowSettings(self, settingName):
        """载入窗口设置"""
        settings = QtCore.QSettings('InplusTrader', settingName)
        # 这里由于PyQt4的版本不同，settings.value('state')调用返回的结果可能是：
        # 1. None（初次调用，注册表里无相应记录，因此为空）
        # 2. QByteArray（比较新的PyQt4）
        # 3. QVariant（以下代码正确执行所需的返回结果）
        # 所以为了兼容考虑，这里加了一个try...except，如果是1、2的情况就pass
        # 可能导致主界面的设置无法载入（每次退出时的保存其实是成功了）
        try:
            self.restoreState(settings.value('state').toByteArray())
            self.restoreGeometry(settings.value('geometry').toByteArray())    
        except AttributeError:
            pass
        
    #----------------------------------------------------------------------
    def restoreWindow(self):
        """还原默认窗口设置（还原停靠组件位置）"""
        self.loadWindowSettings('default')
        self.showMaximized()


########################################################################
class AboutWidget(QtGui.QDialog):
    """显示关于信息"""

    #----------------------------------------------------------------------
    def __init__(self, parent=None):
        """Constructor"""
        super(AboutWidget, self).__init__(parent)

        self.initUi()

    #----------------------------------------------------------------------
    def initUi(self):
        """"""
        self.setWindowTitle(u'关于InplusTrader')

        text = u"""
            Developed by Vinson Zheng.

            License：MIT
            
            Website：inpluslab.sysu.edu.cn

            Github：www.github.com/zhengwsh/vnpy

            """

        label = QtGui.QLabel()
        label.setText(text)
        label.setMinimumWidth(500)

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(label)

        self.setLayout(vbox)


########################################################################
class LoginCTPWidget(QtGui.QDialog):
    """登录CTP"""

    # ----------------------------------------------------------------------
    def __init__(self, mainEngine, parent=None):
        """Constructor"""
        super(LoginCTPWidget, self).__init__()
        self.mainEngine = mainEngine

        self.initUi()
        self.loadData()

    # ----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setWindowTitle(u'登录CTP')

        # 设置组件
        labelUserID = QtGui.QLabel(u'账号：')
        labelPassword = QtGui.QLabel(u'密码：')
        labelMdAddress = QtGui.QLabel(u'行情服务器：')
        labelTdAddress = QtGui.QLabel(u'交易服务器：')
        labelBrokerID = QtGui.QLabel(u'经纪商代码')

        self.editUserID = QtGui.QLineEdit()
        self.editPassword = QtGui.QLineEdit()
        self.editMdAddress = QtGui.QLineEdit()
        self.editTdAddress = QtGui.QLineEdit()
        self.editBrokerID = QtGui.QLineEdit()

        self.editUserID.setMinimumWidth(300)

        buttonLogin = QtGui.QPushButton(u'登录')
        buttonCancel = QtGui.QPushButton(u'取消')
        buttonLogin.clicked.connect(self.login)
        self.editUserID.returnPressed.connect(self.login)
        buttonCancel.clicked.connect(self.close)

        # 设置布局
        buttonHBox = QtGui.QHBoxLayout()
        buttonHBox.addStretch()
        buttonHBox.addWidget(buttonLogin)
        buttonHBox.addWidget(buttonCancel)

        grid = QtGui.QGridLayout()
        grid.addWidget(labelUserID, 0, 0)
        grid.addWidget(labelPassword, 1, 0)
        grid.addWidget(labelMdAddress, 2, 0)
        grid.addWidget(labelTdAddress, 3, 0)
        grid.addWidget(labelBrokerID, 4, 0)
        grid.addWidget(self.editUserID, 0, 1)
        grid.addWidget(self.editPassword, 1, 1)
        grid.addWidget(self.editMdAddress, 2, 1)
        grid.addWidget(self.editTdAddress, 3, 1)
        grid.addWidget(self.editBrokerID, 4, 1)
        grid.addLayout(buttonHBox, 5, 0, 1, 2)

        self.setLayout(grid)

    # ----------------------------------------------------------------------
    def loadData(self):
        # 载入json文件
        fileName = './ctpGateway/CTP_connect.json'

        try:
            f = file(fileName)
            # 解析json文件
            setting = json.load(f)
        except IOError:
            return

        try:
            userID = str(setting['userID'])
            password = str(setting['password'])
            brokerID = str(setting['brokerID'])
            tdAddress = str(setting['tdAddress'])
            mdAddress = str(setting['mdAddress'])

            self.editUserID.setText(userID)
            self.editPassword.setEchoMode(QtGui.QLineEdit.Password)
            self.editPassword.setText(password)
            self.editMdAddress.setText(mdAddress)
            self.editTdAddress.setText(tdAddress)
            self.editBrokerID.setText(brokerID)
        except KeyError:
            return

        f.close()

    # ----------------------------------------------------------------------
    def saveData(self):
        # 载入json文件
        fileName = './ctpGateway/CTP_connect.json'

        try:
            setting = {}
            setting['userID'] = str(self.editUserID.text())
            setting['password'] = str(self.editPassword.text())
            setting['mdAddress'] = str(self.editMdAddress.text())
            setting['tdAddress'] = str(self.editTdAddress.text())
            setting['brokerID'] = str(self.editBrokerID.text())
            with open(fileName, 'w') as json_file:
                json_file.write(json.dumps(setting))
        except IOError:
            return

    # ----------------------------------------------------------------------
    def login(self):
        """登录"""
        self.saveData()
        self.mainEngine.connect('CTP')
        self.close()

    # ----------------------------------------------------------------------
    def closeEvent(self, event):
        """关闭事件处理"""
        # 当窗口被关闭时，先保存登录数据，再关闭
        self.saveData()
        event.accept()


########################################################################
class MongoWidget(QtGui.QDialog):
    """登录Mongo"""

    # ----------------------------------------------------------------------
    def __init__(self, mainEngine, parent=None):
        """Constructor"""
        super(MongoWidget, self).__init__()
        self.mainEngine = mainEngine

        self.initUi()
        self.loadData()

    # ----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setWindowTitle(u'连接MongoDB')

        # 设置组件
        labelIp = QtGui.QLabel(u'地址：')
        labelPort = QtGui.QLabel(u'端口：')

        self.editIp = QtGui.QLineEdit()
        self.editPort = QtGui.QLineEdit()
        self.editIp.setMinimumWidth(300)

        buttonConnect = QtGui.QPushButton(u'连接')
        buttonCancel = QtGui.QPushButton(u'取消')
        buttonConnect.clicked.connect(self.connect)
        self.editIp.returnPressed.connect(self.connect)
        buttonCancel.clicked.connect(self.close)

        # 设置布局
        buttonHBox = QtGui.QHBoxLayout()
        buttonHBox.addStretch()
        buttonHBox.addWidget(buttonConnect)
        buttonHBox.addWidget(buttonCancel)

        grid = QtGui.QGridLayout()
        grid.addWidget(labelIp, 0, 0)
        grid.addWidget(labelPort, 1, 0)

        grid.addWidget(self.editIp, 0, 1)
        grid.addWidget(self.editPort, 1, 1)

        grid.addLayout(buttonHBox, 2, 0, 1, 2)

        self.setLayout(grid)

    # ----------------------------------------------------------------------
    def loadData(self):
        # 载入json文件
        fileName = './VT_setting.json'

        try:
            f = file(fileName)
            # 解析json文件
            setting = json.load(f)
        except IOError:
            return

        try:
            ip = str(setting['mongoHost'])
            port = str(setting['mongoPort'])

            self.editIp.setText(ip)
            self.editPort.setText(port)
        except KeyError:
            return

        f.close()

    # ----------------------------------------------------------------------
    def saveData(self):
        # 载入json文件
        fileName = './VT_setting.json'
        try:
            f = file(fileName)
            # 解析json文件
            setting = json.load(f)

            setting['mongoHost'] = str(self.editIp.text())
            setting['mongoPort'] = int(self.editPort.text())

            with open(fileName, 'w') as json_file:
                json_file.write(json.dumps(setting))
                json_file.close()
        except IOError:
            return

    # ----------------------------------------------------------------------
    def connect(self):
        """登录"""
        self.saveData()
        self.mainEngine.dbConnect()
        self.close()

    # ----------------------------------------------------------------------
    def closeEvent(self, event):
        """关闭事件处理"""
        # 当窗口被关闭时，先保存登录数据，再关闭
        self.saveData()
        event.accept()
