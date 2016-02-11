'''
Agent wrapping
'''
import pytest
from pysipp import agent, launch, plugin


@pytest.fixture
def ua():
    return agent.Scenario([agent.ua()]).prepare()[0]


def test_ua(ua):
    sock = ('10.10.9.9', 5060)
    ua.proxyaddr = sock
    assert ua.name == str(None)
    assert "'{}':'{}'".format(*sock) in ua.render()


def test_logdir(ua):
    logdir = ua.logdir
    assert logdir
    cmd = ua.render()
    logs = [token for token in cmd.split() if logdir in token]
    assert len(logs) == len(ua._log_types)  # currently default num of logs


def test_client():
    # built-in scen
    remote_sock = ('192.168.1.1', 5060)
    uac = agent.client(destaddr=remote_sock)
    cmdstr = uac.render()
    assert "-sn 'uac'" in cmdstr
    assert "'{}':'{}'".format(*remote_sock) in cmdstr

    # pretend script file
    script = '/home/sipp_scen/uac.xml'
    uac2 = agent.client(destaddr=remote_sock, scen_file=script)
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
    (agent.client(destaddr=('99.99.99.99', 5060)), 1, {}, RuntimeError),

    # test if server times out it is signalled
    (agent.server(), 0, {'timeout': 1}, launch.TimeoutError)],
    ids=['ua', 'uac', 'uas'],
)
def test_failures(ua, retcode, kwargs, exc):
    """Test failure cases for all types of agents
    """
    # run it without raising
    runner = ua(raise_exc=False, **kwargs)
    cmds2procs = runner.get(timeout=0)
    assert not runner.is_alive()
    assert len(list(runner.iterprocs())) == 0
    # tests transparency of the defaults config pipeline
    scen = plugin.mng.hook.pysipp_conf_scen_protocol(
        agents=[ua], confpy=None, defaults=None)
    cmd = scen.prepare_agent(ua).render()
    assert cmd in cmds2procs
    assert len(cmds2procs) == 1
    proc = cmds2procs[cmd]
    assert proc.returncode == retcode

    # rerun it with raising
    if not exc:
        with pytest.raises(RuntimeError):
            ua(**kwargs)


def test_scenario():
    uas, uac = agent.server(), agent.client()
    agents = [uas, uac]
    scen = agent.Scenario(agents)
    scen2 = agent.Scenario(agents)

    # verify contained agents
    assert scen.agents.values() == agents == scen._agents
    assert scen.prepare() != agents  # new copies

    # verify order
    assert uas is scen.agents.values()[0]
    assert uac is scen.agents.values()[1]
    # verify servers
    assert uas is scen.servers.values()[0]
    # verify clients
    assert uac is scen.clients.values()[0]

    # ensure defaults attr setting works
    doggy = 'doggy'
    scen.local_host = doggy
    uas, uac = scen.prepare()
    assert uac.local_host == uas.local_host == doggy

    # should be no shared state between instances
    assert scen2.local_host != doggy
    scen2.local_host = 10
    assert scen.local_host == doggy

    # same error for any non-spec defined agent attr
    with pytest.raises(AttributeError):
        scen.agentdefaults.local_man = 'flasher'
        scen.prepare()

    # defaults on servers only
    scen.serverdefaults.uri_username = doggy
    uas, uac = scen.prepare()
    assert uas.uri_username == doggy
    assert uac.uri_username != doggy

    assert scen.name == 'uas_uac'
