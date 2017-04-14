# encoding: UTF-8

'''
期货回测模块相关的GUI控制组件
'''

from uiBasicWidget import QtGui, QtCore, BasicCell
from eventEngine import *

import os
import csv
import json


########################################################################
class FutureValueMonitor(QtGui.QTableWidget):
    """参数监控"""
    signal = QtCore.pyqtSignal(type(Event()))

    # ----------------------------------------------------------------------
    def __init__(self, futureBacktestEngine, eventEngine, name, parent=None):
        """Constructor"""
        super(FutureValueMonitor, self).__init__(parent)

        self.futureBacktestEngine = futureBacktestEngine
        self.eventEngine = eventEngine
        self.name = name

        self.data = {}
        self.keyCellDict = {}
        self.lables = ['run_id', 'strategy_file', 'start_date', 'end_date', 'future_starting_cash',
                       'frequency', 'matching_type', 'benchmark', 'slippage', 'commission_multiplier',
                       'margin_multiplier']
        self.typeMap = [int, str, str, str, int, str, str, str, float, float, float]
        self.inited = False

        self.initUi()

    # ----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setRowCount(1)
        self.verticalHeader().setVisible(False)

        self.setMaximumHeight(self.sizeHint().height())

    # ----------------------------------------------------------------------
    def updateData(self, data):
        """更新数据"""
        self.data = data

        if not self.inited:
            if 'run_id' in data.keys():
                self.setEditTriggers(self.DoubleClicked)

                self.setColumnCount(len(self.lables))
                self.setFixedHeight(80)

                self.setHorizontalHeaderLabels(self.lables)
                self.resizeColumnsToContents()
                self.resizeRowsToContents()

                col = 0

                cell = QtGui.QTableWidgetItem(unicode(data['run_id']))
                self.resizeColumnsToContents()
                self.keyCellDict['run_id'] = cell
                self.setItem(0, col, cell)
                col += 1

                cell = QtGui.QTableWidgetItem(unicode(data['strategy_file']))
                self.resizeColumnsToContents()
                self.keyCellDict['strategy_file'] = cell
                self.setItem(0, col, cell)
                col += 1

                cell = QtGui.QTableWidgetItem(unicode(data['start_date']))
                self.resizeColumnsToContents()
                self.keyCellDict['start_date'] = cell
                self.setItem(0, col, cell)
                col += 1

                cell = QtGui.QTableWidgetItem(unicode(data['end_date']))
                self.resizeColumnsToContents()
                self.keyCellDict['end_date'] = cell
                self.setItem(0, col, cell)
                col += 1

                """
                cell = QtGui.QCalendarWidget()
                self.resizeColumnsToContents()
                self.resizeRowsToContents()
                self.keyCellDict['start_date'] = cell
                self.setCellWidget(0, col, cell)
                col += 1

                cell = QtGui.QCalendarWidget()
                self.resizeColumnsToContents()
                self.resizeRowsToContents()
                self.keyCellDict['end_date'] = cell
                self.setCellWidget(0, col, cell)
                col += 1
                """

                cell = QtGui.QTableWidgetItem(unicode(data['future_starting_cash']))
                self.resizeColumnsToContents()
                self.keyCellDict['future_starting_cash'] = cell
                self.setItem(0, col, cell)
                col += 1

                cell = QtGui.QComboBox()
                cell.addItem("1d")
                cell.addItem("1m")
                cell.addItem("tick")
                self.resizeColumnsToContents()
                self.keyCellDict['frequency'] = cell
                self.setCellWidget(0, col, cell)
                cell.currentIndexChanged.connect(self.sendChangeSignal2)
                col += 1

                cell = QtGui.QComboBox()
                cell.addItem("current_bar")
                cell.addItem("next_bar")
                self.resizeColumnsToContents()
                self.keyCellDict['matching_type'] = cell
                self.setCellWidget(0, col, cell)
                cell.currentIndexChanged.connect(self.sendChangeSignal3)
                col += 1

                cell = QtGui.QTableWidgetItem(unicode(data['benchmark']))
                self.resizeColumnsToContents()
                self.keyCellDict['benchmark'] = cell
                self.setItem(0, col, cell)
                col += 1

                cell = QtGui.QTableWidgetItem(unicode(data['slippage']))
                self.resizeColumnsToContents()
                self.keyCellDict['slippage'] = cell
                self.setItem(0, col, cell)
                col += 1

                cell = QtGui.QTableWidgetItem(unicode(data['commission_multiplier']))
                self.resizeColumnsToContents()
                self.keyCellDict['commission_multiplier'] = cell
                self.setItem(0, col, cell)
                col += 1

                cell = QtGui.QTableWidgetItem(unicode(data['margin_multiplier']))
                self.resizeColumnsToContents()
                self.keyCellDict['margin_multiplier'] = cell
                self.setItem(0, col, cell)
                col += 1

            else:
                self.setEditTriggers(self.NoEditTriggers)

                self.setColumnCount(len(data))
                self.setFixedHeight(80)

                self.setHorizontalHeaderLabels(data.keys())
                self.resizeColumnsToContents()

                col = 0

                for k, v in data.items():
                    cell = QtGui.QTableWidgetItem(unicode(v))
                    self.keyCellDict[k] = cell
                    self.setItem(0, col, cell)
                    col += 1

            self.inited = True
        else:
            for k, v in data.items():
                cell = self.keyCellDict[k]
                cell.setText(unicode(v))

        self.cellChanged.connect(self.sendChangeSignal)

    # ----------------------------------------------------------------------
    def sendChangeSignal(self):
        sentData = self.data
        col = self.currentColumn()
        sentData[self.lables[col]] = self.typeMap[col](self.keyCellDict[self.lables[col]].text())

        event = Event(type_=EVENT_SET_CHANGED + self.name)
        event.dict_ = sentData
        event.dict_['name'] = self.name
        self.eventEngine.put(event)
        self.data = sentData

    # ----------------------------------------------------------------------
    def sendChangeSignal2(self):
        sentData = self.data
        col = 5
        sentData[self.lables[col]] = self.typeMap[col](self.keyCellDict[self.lables[col]].currentText())

        event = Event(type_=EVENT_SET_CHANGED + self.name)
        event.dict_ = sentData
        event.dict_['name'] = self.name
        self.eventEngine.put(event)
        self.data = sentData

    # ----------------------------------------------------------------------
    def sendChangeSignal3(self):
        sentData = self.data
        col = 6
        sentData[self.lables[col]] = self.typeMap[col](self.keyCellDict[self.lables[col]].currentText())

        event = Event(type_=EVENT_SET_CHANGED + self.name)
        event.dict_ = sentData
        event.dict_['name'] = self.name
        self.eventEngine.put(event)
        self.data = sentData


########################################################################
class FutureStrategyManager(QtGui.QGroupBox):
    """策略管理组件"""
    signal = QtCore.pyqtSignal(type(Event()))

    # ----------------------------------------------------------------------
    def __init__(self, futureBacktestEngine, eventEngine, name, runID, parent=None):
        """Constructor"""
        super(FutureStrategyManager, self).__init__(parent)

        self.futureBacktestEngine = futureBacktestEngine
        self.eventEngine = eventEngine
        self.name = name
        self.runID = runID

        path = os.path.abspath(os.path.dirname(__file__)) + '/result/' + self.name + '/'
        if not os.path.exists(path):
            os.makedirs(path)  # 创建路径

        with open(os.path.abspath(os.path.dirname(__file__)) + '/config_template.json', 'r') as f:
            self.setting = json.load(f)
            self.setting['base']['run_id'] = self.runID
            self.setting['base']['strategy_file'] = os.path.abspath(
                os.path.dirname(__file__)) + '/strategy/' + self.name + '.py'
            self.setting['mod']['sys_analyser']['output_file'] = os.path.abspath(
                os.path.dirname(__file__)) + '/result/' + self.name + '/result.pkl'
            #self.setting['mod']['sys_analyser']['plot'] = os.path.expanduser("~")
            self.setting['mod']['sys_analyser']['plot_save_file'] = os.path.abspath(
                os.path.dirname(__file__)) + '/result/' + self.name + '/result.png'
            self.setting['mod']['sys_analyser']['report_save_path'] = os.path.abspath(
                os.path.dirname(__file__)) + '/result/'
            mongo = json.load(open(os.path.dirname(os.getcwd())+'/InplusTrader/VT_setting.json','r'))
            self.setting['mod']['sys_inplustrader']['mongo'] = mongo['mongoHost']


        self.base = self.setting['base']
        self.extra = self.setting['extra']

        self.config = {}

        self.initUi()
        self.updateMonitor()
        self.register()

    # ----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setTitle(self.name)

        self.baseMonitor = FutureValueMonitor(self.futureBacktestEngine, self.eventEngine, self.name)
        self.extraMonitor = FutureValueMonitor(self.futureBacktestEngine, self.eventEngine, self.name)

        height = 60
        self.baseMonitor.setFixedHeight(height)
        self.extraMonitor.setFixedHeight(height)

        buttonEdit = QtGui.QPushButton(u'编辑策略')
        buttonStart = QtGui.QPushButton(u'启动回测')
        buttonShow = QtGui.QPushButton(u'绩效报告')
        buttonEdit.clicked.connect(self.edit)
        buttonStart.clicked.connect(self.start)
        buttonShow.clicked.connect(self.show)

        hbox1 = QtGui.QHBoxLayout()
        hbox1.addWidget(buttonEdit)
        hbox1.addWidget(buttonStart)
        hbox1.addWidget(buttonShow)
        hbox1.addStretch()

        hbox2 = QtGui.QHBoxLayout()
        hbox2.addWidget(self.baseMonitor)

        vbox1 = QtGui.QHBoxLayout()
        vbox1.addWidget(self.extraMonitor)

        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(hbox1)
        vbox.addLayout(hbox2)
        vbox.addLayout(vbox1)

        self.setLayout(vbox)

    # ----------------------------------------------------------------------
    def edit(self):
        self.textBrowser = QtGui.QTextBrowser()
        self.textBrowser.setGeometry(QtCore.QRect(0, 0, 1000, 1000))
        self.textBrowser.setReadOnly(False)
        self.textBrowser.setObjectName(QtCore.QString.fromUtf8("textBrowser"))

        f = open(self.setting['base']['strategy_file'])
        my_data = f.read()
        f.close()
        self.textBrowser.append(my_data.decode('utf-8'))
        self.textBrowser.showMaximized()

    # ----------------------------------------------------------------------
    def start(self):
        """启动回测"""
        self.config = self.setting
        self.futureBacktestEngine.writeBktLog(self.name + u'策略回测中')
        self.futureBacktestEngine.run(self.config)
        self.futureBacktestEngine.writeBktLog(self.name + u'策略回测成功')

    # ----------------------------------------------------------------------
    def show(self):
        """触发显示绩效报告事件（通常用于通知GUI更新）"""
        self.futureBacktestEngine.writeBktLog(self.name + u'绩效报告创建中')
        event = Event(type_=EVENT_BKT_STRATEGY + self.name)
        event.dict_['name'] = self.name
        self.eventEngine.put(event)

    # ----------------------------------------------------------------------
    def updateMonitor(self):
        """显示回测参数最新状态"""
        self.baseMonitor.updateData(self.base)
        self.extraMonitor.updateData(self.extra)

    # ----------------------------------------------------------------------
    def updateSetting(self, event):
        self.setting['base'] = event.dict_
        self.setting['mod']['sys_inplustrader']['matching_type'] = event.dict_['matching_type']
        self.setting['mod']['sys_inplustrader']['slippage'] = event.dict_['slippage']
        self.setting['mod']['sys_inplustrader']['commission_multiplier'] = event.dict_['commission_multiplier']


    # ----------------------------------------------------------------------
    def register(self):
        """注册事件监听"""
        self.signal.connect(self.updateSetting)
        self.eventEngine.register(EVENT_SET_CHANGED + self.name, self.signal.emit)


class FutureBacktestEngineManager(QtGui.QWidget):
    """CTA引擎管理组件"""
    signal = QtCore.pyqtSignal(type(Event()))
    signal2 = QtCore.pyqtSignal(type(Event()))

    # ----------------------------------------------------------------------
    def __init__(self, futureBacktestEngine, eventEngine, parent=None):
        """Constructor"""
        super(FutureBacktestEngineManager, self).__init__(parent)

        self.futureBacktestEngine = futureBacktestEngine
        self.eventEngine = eventEngine

        self.strategyLoaded = False

        self.initUi()
        self.registerEvent()

        # 记录日志
        self.futureBacktestEngine.writeBktLog(u'期货回测引擎启动成功')

    # ----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setWindowTitle(u'期货策略回测')

        # 按钮
        newButton = QtGui.QPushButton(u'新建策略')
        loadButton = QtGui.QPushButton(u'加载策略')

        newButton.clicked.connect(self.new)
        loadButton.clicked.connect(self.load)

        # 滚动区域，放置所有的CtaStrategyManager
        self.scrollArea = QtGui.QScrollArea()
        self.scrollArea.setWidgetResizable(True)

        # 回测结果区域，Tab显示各项报告
        self.tabWidget = QtGui.QTabWidget(self)

        self.model = QtGui.QStandardItemModel(self)
        self.summaryView = QtGui.QTableView(self)
        self.summaryView.setModel(self.model)
        self.summaryView.horizontalHeader().setStretchLastSection(True)
        self.summaryView.setEditTriggers(self.summaryView.NoEditTriggers)
        self.summaryView.setMaximumHeight(400)
        self.summaryView.resizeColumnsToContents()

        self.model2 = QtGui.QStandardItemModel(self)
        self.total_portfoliosView = QtGui.QTableView(self)
        self.total_portfoliosView.setModel(self.model2)
        self.total_portfoliosView.horizontalHeader().setStretchLastSection(True)
        self.total_portfoliosView.setEditTriggers(self.total_portfoliosView.NoEditTriggers)
        self.total_portfoliosView.setMaximumHeight(400)
        self.total_portfoliosView.resizeColumnsToContents()

        self.model3 = QtGui.QStandardItemModel(self)
        self.future_portfoliosView = QtGui.QTableView(self)
        self.future_portfoliosView.setModel(self.model3)
        self.future_portfoliosView.horizontalHeader().setStretchLastSection(True)
        self.future_portfoliosView.setEditTriggers(self.future_portfoliosView.NoEditTriggers)
        self.future_portfoliosView.setMaximumHeight(400)
        self.future_portfoliosView.resizeColumnsToContents()

        self.model4 = QtGui.QStandardItemModel(self)
        self.future_positionsView = QtGui.QTableView(self)
        self.future_positionsView.setModel(self.model4)
        self.future_positionsView.horizontalHeader().setStretchLastSection(True)
        self.future_positionsView.setEditTriggers(self.future_positionsView.NoEditTriggers)
        self.future_positionsView.setMaximumHeight(400)
        self.future_positionsView.resizeColumnsToContents()

        self.model5 = QtGui.QStandardItemModel(self)
        self.tradesView = QtGui.QTableView(self)
        self.tradesView.setModel(self.model5)
        self.tradesView.horizontalHeader().setStretchLastSection(True)
        self.tradesView.horizontalHeader().setVisible(False)
        self.tradesView.setEditTriggers(self.tradesView.NoEditTriggers)
        self.tradesView.setMaximumHeight(400)
        self.tradesView.resizeColumnsToContents()

        self.tabWidget.addTab(self.summaryView, "summary")
        self.tabWidget.addTab(self.total_portfoliosView, "total_portfolios")
        self.tabWidget.addTab(self.future_portfoliosView, "future_portfolios")
        self.tabWidget.addTab(self.future_positionsView, "future_positions")
        self.tabWidget.addTab(self.tradesView, "trades")

        # 回测图表
        Button1 = QtGui.QPushButton(u'交易资料')
        Button2 = QtGui.QPushButton(u'周期分析')
        Button3 = QtGui.QPushButton(u'策略分析')
        Button4 = QtGui.QPushButton(u'交易分析')

        # Button1.clicked.connect(self.show1)
        # Button2.clicked.connect(self.show2)
        # Button3.clicked.connect(self.show3)
        # Button4.clicked.connect(self.show4)

        # 回测组件的日志监控
        self.bktLogMonitor = QtGui.QTextEdit()
        self.bktLogMonitor.setReadOnly(True)
        self.bktLogMonitor.setMaximumHeight(100)

        # 设置布局
        hbox2 = QtGui.QHBoxLayout()
        hbox2.addWidget(newButton)
        hbox2.addWidget(loadButton)
        hbox2.addStretch()

        vbox2 = QtGui.QVBoxLayout()
        vbox2.addWidget(Button1)
        vbox2.addWidget(Button2)
        vbox2.addWidget(Button3)
        vbox2.addWidget(Button4)
        vbox2.addStretch()

        hbox3 = QtGui.QHBoxLayout()
        hbox3.addLayout(vbox2)
        hbox3.addWidget(self.tabWidget)

        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(hbox2)
        vbox.addWidget(self.scrollArea)
        vbox.setSpacing(20)
        vbox.addLayout(hbox3)
        # vbox.addWidget(self.tabWidget)
        vbox.setSpacing(20)
        vbox.addWidget(self.bktLogMonitor)
        self.setLayout(vbox)

    # ----------------------------------------------------------------------
    def initStrategyManager(self):
        """初始化策略管理组件界面"""
        w = QtGui.QWidget()
        vbox = QtGui.QVBoxLayout()
        self.runID = 9999

        for name in self.futureBacktestEngine.strategyDict.keys():
            strategyManager = FutureStrategyManager(self.futureBacktestEngine, self.eventEngine, name, self.runID)
            vbox.addWidget(strategyManager)
            self.runID -= 1

            self.signal2.connect(self.updateBktResult)
            self.eventEngine.register(EVENT_BKT_STRATEGY + name, self.signal2.emit)

        vbox.addStretch()

        w.setLayout(vbox)
        self.scrollArea.setWidget(w)

        # ----------------------------------------------------------------------

    def load(self):
        """加载策略"""
        if not self.strategyLoaded:
            self.futureBacktestEngine.loadStrategy()
            self.initStrategyManager()
            self.strategyLoaded = True
            self.futureBacktestEngine.writeBktLog(u'策略加载成功')

    # ----------------------------------------------------------------------
    def new(self):
        self.futureBacktestEngine.writeBktLog(u'策略新建成功')

    # ----------------------------------------------------------------------
    def updateBktResult(self, event):
        name = event.dict_['name']
        fileName = os.path.abspath(os.path.dirname(__file__)) + '/result/' + name + '/summary.csv'
        fileName2 = os.path.abspath(os.path.dirname(__file__)) + '/result/' + name + '/total_portfolios.csv'
        fileName3 = os.path.abspath(os.path.dirname(__file__)) + '/result/' + name + '/future_portfolios.csv'
        fileName4 = os.path.abspath(os.path.dirname(__file__)) + '/result/' + name + '/future_positions.csv'
        fileName5 = os.path.abspath(os.path.dirname(__file__)) + '/result/' + name + '/trades.csv'

        self.model.clear()
        self.model2.clear()
        self.model3.clear()
        self.model4.clear()
        self.model5.clear()

        with open(fileName, "rb") as fileInput:
            for row in csv.reader(fileInput):
                items = [
                    QtGui.QStandardItem(field.decode('utf-8'))
                    for field in row
                ]
                self.model.appendRow(items)
                self.summaryView.resizeColumnsToContents()
            fileInput.close()

        with open(fileName2, "rb") as fileInput:
            isLable = True
            for row in csv.reader(fileInput):
                if isLable:
                    items = [field for field in row]
                    self.model2.setHorizontalHeaderLabels(items)
                    isLable = False
                else:
                    items = [
                        QtGui.QStandardItem(field.decode('utf-8'))
                        for field in row
                    ]
                    self.model2.appendRow(items)
                self.total_portfoliosView.resizeColumnsToContents()
            fileInput.close()

        with open(fileName3, "rb") as fileInput:
            isLable = True
            for row in csv.reader(fileInput):
                if isLable:
                    items = [field for field in row]
                    self.model3.setHorizontalHeaderLabels(items)
                    isLable = False
                else:
                    items = [
                        QtGui.QStandardItem(field.decode('utf-8'))
                        for field in row
                    ]
                    self.model3.appendRow(items)
                self.future_portfoliosView.resizeColumnsToContents()
            fileInput.close()

        with open(fileName4, "rb") as fileInput:
            isLable = True
            for row in csv.reader(fileInput):
                if isLable:
                    items = [field for field in row]
                    self.model4.setHorizontalHeaderLabels(items)
                    isLable = False
                else:
                    items = [
                        QtGui.QStandardItem(field.decode('utf-8'))
                        for field in row
                    ]
                    self.model4.appendRow(items)
                self.future_positionsView.resizeColumnsToContents()
            fileInput.close()

        with open(fileName5, "rb") as fileInput:
            isLable = True
            for row in csv.reader(fileInput):
                if isLable:
                    items = [field for field in row]
                    self.model5.setHorizontalHeaderLabels(items)
                    isLable = False
                else:
                    items = [
                        QtGui.QStandardItem(field.decode('utf-8'))
                        for field in row
                    ]
                    self.model5.appendRow(items)
                self.tradesView.resizeColumnsToContents()
            fileInput.close()

        self.futureBacktestEngine.writeBktLog(name + u'绩效报告创建成功')

    # ----------------------------------------------------------------------
    def updateBktLog(self, event):
        """更新回测相关日志"""
        log = event.dict_['data']
        content = '\t'.join([log.logTime, log.logContent])
        self.bktLogMonitor.append(content)

    # ----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.signal.connect(self.updateBktLog)
        self.eventEngine.register(EVENT_BKT_LOG, self.signal.emit)
