import logging

LOG_FORMAT = ("%(asctime)s [%(levelname)s] %(name)s %(filename)s:%(lineno)d "
              ": %(message)s")
DATE_FORMAT = '%b %d %H:%M:%S'

def get_logger():
    return logging.getLogger('pysipp')
