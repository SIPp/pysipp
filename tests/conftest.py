'''
unit testing
'''
import pytest
import os
import logging
from pysipp.utils import LOG_FORMAT
from pysipp import agent


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


@pytest.fixture
def default_agents():
    uas = agent.server(local_host='127.0.0.1', local_port=5060)
    uac = agent.client(uas.local_host, uas.local_port)
    return uas, uac
