from rqalpha import run

config = {
    "base": {
        "strategy_file": "/home/vinson/.rqalpha/examples/buy_and_hold.py",
        "start_date": "2016-06-01",
        "end_date": "2016-12-01",
        "stock_starting_cash": 100000,
        "benchmark": "000300.XSHG",
    },
    "extra": {
        "log_level": "verbose",
    },
    "mod": {
            "sys_simulation": {
                "enabled": True,
                "priority": 100
            },
            "sys_analyser": {
                "priority": 100,
                "enabled": True,
                "record": True,
                "output_file": "/home/vinson/.rqalpha/examples/buy_and_hold/result.pkl",
                "plot": "~",
                "plot_save_file": "/home/vinson/.rqalpha/examples/buy_and_hold/result.png",
                "report_save_path": "/home/vinson/.rqalpha/examples/buy_and_hold/"
            }
        }
}

run(config)
