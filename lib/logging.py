import logging
import sys


def configure_logging(level=logging.INFO):
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    # Create formatter
    date_format = '%Y-%m-%d %H:%M:%S'
    log_format = '[%(asctime)-8s][%(levelname)-8s][%(name)-12s]: %(message)s'
    formatter = logging.Formatter(log_format, datefmt=date_format)
    # Create sh handler
    handler_sh = logging.StreamHandler(sys.stdout)
    handler_sh.setLevel(level)
    # Add formatter to handler, and handler to root logger
    handler_sh.setFormatter(formatter)
    root_logger.addHandler(handler_sh)
