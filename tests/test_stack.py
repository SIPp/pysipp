"""
End to end tests with plugin support
"""
import functools
import os

import pytest

import pysipp


@pytest.fixture
def scenwalk(scendir):
    return functools.partial(pysipp.walk, scendir)


def test_collect(scenwalk):
    """Verify the scendir filtering hook"""
    assert len(list(scenwalk())) == 2

    # test filtering hook
    class blockall(object):
        @pysipp.plugin.hookimpl
        def pysipp_load_scendir(self, path, xmls, confpy):
            return False

    with pysipp.plugin.register([blockall()]):
        assert not len(list(scenwalk()))

    @pysipp.plugin.hookimpl
    def confpy_included(self, path, xmls, confpy):
        return bool(confpy)

    blockall.pysipp_load_scendir = confpy_included

    pysipp.plugin.mng.register(blockall())
    assert len(list(scenwalk())) == 1


def test_confpy_hooks(scendir):
    """Test that hooks included in a confpy file work

    Assertions here are based on predefined hooks
    """
    path, scen = list(pysipp.walk(scendir + "/default_with_confpy"))[0]
    assert scen.mod
    # ordering hook should reversed agents
    agents = list(scen.agents.values())
    assert agents[0].is_client()
    assert agents[1].is_server()
    # check that `scen.remote_host = 'doggy'` was applied
    assert scen.defaults.uri_username == "doggy"
    for agent in scen.prepare():
        assert agent.uri_username == "doggy"


def test_proxyaddr_with_scendir(scendir):
    """When building a scenario from a xml file directory the
    `proxyaddr` kwarg should be assigned.
    """
    remoteaddr = ("9.9.9.9", 80)
    scen = pysipp.scenario(
        dirpath=scendir + "/default_with_confpy", proxyaddr=remoteaddr
    )

    assert scen.clientdefaults.proxyaddr == remoteaddr
    for name, cmd in scen.cmditems():
        if name == "uac":
            assert "-rsa '{}':'{}'".format(*remoteaddr) in cmd
            assert "'{}':'{}'".format(*scen.clientdefaults.destaddr) in cmd
        elif name == "uas":
            assert "-rsa '{}':'{}'".format(*remoteaddr) not in cmd


def test_sync_run(scenwalk):
    """Ensure all scenarios in the test run to completion in
    synchronous mode"""
    for path, scen in scenwalk():
        runner = scen(timeout=6)
        for cmd, proc in runner.get(timeout=0).items():
            assert proc.returncode == 0


def test_async_run(scenwalk):
    """Ensure multiple scenarios run to completion in asynchronous mode."""
    finalizers = []
    for path, scen in scenwalk():
        finalizers.append((scen, scen(block=False)))

    # collect all results synchronously
    for scen, finalizer in finalizers:
        for cmd, proc in scen.finalize(timeout=6).items():
            assert proc.returncode == 0


def test_basic(basic_scen):
    """Test the most basic uac <-> uas call flow"""
    assert len(basic_scen.agents) == 2
    # ensure sync run works
    runner = basic_scen()
    assert not runner.is_alive()


def test_unreachable_uas(basic_scen):
    """Test the basic scenario but have the uas bind to a different port thus
    causing the uac to timeout on request responses. Ensure that an error is
    raised and that the appropriate log files are generated per agent.
    """
    uas = basic_scen.agents["uas"]
    uas.proxyaddr = uas.local_host, 9999
    with pytest.raises(RuntimeError):
        basic_scen()

    # verify log file generation for each agent
    for ua in basic_scen.prepare():
        for name, path in ua.iter_logfile_items():
            # randomly the -logfile stopped being generated?
            if "log" not in name:
                assert os.path.isfile(path)
                os.remove(path)


def test_hook_overrides(basic_scen):
    """Ensure that composite agent attributes (such as socket addresses) do
    not override individual agent argument attrs that were set explicitly
    elsewhere (eg. in a hook).
    """

    class Router(object):
        @pysipp.plugin.hookimpl
        def pysipp_conf_scen(self, agents, scen):
            # no explicit port is set on agents by default
            agents["uas"].local_port = 5090
            agents["uac"].remote_port = agents["uas"].local_port

    with pysipp.plugin.register([Router()]):
        pysipp.plugin.mng.hook.pysipp_conf_scen(
            agents=basic_scen.agents, scen=basic_scen
        )

    # apply a composite socket addr attr
    basic_scen.clientdefaults["destaddr"] = "10.10.99.99", "doggy"

    # destaddr set in clientdefaults should not override agent values
    agents = basic_scen.prepare()
    # ensure uac still points to uas port
    assert agents[1].remote_port == agents[0].local_port


@pytest.mark.parametrize(
    "dictname",
    ["defaults", "clientdefaults", "serverdefaults"],
    ids=str,
)
@pytest.mark.parametrize(
    "data",
    [
        {"local_host": "127.0.0.1"},
        {"local_port": 5080},
        {"local_port": 5080, "local_host": "127.0.0.1"},
        {"srcaddr": ("127.0.0.1", 5080)},
        {"media_addr": "127.0.0.1"},
        {"media_port": 5080},
        {"media_port": 5080, "media_addr": "127.0.0.1"},
        {"mediaaddr": ("127.0.0.1", 5080)},
    ],
    ids=lambda d: str(d),
)
def test_autonet_overrides(dictname, data):
    """Ensure the auto-networking plugin doesn't override default or agent
    settings applied by client code.
    """
    scen = pysipp.scenario(**{dictname: data})
    scen = scen.from_agents()
    # netplug.py hooks shouldn't override the uac srcaddr
    if "client" in dictname:
        agents = scen.clients
    elif "server" in dictname:
        agents = scen.servers
    else:
        agents = scen.agents

    for key, val in data.items():
        for ua in agents.values():
            assert getattr(ua, key) == val
