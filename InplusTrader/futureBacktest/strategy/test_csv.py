from rqalpha.api import *


def init(context):
    IF1706_df = get_csv_as_df()
    context.IF1706_df = IF1706_df


def before_trading(context):
    logger.info(context.IF1706_df)