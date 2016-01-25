'''
End to end tests with plugin support
'''
import pytest
import pysipp
import functools
import os


@pytest.fixture
def scenwalk(scendir):
    return functools.partial(pysipp.walk, scendir)


def test_collect(scenwalk):
    """Verify the scendir filtering hook
    """
    assert len(list(scenwalk())) == 2

    # test filtering hook
    class blockall(object):
        @pysipp.plugin.hookimpl
        def pysipp_load_scendir(self, path, xmls, confpy):
            return False

    ba = blockall()
    pysipp.plugin.mng.register(ba)
    assert not len(list(scenwalk()))
    pysipp.plugin.mng.unregister(ba)

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
    path, scen = list(pysipp.walk(scendir + '/default_with_confpy'))[0]
    assert scen.mod
    # ordering hook should reversed agents
    agents = scen.agents.values()
    assert agents[0].is_client()
    assert agents[1].is_server()
    # check multi-attr set was applied
    for agent in scen.agents.values():
        assert agent.remote_host == 'doggy'


def test_sync_run(scenwalk):
    """Ensure all scenarios in the test run to completion in synchronous mode
    """
    for path, scen in scenwalk():
        runner = scen(raise_exc=False, timeout=5)
        for cmd, proc in runner.get(timeout=0).items():
            if 'default_with_confpy' in scen.name:
                assert proc.returncode != 0
            else:
                assert proc.returncode == 0


def test_basic(basic_scen):
    """Test the most basic uac <-> uas call flow
    """
    assert len(basic_scen.agents) == 2
    # ensure sync run works
    runner = basic_scen()
    assert not runner.is_alive()


def test_unreachable_uas(basic_scen):
    """Test the basic scenario but have the uas bind to a different port thus
    causing the uac to timeout on request responses. Ensure that an error is
    raised and that the appropriate log files are generated per agent.
    """
    basic_scen.servers.proxyaddr = ('127.0.0.1', 5070)
    with pytest.raises(RuntimeError):
        basic_scen()

    # verify log file generation for each agent
    uas = basic_scen.agents['uas']
    logdir = uas.logdir
    numagents = len(basic_scen.agents)
    numlogs = len(list(uas.iter_logfile_items()))
    assert numagents * 3 <= len(os.listdir(logdir)) <= numagents * numlogs


# def test_async_run(scenwalk):
#     """Ensure all scenarios in the test run to completion in asynchronous
#     mode
#     """
#     pass
