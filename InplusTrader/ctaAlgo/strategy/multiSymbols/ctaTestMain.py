# encoding: UTF-8

import sys
from vtEngine2 import MainEngine
import time,datetime


#----------------------------------------------------------------------
def main():
    """主程序入口"""
    # 重载sys模块，设置默认字符串编码方式为utf8
    reload(sys)
    sys.setdefaultencoding('utf8')

    # 初始化主引擎和主窗口对象
    mainEngine = MainEngine()
    mainEngine.connect('CTP')
    time.sleep(5)
    mainEngine.ctaEngine2.loadSetting()
    mainEngine.ctaEngine2.initStrategy('tradeTest')
    mainEngine.ctaEngine2.startStrategy('tradeTest')
if __name__ == '__main__':
    main()