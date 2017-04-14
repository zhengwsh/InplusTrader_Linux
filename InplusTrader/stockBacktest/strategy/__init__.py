# encoding: UTF-8

'''
动态载入所有的策略
'''

import os

# 用来保存策略位置的字典
STRATEGY_PATH = {}

# 获取目录路径
path = os.path.abspath(os.path.dirname(__file__))

# 遍历strategy目录下的文件
for root, subdirs, files in os.walk(path):
    for name in files:
        # 只有文件名中.py且非.pyc的文件，才是策略文件
        if '.py' in name and '.pyc' not in name and '__init__' not in name:
            STRATEGY_PATH[name.replace('.py', '')] = path + name
