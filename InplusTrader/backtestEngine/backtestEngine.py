from .utils.config import parse_config
from . import main

class  BacktestEngine(object):
    def __init__(self):
        pass

    def run(self, config, source_code=None):
        return main.run(parse_config(config, click_type=False, source_code=source_code), source_code=source_code)

    def update_bundle(self, data_bundle_path=None, confirm=True):
        main.update_bundle(data_bundle_path, confirm)
