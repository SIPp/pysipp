"""
Wrappers for user agents which apply sensible cmdline arg defaults
"""
import itertools
import re
import tempfile
from collections import namedtuple
from collections import OrderedDict
from copy import deepcopy
from os import path

from shutil import which

from . import command
from . import plugin
from . import utils

log = utils.get_logger()

SocketAddr = namedtuple("SocketAddr", "ip port")


def tuple_property(attrs):
    def getter(self):
        tup = tuple(getattr(self, attr) for attr in attrs)
        if all(tup):
            return tup
        return None

    def setter(self, pair):
        if not isinstance(pair, tuple):
            if pair is None:
                pair = (None, None)
            else:
                raise ValueError("{} must be a tuple".format(pair))
        for attr, val in zip(attrs, pair):
            setattr(self, attr, val)

    doc = "{} parameters composed as a tuple".format(", ".join(attrs))

    return property(getter, setter, doc=doc)


class UserAgent(command.SippCmd):
    """An extension of a SIPp command string which provides more pythonic
    higher level attributes for assigning input arguments similar to
    configuration options for a SIP UA.
    """

    # we skip `error` since we can get it from stderr
    _log_types = "screen log".split()
    _debug_log_types = "calldebug message".split()
    _to_console = "screen"

    @property
    def name(self):
        """Compute the name identifier for this agent based the scenario script
        or scenario name
        """
        return self.scen_name or path2namext(self.scen_file) or str(None)

    srcaddr = tuple_property(("local_host", "local_port"))
    destaddr = tuple_property(("remote_host", "remote_port"))
    mediaaddr = tuple_property(("media_addr", "media_port"))
    proxyaddr = tuple_property(("proxy_host", "proxy_port"))
    ipcaddr = tuple_property(("ipc_host", "ipc_port"))
    call_load = tuple_property(("rate", "limit", "call_count"))

    def __call__(
        self, block=True, timeout=180, runner=None, raise_exc=True, **kwargs
    ):

        # create and configure a temp scenario
        scen = plugin.mng.hook.pysipp_conf_scen_protocol(
            agents=[self],
            confpy=None,
            scenkwargs={},
        )
        # run the standard protocol
        # (attach allocted runner for reuse/post-portem)
        return plugin.mng.hook.pysipp_run_protocol(
            scen=scen,
            block=block,
            timeout=timeout,
            runner=runner,
            raise_exc=raise_exc,
            **kwargs
        )

    def is_client(self):
        return "uac" in self.name.lower()

    def is_server(self):
        return "uas" in self.name.lower()

    def iter_logfile_items(
        self, types_attr="_log_types", enable_screen_file=True
    ):
        for name in getattr(self, types_attr):
            if name != "screen" or enable_screen_file:
                attr_name = name + "_file"
                yield attr_name, getattr(self, attr_name)

    def iter_toconsole_items(self):
        yield "screen_file", self.screen_file

    @property
    def cmd(self):
        """Rendered SIPp command string"""
        return self.render()

    @property
    def logdir(self):
        return getattr(self, "_logdir", None)

    @logdir.setter
    def logdir(self, dirpath):
        assert path.isdir(dirpath), "{} is an invalid path".format(dirpath)
        self._logdir = dirpath

    @property
    def plays_media(self, patt="play_pcap_audio"):
        """Bool determining whether script plays media"""
        # TODO: should be able to parse using -sd
        if not self.scen_file:
            return False

        with open(self.scen_file, "r") as sf:
            return bool(re.search(patt, sf.read()))

    def enable_tracing(self):
        """Enable trace flags for this command"""
        for name in self._log_types:
            attr_name = "trace_" + name
            setattr(self, attr_name, True)

    def enable_logging(
        self, logdir=None, debug=False, enable_screen_file=True
    ):
        """Enable agent logging by appending appropriately named log file
        arguments to the underlying command.
        """
        logattrs = self.iter_logfile_items(
            enable_screen_file=enable_screen_file
        )
        if debug:
            logattrs = itertools.chain(
                logattrs,
                self.iter_logfile_items("_debug_log_types"),
            )
        # prefix all log file paths
        for name, attr in logattrs:
            setattr(
                self,
                name,
                attr
                or path.join(
                    logdir or self.logdir or tempfile.gettempdir(),
                    "{}_{}".format(self.name, name),
                ),
            )

        self.enable_tracing()


def path2namext(filepath):
    if not filepath:
        return None
    name, ext = path.splitext(path.basename(filepath))
    return name


def ua(logdir=None, **kwargs):
    """Default user agent factory.
    Returns a command string instance with sensible default arguments.
    """
    defaults = {
        "bin_path": which("sipp"),
    }
    # drop any built-in scen if a script file is provided
    if "scen_file" in kwargs:
        kwargs.pop("scen_name", None)

    # override with user settings
    defaults.update(kwargs)
    ua = UserAgent(defaults)

    # assign output file paths
    if logdir:
        ua.logdir = logdir

    return ua


def server(**kwargs):
    """A SIPp user agent server
    (i.e. recieves a SIP message as it's first action)
    """
    defaults = {
        "scen_name": "uas",
    }
    if "dstaddr" in kwargs:
        raise ValueError(
            "User agent server does not accept a destination address"
        )
    # override with user settings
    defaults.update(kwargs)
    return ua(**defaults)


def client(**kwargs):
    """A SIPp user agent client
    (i.e. sends a SIP message as it's first action)
    """
    defaults = {
        "scen_name": "uac",
    }
    # override with user settings
    defaults.update(kwargs)
    return ua(**defaults)


# default values every scenario should define at a minimum
_minimum_defaults_template = {
    "key_vals": {},
    "global_vars": {},
}
_scen_defaults_template = {
    "recv_timeout": 5000,
    "call_count": 1,
    "rate": 1,
    "limit": 1,
    "logdir": tempfile.gettempdir(),
}
_scen_defaults_template.update(deepcopy(_minimum_defaults_template))


def Scenario(agents, **kwargs):
    """Wraps (subsets of) user agents in global state pertaining to
    configuration, routing, and default arguments.

    If called it will invoke the standard run hooks.
    """
    scentype = type("Scenario", (ScenarioType,), {})

    _defs = OrderedDict(deepcopy(_scen_defaults_template))
    # for any passed kwargs that have keys in ``_defaults_template``, set them
    # as the new defaults for the scenario
    for key, val in kwargs.copy().items():
        if key in _defs:
            _defs[key] = kwargs.pop(key)

    # if a `defaults` kwarg is passed in by the user override template
    # values with values from that as well
    user_defaults = kwargs.pop("defaults", None)
    if user_defaults:
        _defs.update(user_defaults)

    # this gives us scen.<param> attribute access to scen.defaults
    utils.DictProxy(_defs, UserAgent.keys(), cls=scentype)
    return scentype(agents, _defs, **kwargs)


class ScenarioType(object):
    """Wraps (subsets of) user agents in global state pertaining to
    configuration, routing, and default arguments.

    If called it will invoke the standard run hooks.
    """

    def __init__(
        self,
        agents,
        defaults,
        clientdefaults=None,
        serverdefaults=None,
        confpy=None,
        enable_screen_file=True,
    ):
        # agents iterable in launch-order
        self._agents = agents
        ua_attrs = UserAgent.keys()

        # default settings
        self._defaults = defaults
        self.defaults = utils.DictProxy(self._defaults, ua_attrs)()

        # client settings
        self._clientdefaults = OrderedDict(
            clientdefaults or deepcopy(_minimum_defaults_template)
        )
        self.clientdefaults = utils.DictProxy(self._clientdefaults, ua_attrs)()

        # server settings
        self._serverdefaults = OrderedDict(
            serverdefaults or deepcopy(_minimum_defaults_template)
        )
        self.serverdefaults = utils.DictProxy(self._serverdefaults, ua_attrs)()

        # hook module
        self.mod = confpy
        self.enable_screen_file = enable_screen_file

    @property
    def agents(self):
        return OrderedDict((ua.name, ua) for ua in self._agents)

    @property
    def clients(self):
        return OrderedDict(
            (ua.name, ua) for ua in self._agents if ua.is_client()
        )

    @property
    def servers(self):
        return OrderedDict(
            (ua.name, ua) for ua in self._agents if ua.is_server()
        )

    @property
    def name(self):
        """Attempt to extract a name from a combination of scenario directory
        and script names
        """
        dirnames = []
        for agent in self._agents:
            if agent.scen_file:
                dirnames.append(path.basename(path.dirname(agent.scen_file)))
            else:
                dirnames.append(agent.scen_name)

        # concat dirnames if scripts come from separate dir locations
        if len(set(dirnames)) > 1:
            return "_".join(dirnames)

        return dirnames[0]

    def findbyaddr(self, socket, bytype=""):
        """Lookup an agent by socket address. `bytype` is a keyword which
        determines which socket to use at the key and can be one of
        {'media', 'dest', 'src'}
        """
        for agent in self.prepare():
            val = getattr(agent, "{}sockaddr".format(bytype), False)
            if val:
                return agent

    @property
    def has_media(self):
        """Bool dermining whether this scen is a media player"""
        if any(agent.plays_media for agent in self._agents):
            return True
        return False

    @property
    def dirpath(self):
        """Scenario directory path in the file system where all xml scripts
        and pysipp_conf.py should reside.
        """
        scenfile = self.prepare()[0].scen_file
        return path.dirname(scenfile) if scenfile else None

    def cmditems(self):
        """Agent names to cmd strings items"""
        return [(agent.name, agent.cmd) for agent in self.prepare()]

    def pformat_cmds(self):
        """Pretty format string for printing agent commands"""
        return "\n\n".join(
            ["{}:\n{}".format(name, cmd) for name, cmd in self.cmditems()]
        )

    def prepare_agent(self, agent):
        """Return a new agent with all default settings applied from this
        scenario
        """

        def merge(dicts):
            """Merge dicts without clobbering up to 1 level deep's worth of
            sub-dicts
            """
            merged = deepcopy(dicts[0])
            for key, val in itertools.chain(*[d.items() for d in dicts[1:]]):
                if isinstance(val, dict):
                    merged.setdefault(key, val).update(val)
                else:
                    merged[key] = val

            return merged

        if agent.is_client():
            secondary = self._clientdefaults
            dname = "clientdefaults"
        elif agent.is_server():
            secondary = self._serverdefaults
            dname = "serverdefaults"
        else:
            secondary = {}
            dname = "unspecialized ua"

        # call pre defaults hook
        plugin.mng.hook.pysipp_pre_ua_defaults(ua=agent)

        # apply defaults
        ordered = [self._defaults, secondary, agent.todict()]
        for name, defs in zip(["defaults", dname, "agent.todict()"], ordered):
            log.debug("{} '{}' contents:\n{}".format(agent.name, name, defs))

        params = merge(ordered)
        log.debug("{} merged contents:\n{}".format(agent.name, params))
        ua = UserAgent(defaults=params)

        ua.enable_logging(enable_screen_file=self.enable_screen_file)

        # call post defaults hook
        plugin.mng.hook.pysipp_post_ua_defaults(ua=ua)

        return ua

    def prepare(self, agents=None):
        """Prepare (provided) agents according to the default configuration
        setttings in `defaults`, `clients`, and `servers` and return copies
        in a list.
        """
        copies = []
        agents = agents or self._agents
        for agent in agents:
            copies.append(self.prepare_agent(agent))
        return copies

    def from_settings(self, **kwargs):
        """Create a new scenario from scratch using current settings calling
        all normal plugin hooks.
        """
        from . import scenario

        scenkwargs = {
            "dirpath": self.dirpath,
            "defaults": self._defaults.copy(),
            "clientdefaults": self._clientdefaults.copy(),
            "serverdefaults": self._serverdefaults.copy(),
        }
        for key, value in kwargs.items():
            if key in scenkwargs:
                scenkwargs[key].update(value)

        return scenario(**scenkwargs)

    def from_agents(self, agents=None, autolocalsocks=True, **scenkwargs):
        """Create a new scenario from prepared agents."""
        return type(self)(
            self.prepare(agents), self._defaults, confpy=self.mod
        )

    def __call__(
        self,
        agents=None,
        block=True,
        timeout=180,
        runner=None,
        raise_exc=True,
        copy_agents=False,
        **kwargs
    ):
        return plugin.mng.hook.pysipp_run_protocol(
            scen=self,
            block=block,
            timeout=timeout,
            runner=runner,
            raise_exc=raise_exc,
            **kwargs
        )
