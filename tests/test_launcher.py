'''
Basic agent/scenario launching
'''
from pysipp.agent import client, server
from pysipp.launch import PopenRunner


def run_blocking(*agents):
    runner = PopenRunner(agents)
    assert not runner.is_alive()
    runner()
    assert not runner.is_alive()
    return runner


def test_agent_fails():
    uas = server()
    # apply bogus ip which can't be bound
    uas.local_host, uas.local_port = '99.99.99.99', 5060
    # client calls server at bogus addr
    uac = client(uas.local_host, uas.local_port)
    uac.recv_timeout = 1  # avoids SIPp issue #176

    runner = run_blocking(uas, uac)

    # fails due to invalid ip
    uasproc = runner.agents[uas]
    assert uasproc.streams.stderr
    assert uasproc.returncode == 255, uasproc.streams.stderr

    # killed by signal
    uacproc = runner.agents[uac]
    # assert not uacproc.streams.stderr  # sometimes this has a log msg?
    ret = uacproc.returncode
    # killed by SIGUSR1 or terminates before it starts (racy)
    assert ret == -10 or ret == 0


def test_default_scen(default_agents):
    runner = run_blocking(*default_agents)

    # both agents should be successful
    for ua, proc in runner.agents.items():
        assert not proc.returncode
