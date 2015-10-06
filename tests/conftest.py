'''
unit testing
'''
import pytest
import logging
from pysipp.utils import LOG_FORMAT


def pytest_configure(config):
    # configure log level based on `-v` flags to pytest
    logging.basicConfig(
        level=max(40 - config.option.verbose * 10, 10),
        format=LOG_FORMAT
    )
