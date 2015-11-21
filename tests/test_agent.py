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
    assert ua.name is None
    assert '[{}]:{}'.format(*sock) in ua.render()


def test_logdir(ua):
    logdir = ua.logdir
    assert logdir
    cmd = ua.render()
    logs = [token for token in cmd.split() if logdir in token]
    assert len(logs) == 5  # currently default num of logs


def test_client():
    # built-in scen
    remote_sock = ('192.168.1.1', 5060)
    uac = agent.client(*remote_sock)
    cmdstr = uac.render()
    assert '-sn uac' in cmdstr
    assert '[{}]:{}'.format(*remote_sock) in cmdstr

    # pretend script file
    script = '/home/sipp_scen/uac.xml'
    uac2 = agent.client(*remote_sock, scen_file=script)
    cmdstr = uac2.render()
    assert '-sn uac' not in cmdstr
    assert '-sf {}'.format(script) in cmdstr


def test_server():
    uac = agent.server()
    cmdstr = uac.render()
    assert '-sn uas' in cmdstr
    assert not (uac.remote_host and uac.remote_port)


@pytest.mark.parametrize('ua, retcode, kwargs, exc', [
    # test unspecialized ua failure
    (agent.ua(), 255, {}, None),

    # test client failure on bad remote destination
    (agent.client('99.99.99.99', 5060), 1, {}, None),

    # test if server times out it is signalled
    (agent.server(), 0, {'timeout': 1}, launch.TimeoutError)],
    ids=['ua', 'uac', 'uas'],
)
def test_runner_fails(ua, retcode, kwargs, exc):
    """Test failure cases for all types of agents
    """
    assert not ua.runner.is_alive()
    # run it
    if exc:
        pytest.raises(exc, partial(ua.run, **kwargs))
        agents = ua.runner.agents
    else:
        agents = ua.run(**kwargs)

    assert not ua.runner.is_alive()
    assert len(list(ua.runner.iterprocs())) == 0
    assert ua in agents
    assert len(agents) == 1
    proc = agents[ua]
    assert proc.returncode == retcode
