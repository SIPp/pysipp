'''
Wrappers for user agents which apply sensible cmdline arg defaults
'''
from os import path
import re
from distutils import spawn
from copy import copy
from collections import namedtuple, OrderedDict
from . import command, plugin
import utils

log = utils.get_logger()

SocketAddr = namedtuple('SocketAddr', 'ip port')


class UserAgent(command.SippCmd):
    """An extension of a SIPp command string which provides more pythonic
    higher level attributes for assigning input arguments similar to
    configuration options for a SIP UA.
    """
    # we skip `error` since we can get it from stderr
    _log_types = 'screen calldebug message log'.split()

    @property
    def name(self):
        """Compute the name identifier for this agent based the scenario script
        or scenario name
        """
        return self.scen_name or path2namext(self.scen_file) or str(None)

    @property
    def sockaddr(self):
        """Local socket info as a tuple
        """
        return SocketAddr(self.local_host, self.local_port)

    @sockaddr.setter
    def sockaddr(self, pair):
        self.local_host, self.local_port = pair

    @property
    def remotesockaddr(self):
        """Local socket info as a tuple
        """
        return SocketAddr(self.remote_host, self.remote_port)

    @remotesockaddr.setter
    def remotesockaddr(self, pair):
        self.remote_host, self.remote_port = pair

    @property
    def mediasockaddr(self):
        """Local socket info as a tuple
        """
        return SocketAddr(self.media_addr, self.media_port)

    @mediasockaddr.setter
    def mediasockaddr(self, pair):
        self.media_addr, self.media_port = pair

    @property
    def proxy(self):
        """A tuple holding the (addr, port) socket pair which will be set as
        the `-rsa addr:port` flag to underlying SIPp UACs.
        """
        return SocketAddr(self.proxy_addr, self.proxy_port)

    @proxy.setter
    def proxy(self, pair):
        if pair is None:
            self.proxy_addr = self.proxy_port = None

        self.proxy_addr, self.proxy_port = pair

    @property
    def ipcsockaddr(self, pair):
        return SocketAddr(self.ipc_host, self.ipc_port)

    @ipcsockaddr.setter
    def ipcsockaddr(self, pair):
        self.ipc_host, self.ipc_port = pair

    @property
    def call_load(self, tup):
        """Shorthand attr for accessing load settings
        """
        return self.rate, self.limit, self.call_count

    @call_load.setter
    def call_load(self, tup):
        self.rate, self.limit, self.call_count = tup

    def __call__(self, block=True, timeout=180, runner=None, raise_exc=True,
                 **kwargs):

        # create and configure a temp scenario
        scen = plugin.mng.hook.pysipp_conf_scen_protocol(
            agents=[self], confpy=None
        )
        # run the standard protocol
        # (attach allocted runner for reuse/post-portem)
        return plugin.mng.hook.pysipp_run_protocol(
            scen=scen, block=block, timeout=timeout,
            runner=runner,
            raise_exc=raise_exc, **kwargs
        )

    def is_client(self):
        return 'uac' in self.name.lower()

    def is_server(self):
        return 'uas' in self.name.lower()

    def iter_logfile_items(self):
        for name in self._log_types:
            attr_name = name + '_file'
            yield attr_name, getattr(self, attr_name)

    def enable_tracing(self):
        for name in self._log_types:
            attr_name = 'trace_' + name
            setattr(self, attr_name, True)

    @property
    def cmd(self):
        """Rendered SIPp command string
        """
        return self.render()

    @property
    def logdir(self):
        return self._logdir

    @logdir.setter
    def logdir(self, dirpath):
        assert path.isdir(dirpath)
        for name, attr in self.iter_logfile_items():
            # set all log files
            setattr(self, name,
                    path.join(dirpath, "{}_{}".format(self.name, name)))

        # enable all corresponding trace flag args
        self.enable_tracing()
        self._logdir = dirpath

    @property
    def plays_media(self, patt='play_pcap_audio'):
        """Bool determining whether script plays media
        """
        # FIXME: should be able to parse using -sd
        if not self.scen_file:
            return False

        with open(self.scen_file, 'r') as sf:
            return bool(re.match(patt, sf.read()))


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
        'bin_path': spawn.find_executable('sipp'),
        'recv_timeout': 5000,
        'call_count': 1,
        'rate': 1,
    }
    # drop any built-in scen if a script file is provided
    if 'scen_file' in kwargs:
        kwargs.pop('scen_name')

    log.debug("defaults are {} extras are {}".format(
        defaults, kwargs))

    # override with user settings
    defaults.update(kwargs)
    ua = UserAgent(defaults)

    # call pre defaults hook
    plugin.mng.hook.pysipp_pre_ua_defaults(ua=ua)

    # apply defaults
    # assign output file paths
    ua.logdir = logdir or utils.get_tmpdir()

    # call post defaults hook
    plugin.mng.hook.pysipp_post_ua_defaults(ua=ua)

    return ua


def server(**kwargs):
    """A SIPp user agent server
    (i.e. recieves a SIP message as it's first action)
    """
    defaults = {
        'scen_name': 'uas',
    }
    # override with user settings
    defaults.update(kwargs)
    return ua(**defaults)


def client(remote_host, remote_port, **kwargs):
    """A SIPp user agent client
    (i.e. sends a SIP message as it's first action)
    """
    defaults = {
        'scen_name': 'uac',
    }
    # override with user settings
    defaults.update(kwargs)
    assert remote_host and remote_port
    return ua(
        remote_host=remote_host,
        remote_port=remote_port,
        **defaults
    )


class MultiAccess(OrderedDict):
    """A OrderedDict which applies attr sets to all values
    """
    @classmethod
    def from_iter(cls, itr):
        inst = cls()
        inst._init = True  # mark instantiation complete
        # insert items by name
        for item in itr:
            inst[item.name] = item

        return inst

    def __setattr__(self, name, value):
        # default impl
        if not hasattr(self, '_init'):
            object.__setattr__(self, name, value)
            return

        # multi-setattr all items with a copy after init is complete
        for agent in self.values():
            setattr(agent, name, copy(value))

    def __getattr__(self, key):
        if not hasattr(self, '_init'):
            return object.__getattribute__(self, key)
        try:
            return object.__getattribute__(self, key)
        except AttributeError:
            vals = self.values()
            if vals and key not in dir(vals[0]):
                raise
            res = OrderedDict()
            for name, ua in self.items():
                val = getattr(ua, key, None)
                if val:
                    res[name] = val
            return res

    def multiupdate(self, attr, item):
        """Update all values.attrs with the provided item
        """
        for val in self.values():
            getattr(val, attr).update(item)


class Scenario(object):
    """Wraps user agents as a collection for configuration,
    routing, and launching by hooks. It is callable and can be optionally
    be invoked asynchronously.
    """
    def __init__(self, agents, confpy=None):
        self._agents = agents  # original iterable
        self.agents = MultiAccess.from_iter(agents)
        self.clients = MultiAccess.from_iter(
            a for a in agents if a.is_client())
        self.servers = MultiAccess.from_iter(
            a for a in agents if a.is_server())
        self.mod = confpy

    @property
    def proxy(self):
        """Proxy socket for the first client in this scenario
        """
        return self.clients.values()[0].proxy

    @proxy.setter
    def proxy(self, value):
        self.clients.values()[0].proxy = value

    @property
    def name(self):
        """Attempt to extract a name from a combination of scenario directory
        and script names
        """
        dirnames = []
        for agent in self.agents.values():
            if agent.scen_file:
                dirnames.append(path.basename(path.dirname(agent.scen_file)))
            else:
                dirnames.append(agent.scen_name)

        # concat dirnames if scripts come from separate dir locations
        if len(set(dirnames)) > 1:
            return '_'.join(dirnames)

        return dirnames[0]

    def socket2agent(self, socket, bytype=''):
        """Lookup an agent by socket. `bytype` is a keyword which determines
        which socket to use at the key and can be one of {'media', 'remote'}
        """
        for agent in self.agents.values():
            val = getattr(agent, "{}sockaddr".format(bytype), False)
            if val:
                return agent

    @property
    def has_media(self):
        """Bool dermining whether this scen is a media player
        """
        if any(agent.plays_media for agent in self.agents.values()):
            return True
        return False

    @property
    def dirpath(self):
        """Scenario directory path in the file system where all xml scripts
        and pysipp_conf.py should reside.
        """
        scenfile = self.agents.values()[0].scen_file
        return path.dirname(scenfile) if scenfile else None

    def cmditems(self):
        """Map of agent names to cmd strings
        """
        return [(name, agent.cmd) for name, agent in self.agents.iteritems()]

    def pformat_cmds(self):
        """Pretty format string for printing agent commands
        """
        return '\n\n'.join(
            ["{}:\n{}".format(name, cmd) for name, cmd in self.cmditems()]
        )

    def __call__(self, block=True, timeout=180, runner=None, raise_exc=True,
                 **kwargs):
        return plugin.mng.hook.pysipp_run_protocol(
            scen=self, block=block, timeout=timeout, runner=runner,
            raise_exc=raise_exc, **kwargs
        )
