"""
Basic agent/scenario launching
"""
from pysipp.agent import client
from pysipp.agent import server
from pysipp.launch import PopenRunner


def run_blocking(*agents):
    runner = PopenRunner()
    assert not runner.is_alive()
    runner(ua.render() for ua in agents)
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

    runner = run_blocking(uas, uac)

    # fails due to invalid ip
    uasproc = runner.get(timeout=0)[uas.render()]
    assert uasproc.streams.stderr
    assert uasproc.returncode == 255, uasproc.streams.stderr

    # times out (can't do by signal - SIPp issue #176)
    uacproc = runner.get(timeout=0)[uac.render()]
    # assert not uacproc.streams.stderr  # sometimes this has a log msg?
    ret = uacproc.returncode
    # timed out or terminates before it starts (racy)
    assert ret == -10 or ret == 0 or ret == 1


def test_default_scen(default_agents):
    runner = run_blocking(*default_agents)

    # both agents should be successful
    for cmd, proc in runner.get(timeout=0).items():
        assert not proc.returncode
