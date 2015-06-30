'''
Basic agent launching
'''
import pytest
from pysipp.agent import client, server
from pysipp.launch import PopenRunner


def run_blocking(*agents):
    runner = PopenRunner(agents)
    assert not runner.is_alive()
    runner()
    assert not runner.is_alive()
    return runner


# @pytest.mark.parametrize('uas_host, uas_ec,')
def test_agent_fails():
    uas = server()
    # apply bogus ip which can't be bound
    uas.local_host, uas.local_port = '99.99.99.99', 5060
    uac = client(uas.local_host, uas.local_port)

    runner = run_blocking(uas, uac)

    # fails due to invalid ip
    uasproc = runner.agents[uas]
    assert uasproc.streams.stderr
    assert uasproc.returncode == 255

    # killed by signal
    uacproc = runner.agents[uac]
    assert not uacproc.streams.stderr
    assert uacproc.returncode == -10
