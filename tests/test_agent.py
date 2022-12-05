"""
pysipp.agent module tests
"""
import tempfile

import pytest

import pysipp
from pysipp import agent
from pysipp import launch
from pysipp import plugin


@pytest.fixture
def ua():
    return agent.Scenario([agent.ua()]).prepare()[0]


def test_ua(ua):
    """Set up a typeless agent and perform basic attr checks"""
    sock = ("10.10.9.9", 5060)
    ua.proxyaddr = sock
    assert ua.name == str(None)
    assert "'{}':'{}'".format(*sock) in ua.render()


def check_log_files(ua, logdir=None):
    logdir = logdir or ua.logdir
    assert logdir

    # check attr values contain logdir and agent name
    for name, path in ua.iter_logfile_items():
        assert logdir in path
        assert ua.name in path

    cmd = ua.render()
    assert logdir in cmd
    logs = [token for token in cmd.split() if logdir in token]
    # check num of args with logdir in the value
    assert len(logs) == len(ua._log_types)


@pytest.mark.parametrize(
    "funcname",
    ["ua", "client", "server"],
)
def test_logdir(funcname):
    """Verify that a default logdir is set and filenames are
    based on the agent's name.
    """
    func = getattr(agent, funcname)
    # enables SIPp logging by default
    ua = agent.Scenario([func()]).prepare()[0]
    check_log_files(ua, tempfile.gettempdir())


def test_scen_assign_logdir():
    """Verify log file arguments when logdir is set using Scenario.defaults"""
    scen = pysipp.scenario()
    logdir = tempfile.mkdtemp(suffix="_pysipp")
    scen.defaults.logdir = logdir
    for ua in scen.prepare():
        check_log_files(ua, logdir)


def test_scen_pass_logdir():
    """Verify log file arguments when logdir is set using Scenario.defaults"""
    logdir = tempfile.mkdtemp(suffix="_pysipp")
    scen = pysipp.scenario(logdir=logdir)
    assert scen.defaults.logdir == logdir

    # logdir isn't set until the scenario is "prepared"
    assert scen.agents["uac"].logdir is None

    # logdir is set once scenario is "rendered"
    for ua in scen.prepare():
        check_log_files(ua, logdir)


def test_walk_pass_logdir():
    logdir = tempfile.mkdtemp(suffix="_pysipp")
    scen = next(pysipp.walk("./tests/scens/default/", logdir=logdir))[1]
    assert scen.logdir == logdir

    # logdir is set once scenario is "rendered"
    for ua in scen.prepare():
        check_log_files(ua, logdir)


def test_client():
    # check the built-in uac xml scenario
    remote_sock = ("192.168.1.1", 5060)
    uac = agent.client(destaddr=remote_sock)
    cmdstr = uac.render()
    assert "-sn 'uac'" in cmdstr
    assert "'{}':'{}'".format(*remote_sock) in cmdstr

    # pretend script file
    script = "/home/sipp_scen/uac.xml"
    uac2 = agent.client(destaddr=remote_sock, scen_file=script)
    cmdstr = uac2.render()
    assert "-sn 'uac'" not in cmdstr
    assert "-sf '{}'".format(script) in cmdstr


def test_server():
    ua = agent.server()
    cmdstr = ua.render()
    assert "-sn 'uas'" in cmdstr
    assert not (ua.remote_host and ua.remote_port)


@pytest.mark.parametrize(
    "ua, retcode, kwargs, exc",
    [
        # test unspecialized ua failure
        (agent.ua(), 255, {}, RuntimeError),
        # test client failure on bad remote destination
        (agent.client(destaddr=("99.99.99.99", 5060)), 1, {}, RuntimeError),
        # test if server times out it is signalled
        (agent.server(), 0, {"timeout": 1}, launch.TimeoutError),
    ],
    ids=["ua", "uac", "uas"],
)
def test_failures(ua, retcode, kwargs, exc):
    """Test failure cases for all types of agents"""
    # run it without raising
    runner = ua(raise_exc=False, **kwargs)
    cmds2procs = runner.get(timeout=0)
    assert not runner.is_alive()
    assert len(list(runner.iterprocs())) == 0
    # tests transparency of the defaults config pipeline
    scen = plugin.mng.hook.pysipp_conf_scen_protocol(
        agents=[ua], confpy=None, scenkwargs={}
    )
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
    assert list(scen.agents.values()) == agents == scen._agents
    assert scen.prepare() != agents  # new copies

    # verify order
    agents = list(scen.agents.values())
    assert uas is agents[0]
    assert uac is agents[1]
    # verify servers
    assert uas is list(scen.servers.values())[0]
    # verify clients
    assert uac is list(scen.clients.values())[0]

    # ensure defaults attr setting works
    doggy = "doggy"
    scen.local_host = doggy
    uas, uac = scen.prepare()
    assert uac.local_host == uas.local_host == doggy

    # should be no shared state between instances
    assert scen2.local_host != doggy
    scen2.local_host = 10
    assert scen.local_host == doggy

    # same error for any non-spec defined agent attr
    with pytest.raises(AttributeError):
        scen.agentdefaults.local_man = "flasher"
        scen.prepare()

    # defaults on servers only
    scen.serverdefaults.uri_username = doggy
    uas, uac = scen.prepare()
    assert uas.uri_username == doggy
    assert uac.uri_username != doggy

    assert scen.name == "uas_uac"


def test_pass_bad_socket_addr():
    with pytest.raises(ValueError):
        pysipp.client(proxyaddr="10.10.8.88")


def test_authentication_arguments():
    client = agent.client(auth_username="username", auth_password="passw0rd")

    cmd = client.render()

    assert "-au 'username'" in cmd
    assert "-ap 'passw0rd'" in cmd
