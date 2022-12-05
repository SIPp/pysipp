"""
unit testing
"""
import os

import pytest

from pysipp import agent
from pysipp import scenario
from pysipp import utils


def pytest_configure(config):
    # configure log level based on `-v` flags to pytest
    utils.log_to_stderr(
        level=max(40 - config.option.verbose * 10, 10),
    )


@pytest.fixture
def scendir():
    path = "{}/scens/".format(os.path.dirname(__file__))
    assert os.path.isdir(path)
    return path


@pytest.fixture
def default_agents():
    uas = agent.server(local_host="127.0.0.1", local_port=5060, call_count=1)
    uac = agent.client(call_count=1, destaddr=(uas.local_host, uas.local_port))
    return uas, uac


@pytest.fixture(params=[True, False], ids="autolocalsocks={}".format)
def basic_scen(request):
    """The most basic scenario instance"""
    return scenario(autolocalsocks=request.param)
