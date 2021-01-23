"""
Basic agent/scenario launching
"""
import trio
import pytest

from pysipp.agent import client, server
from pysipp.launch import TrioRunner, run_all_agents, SIPpFailure


def run_blocking(runner, agents):
    assert not runner.is_alive()
    trio.run(run_all_agents, runner, agents, 10)
    assert not runner.is_alive()
    return runner


def test_agent_fails():
    uas = server(call_count=1)
    # apply bogus ip which can't be bound
    uas.local_host, uas.local_port = "99.99.99.99", 5060
    # client calls server at bogus addr
    uac = client(destaddr=(uas.local_host, uas.local_port))
    uac.recv_timeout = 1  # avoids SIPp issue #176
    uac.call_count = 1  # avoids SIPp issue #176

    runner = TrioRunner()
    with pytest.raises(SIPpFailure):
        run_blocking(runner, (uas, uac))

    # fails due to invalid ip
    uasproc = runner._procs[uas.render()]
    print(uasproc.stderr_output)
    assert uasproc.stderr_output
    assert uasproc.returncode == 255, uasproc.streams.stderr

    # killed by signal
    uacproc = runner._procs[uac.render()]
    # assert not uacproc.stderr_output  # sometimes this has a log msg?
    ret = uacproc.returncode
    # killed by SIGUSR1 or terminates before it starts (racy)
    assert ret == -10 or ret == 0


def test_default_scen(default_agents):
    runner = TrioRunner()
    runner = run_blocking(runner, default_agents)

    # both agents should be successful
    for cmd, proc in runner._procs.items():
        assert not proc.returncode
