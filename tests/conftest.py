'''
unit testing
'''
import pytest
import os
import logging
from pysipp.utils import LOG_FORMAT


def pytest_configure(config):
    # configure log level based on `-v` flags to pytest
    logging.basicConfig(
        level=max(40 - config.option.verbose * 10, 10),
        format=LOG_FORMAT
    )


@pytest.fixture
def scendir():
    path = "{}/scens/".format(os.path.dirname(__file__))
    assert os.path.isdir(path)
    return path
