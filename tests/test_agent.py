'''
Agent wrapping
'''
import pytest
from functools import partial
from pysipp import agent, launch


@pytest.fixture
def ua():
    return agent.ua()


def test_ua(ua):
    sock = ('10.10.9.9', 5060)
    ua.proxy = sock
    assert ua.name == str(None)
    assert "'[{}]':'{}'".format(*sock) in ua.render()


def test_logdir(ua):
    logdir = ua.logdir
    assert logdir
    cmd = ua.render()
    logs = [token for token in cmd.split() if logdir in token]
    assert len(logs) == len(ua._log_types)  # currently default num of logs


def test_client():
    # built-in scen
    remote_sock = ('192.168.1.1', 5060)
    uac = agent.client(*remote_sock)
    cmdstr = uac.render()
    assert "-sn 'uac'" in cmdstr
    assert "'[{}]':'{}'".format(*remote_sock) in cmdstr

    # pretend script file
    script = '/home/sipp_scen/uac.xml'
    uac2 = agent.client(*remote_sock, scen_file=script)
    cmdstr = uac2.render()
    assert "-sn 'uac'" not in cmdstr
    assert "-sf '{}'".format(script) in cmdstr


def test_server():
    ua = agent.server()
    cmdstr = ua.render()
    assert "-sn 'uas'" in cmdstr
    assert not (ua.remote_host and ua.remote_port)


@pytest.mark.parametrize('ua, retcode, kwargs, exc', [
    # test unspecialized ua failure
    (agent.ua(), 255, {}, RuntimeError),

    # test client failure on bad remote destination
    (agent.client('99.99.99.99', 5060), 1, {}, RuntimeError),

    # test if server times out it is signalled
    (agent.server(), 0, {'timeout': 1}, RuntimeError)],
    ids=['ua', 'uac', 'uas'],
)
def test_call_fails(ua, retcode, kwargs, exc):
    """Test failure cases for all types of agents
    """
    # run it
    if exc:
        with pytest.raises(exc):
            ua(**kwargs)
        runner = ua._runner
        agents = ua._runner.agents
    else:
        agents = ua(**kwargs).agents

    assert not runner.is_alive()
    assert len(list(runner.iterprocs())) == 0
    assert ua in agents
    assert len(agents) == 1
    proc = agents[ua]
    assert proc.returncode == retcode


def test_scenario(default_agents):
    uas, uac = default_agents
    agents = list(default_agents)
    scen = agent.Scenario(agents)

    # verify agents
    assert scen.agents.values() == agents
    assert uas is scen.agents.values()[0]
    assert uac is scen.agents.values()[1]
    # verify servers
    assert uas is scen.servers.values()[0]
    # verify clients
    assert uac is scen.clients.values()[0]

    # ensure mult agent attr setting works
    doggy = 'doggy'
    scen.agents.local_host = doggy
    assert uac.local_host == uas.local_host == doggy

    # same error for any non-spec defined agent attr
    with pytest.raises(AttributeError):
        scen.agents.local_man = 'flasher'

    # multi-setattr on servers only
    scen.servers.remote_host = doggy
    assert uas.remote_host == doggy
    assert uac.remote_host != doggy

    assert scen.name == 'uas_uac'
