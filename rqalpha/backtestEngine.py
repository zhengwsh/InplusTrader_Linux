
class BacktestEngine(object):
    def __init__(self):
        pass


    def run(self, config, source_code=None):
        from .utils.config import parse_config
        from . import main

        return main.run(parse_config(config, click_type=False, source_code=source_code), source_code=source_code)


    def update_bundle(self, data_bundle_path=None, locale="zh_Hans_CN", confirm=True):
        from . import main
        main.update_bundle(data_bundle_path=data_bundle_path, locale=locale, confirm=confirm)
