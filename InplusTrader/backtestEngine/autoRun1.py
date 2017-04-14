# -*- coding: utf-8 -*-
import os, sys
from rqalpha import run


def getConfig():
    # 白名单，设置可以直接在策略代码中指定哪些模块的配置项目
    whitelist = ["base", "extra", "validator", "mod"]

    strategy_name = "pair_trading"

    path = os.path.expanduser("~\\.rqalpha\\res\\" + strategy_name + "\\")
    if not os.path.exists(path):
        os.makedirs(path)  # 创建路径

    config = {
        "base": {
            # 可以指定回测的唯一ID，用户区分多次回测的结果
            "run_id": 9999,
            # 数据源所存储的文件路径
            "data_bundle_path": os.path.expanduser("~\\.rqalpha\\bundle\\"),
            # 启动的策略文件路径
            "strategy_file": os.path.expanduser("~\\.rqalpha\\examples\\" + strategy_name + ".py"),
            # 回测起始日期
            "start_date": "2015-12-16",
            # 回测结束日期(如果是实盘，则忽略该配置)
            "end_date": "2016-12-15",
            # 股票起始资金，默认为0
            "stock_starting_cash": 100000,
            # 期货起始资金，默认为0
            "future_starting_cash": 1000000,
            # 设置策略类型，目前支持 `stock` (股票策略)、`future` (期货策略)及 `stock_future` (混合策略)
            "strategy_type": "future",
            # 运行类型，`b` 为回测，`p` 为模拟交易, `r` 为实盘交易。
            "run_type": "b",
            # 目前支持 `1d` (日线回测) 和 `1m` (分钟线回测)，如果要进行分钟线，请注意是否拥有对应的数据源，目前开源版本是不提供对应的数据源的。
            "frequency": "1d",
            # 启用的回测引擎，目前支持 `current_bar` (当前Bar收盘价撮合) 和 `next_bar` (下一个Bar开盘价撮合)
            "matching_type": "current_bar",
            # Benchmark，如果不设置，默认没有基准参照。
            "benchmark": None,  # "000300.XSHG"
            # 设置滑点
            "slippage": 0.05,
            # 设置手续费乘数，默认为1
            "commission_multiplier": 1,
            # 设置保证金乘数，默认为1
            "margin_multiplier": 1,
            # 在模拟交易和实盘交易中，RQAlpha支持策略的pause && resume，该选项表示开启 resume 功能
            "resume_mode": False,
            # 在模拟交易和实盘交易中，RQAlpha支持策略的pause && resume，该选项表示开启 persist 功能呢，
            # 其会在每个bar结束对进行策略的持仓、账户信息，用户的代码上线文等内容进行持久化
            "persist": False,
            "persist_mode": "real_time",
            # 选择是否开启自动处理, 默认不开启
            "handle_split": False
        },
        "extra": {
            # 选择日期的输出等级，有 `verbose` | `info` | `warning` | `error` 等选项，您可以通过设置 `verbose` 来查看最详细的日志，
            # 或者设置 `error` 只查看错误级别的日志输出
            "log_level": "verbose",
            "user_system_log_disabled": False,
            # 在回测结束后，选择是否查看图形化的收益曲线
            "context_vars": False,
            # force_run_init_when_pt_resume: 在PT的resume模式时，是否强制执行用户init。主要用于用户改代码。
            "force_run_init_when_pt_resume": False,
            # enable_profiler: 是否启动性能分析
            "enable_profiler": False,
            "is_hold": False
        },
        "validator": {
            # cash_return_by_stock_delisted: 开启该项，当持仓股票退市时，按照退市价格返还现金
            "cash_return_by_stock_delisted": False,
            # close_amount: 在执行order_value操作时，进行实际下单数量的校验和scale，默认开启
            "close_amount": True,
            # bar_limit: 在处于涨跌停时，无法买进\卖出，默认开启
            "bar_limit": True
        },
        "mod": {
            # 回测
            "inplus_trader_backtest": {
                "lib": 'rqalpha.mod.inplus_trader_backtest',
                "enabled": True,
                "mongo": "172.18.181.119",
                "priority": 100
            },
            # 回测 / 模拟交易 支持 Mod
            "simulation": {
                "lib": 'rqalpha.mod.simulation',
                "enabled": False,
                "priority": 100
            },
            # 技术分析API
            "funcat_api": {
                "lib": 'rqalpha.mod.funcat_api',
                "enabled": False,
                "priority": 200
            },
            # 开启该选项，可以在命令行查看回测进度
            "progress": {
                "lib": 'rqalpha.mod.progress',
                "enabled": False,
                "priority": 400
            },
            # 接收实时行情运行
            "simple_stock_realtime_trade": {
                "lib": 'rqalpha.mod.simple_stock_realtime_trade',
                "persist_path": ".\\persist\\strategy\\",
                "fps": 3,
                "enabled": False,
                "priority": 500
            },
            # 渐进式输出运行结果
            "progressive_output_csv": {
                "lib": 'rqalpha.mod.progressive_output_csv',
                "enabled": False,
                "output_path": os.path.expanduser("~\\.rqalpha\\res\\" + strategy_name + "\\"),
                "priority": 600
            },
            "risk_manager": {
                "lib": 'rqalpha.mod.risk_manager',
                "enabled": False,
                "priority": 700,
                # available_cash: 查可用资金是否充足，默认开启
                "available_cash": True,
                # available_position: 检查可平仓位是否充足，默认开启
                "available_position": True,
            },
            "analyser": {
                "priority": 100,
                "enabled": True,
                "lib": 'rqalpha.mod.analyser',
                "record": True,
                "output_file": os.path.expanduser("~\\.rqalpha\\res\\" + strategy_name + "\\result.pkl"),
                "plot": os.path.expanduser("~"),
                "plot_save_file": os.path.expanduser("~\\.rqalpha\\res\\" + strategy_name + "\\result.png"),
                "report_save_path": os.path.expanduser("~\\.rqalpha\\res\\")
            }
        }
    }

    return config



if __name__ == '__main__':
    run(getConfig())
