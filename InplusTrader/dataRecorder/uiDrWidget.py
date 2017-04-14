# encoding: UTF-8

'''
行情记录模块相关的GUI控制组件
'''

import os
import json

from uiBasicWidget import QtGui, QtCore
from eventEngine import *


########################################################################
class TableCell(QtGui.QTableWidgetItem):
    """居中的单元格"""

    #----------------------------------------------------------------------
    def __init__(self, text=None, mainEngine=None):
        """Constructor"""
        super(TableCell, self).__init__()
        self.data = None
        self.setTextAlignment(QtCore.Qt.AlignCenter)
        if text:
            self.setContent(text)
    
    #----------------------------------------------------------------------
    def setContent(self, text):
        """设置内容"""
        if text == '0' or text == '0.0':
            self.setText('')
        else:
            self.setText(text)


########################################################################
class DrEngineManager(QtGui.QWidget):
    """行情数据记录引擎管理组件"""
    signal = QtCore.pyqtSignal(type(Event()))
    signal2 = QtCore.pyqtSignal(type(Event()))

    #----------------------------------------------------------------------
    def __init__(self, drEngine, mainEngine, eventEngine, parent=None):
        """Constructor"""
        super(DrEngineManager, self).__init__(parent)
        
        self.drEngine = drEngine
        self.mainEngine = mainEngine
        self.eventEngine = eventEngine
        
        self.initUi()
        self.updateSetting()
        self.registerEvent() 
        
    #----------------------------------------------------------------------
    def initUi(self):
        """初始化界面"""
        self.setWindowTitle(u'行情数据记录工具')

        # 菜单
        lineSelect = QtGui.QLabel(u'需要收集的合约：')
        buttonSelect = QtGui.QPushButton(u'选择')

        lineType = QtGui.QLabel(u'合成Bar类型：')
        barType = ['1m', '5m', '15m', '30m', '60m']
        comboType = QtGui.QComboBox()
        comboType.addItems(barType)

        lineStart = QtGui.QLabel(u'开始收集：')
        buttonStart = QtGui.QPushButton(u'收集')

        buttonSelect.clicked.connect(self.select)
        buttonStart.clicked.connect(self.start)

        # 记录合约配置监控
        tickLabel = QtGui.QLabel(u'Tick记录')
        self.tickTable = QtGui.QTableWidget()
        self.tickTable.setColumnCount(2)
        self.tickTable.verticalHeader().setVisible(False)
        self.tickTable.setEditTriggers(QtGui.QTableWidget.NoEditTriggers)
        self.tickTable.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)
        self.tickTable.setAlternatingRowColors(True)
        self.tickTable.setHorizontalHeaderLabels([u'合约代码', u'接口'])
        
        barLabel = QtGui.QLabel(u'Bar记录')
        self.barTable = QtGui.QTableWidget()
        self.barTable.setColumnCount(2)
        self.barTable.verticalHeader().setVisible(False)
        self.barTable.setEditTriggers(QtGui.QTableWidget.NoEditTriggers)
        self.barTable.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)
        self.barTable.setAlternatingRowColors(True)        
        self.barTable.setHorizontalHeaderLabels([u'合约代码', u'接口'])

        activeLabel = QtGui.QLabel(u'主力合约')
        self.activeTable = QtGui.QTableWidget()
        self.activeTable.setColumnCount(2)
        self.activeTable.verticalHeader().setVisible(False)
        self.activeTable.setEditTriggers(QtGui.QTableWidget.NoEditTriggers)
        self.activeTable.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)
        self.activeTable.setAlternatingRowColors(True)        
        self.activeTable.setHorizontalHeaderLabels([u'主力代码', u'合约代码'])

        # 日志监控
        self.logMonitor = QtGui.QTextEdit()
        self.logMonitor.setReadOnly(True)
        self.logMonitor.setMinimumHeight(600)

        self.logMonitor2 = QtGui.QTextEdit()
        self.logMonitor2.setReadOnly(True)
        self.logMonitor2.setMinimumHeight(600)

        self.logMonitor3 = QtGui.QTextEdit()
        self.logMonitor3.setReadOnly(True)
        self.logMonitor3.setMinimumHeight(600)

        # 设置布局
        hbox = QtGui.QHBoxLayout()
        hbox.addWidget(lineSelect)
        hbox.addWidget(buttonSelect)
        hbox.addWidget(lineType)
        hbox.addWidget(comboType)
        hbox.addWidget(lineStart)
        hbox.addWidget(buttonStart)

        grid = QtGui.QGridLayout()
        grid.addWidget(tickLabel, 0, 0)
        grid.addWidget(barLabel, 0, 1)
        grid.addWidget(activeLabel, 0, 2)
        grid.addWidget(self.tickTable, 1, 0)
        grid.addWidget(self.barTable, 1, 1)
        grid.addWidget(self.activeTable, 1, 2)

        grid2 = QtGui.QGridLayout()
        grid2.addWidget(self.logMonitor, 0, 0)
        grid2.addWidget(self.logMonitor2, 0, 1)
        grid2.addWidget(self.logMonitor3, 0, 2)

        vbox = QtGui.QVBoxLayout()
        vbox.addLayout(hbox)
        vbox.addLayout(grid)
        vbox.addLayout(grid2)
        self.setLayout(vbox)

    #----------------------------------------------------------------------
    def updateLog(self, event):
        """更新日志"""
        log = event.dict_['data']
        content = '\t'.join([log.logTime, log.logContent])
        self.logMonitor.append(content)

    # ----------------------------------------------------------------------
    def updateLog2(self, event):
        """更新日志"""
        log = event.dict_['data']
        content = '\t'.join([log.logTime, log.logContent])
        self.logMonitor2.append(content)

    #----------------------------------------------------------------------
    def registerEvent(self):
        """注册事件监听"""
        self.signal.connect(self.updateLog)
        self.eventEngine.register(EVENT_DATARECORDER_LOG, self.signal.emit)

        self.signal2.connect(self.updateLog2)
        self.eventEngine.register(EVENT_DATARECORDER_LOG2, self.signal2.emit)
        
    #----------------------------------------------------------------------
    def updateSetting(self):
        """显示引擎行情记录配置"""
        with open(self.drEngine.settingFileName) as f:
            drSetting = json.load(f)
    
            if 'tick' in drSetting:
                l = drSetting['tick']
    
                for setting in l:
                    self.tickTable.insertRow(0)
                    self.tickTable.setItem(0, 0, TableCell(setting[0]))
                    self.tickTable.setItem(0, 1, TableCell(setting[1]))
    
            if 'bar' in drSetting:
                l = drSetting['bar']
    
                for setting in l:
                    self.barTable.insertRow(0)
                    self.barTable.setItem(0, 0, TableCell(setting[0]))
                    self.barTable.setItem(0, 1, TableCell(setting[1]))
    
            if 'active' in drSetting:
                d = drSetting['active']
    
                for activeSymbol, symbol in d.items():
                    self.activeTable.insertRow(0)
                    self.activeTable.setItem(0, 0, TableCell(activeSymbol))
                    self.activeTable.setItem(0, 1, TableCell(symbol))
    
    #----------------------------------------------------------------------
    def select(self):
        pass
    
    #----------------------------------------------------------------------
    def start(self):
        l = self.mainEngine.getAllContracts()
        data = {}
        tick = [[contract.symbol, 'CTP'] for contract in l]
        bar = [[contract.symbol, 'CTP'] for contract in l]
        active = {}
        for contract in l:
            acticeSymbol = filter(str.isalpha, contract.symbol)
            active[acticeSymbol + '88'] = contract.symbol

        data['working'] = True
        data['tick'] = tick
        data['bar'] = bar
        data['active'] = active

        fileName = os.path.abspath(os.path.dirname(__file__)) + '.\\DR_setting.json'
        with open(fileName, 'w') as json_file:
            json_file.write(json.dumps(data))

        self.drEngine.loadSetting()