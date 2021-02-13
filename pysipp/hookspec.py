"""
hookspec defs
"""
import pluggy

hookspec = pluggy.HookspecMarker("pysipp")


# UA factory hooks
@hookspec
def pysipp_pre_ua_defaults(ua):
    """Called prior to default ua cmd line arguments being assigned.
    Only a subset of `pysipp.UserAgent` attributes can be assigned.
    """


@hookspec
def pysipp_post_ua_defaults(ua):
    """Called just after all default ua cmdline args have been assigned.
    Any attribute can be overridden on `ua`.
    """


# Scenario hooks
@hookspec
def pysipp_load_scendir(path, xmls, confpy):
    """Called once for every scenario directory that is scanned and loaded by
    `pysipp.load.iter_scen_dirs`. The `xmls` arg is a list of path strings and
    `confpy` is the imported conf.py module if one exists or None.

    A single implementation of this hook must return `True` to include the
    scanned dir as a collected scenario and all must return `False` if the
    scenario should be skipped entirely.
    """


@hookspec(firstresult=True)
def pysipp_conf_scen_protocol(agents, confpy, scenkwargs):
    """Performs scenario configuration by making multiple hook calls with
    surrounding logic for determining the sub-registration of of pysipp_conf.py
    modules. A scenario object must be returned.
    """


@hookspec(firstresult=True)
def pysipp_order_agents(agents, clients, servers):
    """Return ua iterator which delivers agents in launch order"""


@hookspec(firstresult=True)
def pysipp_new_scen(agents, confpy, scenkwargs):
    """Instantiate a scenario object.
    A scenario must adhere to a simple protocol:
        - support a `name` attribute which uniquely identifies the scenario
        - support 'agents', 'clients', 'servers' attributes
        - be callable (usually launching the underlying agents when
          called by in turn calling the `pysipp_run_protocol` hook)
    """


@hookspec
def pysipp_conf_scen(agents, scen):
    """Called once by each pysipp.Scenario instance just after instantiation.
    Normally this hook is used to configure "call routing" by setting agent
    socket arguments. It it the recommended hook for applying a default
    scenario configuration.
    """


@hookspec(firstresult=True)
def pysipp_new_runner():
    """Create and return a runner instance to be used for invoking
    multiple SIPp commands. The runner must be callable and support both a
    `block` and `timeout` kwarg.
    """


@hookspec(firstresult=True)
def pysipp_run_protocol(scen, runner, block, timeout, raise_exc):
    """Perform steps to execute all SIPp commands usually by calling a
    preconfigured command launcher/runner.
    """
